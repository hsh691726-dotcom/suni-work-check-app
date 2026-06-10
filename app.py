from __future__ import annotations

import io
import calendar
import tomllib
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st


APP_TITLE = "경영지원 업무 체크 도우미"
APP_SUBTITLE = "매일·주간·월간 경영지원 업무를 한 화면에서 확인하고, 오늘 할 일과 미완료 업무를 자동 정리합니다."

BASE_DIR = Path(__file__).parent
ASSET_DIR = BASE_DIR / "assets"
SAMPLE_CSV_PATH = BASE_DIR / "sample_tasks.csv"

TASK_COLUMNS = [
    "업무명",
    "업무구분",
    "반복주기",
    "담당자",
    "마감일",
    "진행상태",
    "중요도",
    "대표님보고",
    "관련시스템",
    "메모",
]

CATEGORIES = ["경리", "총무", "인사", "공무", "고객상담", "CRM", "홈택스", "4대보험", "고용산재", "KISCON", "기타"]
REPEAT_TYPES = ["매일", "주간", "월간", "일회성"]
STATUSES = ["완료", "진행중", "미완료", "보류"]
IMPORTANCES = ["높음", "보통", "낮음"]
REPORT_FLAGS = ["예", "아니오"]
SYSTEMS = ["홈택스", "CRM 앱", "4대보험 EDI", "고용산재 토탈서비스", "KISCON", "카카오톡/문자", "Excel", "PDF", "기타"]
GOOGLE_SHEETS_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMN_ALIASES = {
    "업무명": ["업무명", "업무", "할일", "할 일", "task", "title", "name"],
    "업무구분": ["업무구분", "구분", "분류", "카테고리", "category", "type"],
    "반복주기": ["반복주기", "주기", "반복", "frequency", "repeat"],
    "담당자": ["담당자", "담당", "owner", "assignee"],
    "마감일": ["마감일", "마감", "기한", "due", "deadline", "date"],
    "진행상태": ["진행상태", "상태", "status"],
    "중요도": ["중요도", "우선순위", "priority", "importance"],
    "대표님보고": ["대표님보고", "보고", "대표보고", "보고필요", "report"],
    "관련시스템": ["관련시스템", "시스템", "연동", "관련 시스템", "system"],
    "메모": ["메모", "비고", "설명", "내용", "memo", "note"],
}


def find_logo_file() -> Path | None:
    candidates: list[Path] = []
    for folder in [BASE_DIR, ASSET_DIR]:
        if folder.exists():
            candidates.extend(folder.glob("*"))
    for path in candidates:
        name = path.name.lower()
        if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"] and any(key in name for key in ["logo", "로고", "brand", "icon"]):
            return path
    return None


def create_sample_tasks() -> pd.DataFrame:
    today = date.today()
    rows = [
        ["입출금 내역 확인", "경리", "매일", "경영지원", today, "진행중", "높음", "예", "Excel", "통장 입출금과 미처리 지출을 먼저 확인"],
        ["통장 결제요청 확인", "경리", "매일", "경영지원", today, "미완료", "높음", "예", "Excel", "오늘 지급해야 하는 요청 건 우선 처리"],
        ["텔레그램 결제요청 확인 및 입금 처리", "경리", "매일", "경영지원", today, "진행중", "높음", "예", "카카오톡/문자", "결제 요청 메시지 확인 후 처리 결과 표시"],
        ["홈택스 지출 입력 확인", "홈택스", "매일", "경영지원", today + timedelta(days=1), "미완료", "보통", "아니오", "홈택스", "세금계산서와 지출 입력 누락 확인"],
        ["고객상담 전화 내용 CRM 등록", "고객상담", "매일", "경영지원", today, "미완료", "높음", "예", "CRM 앱", "상담 누락 시 고객 응대 이력 공백 발생"],
        ["미팅 일정 CRM 등록", "CRM", "주간", "경영지원", today + timedelta(days=2), "진행중", "보통", "아니오", "CRM 앱", "확정 일정과 변경 요청을 함께 기록"],
        ["대표님께 미팅 확정 요청 전달", "CRM", "주간", "경영지원", today, "미완료", "높음", "예", "카카오톡/문자", "대표님 확인 필요"],
        ["신규 직원 입사서류 확인", "인사", "일회성", "경영지원", today + timedelta(days=3), "보류", "보통", "예", "Excel", "주민등록등본 등 민감정보는 원본 확인만"],
        ["4대보험 취득신고 확인", "4대보험", "월간", "경영지원", today - timedelta(days=1), "진행중", "높음", "예", "4대보험 EDI", "마감일 지남, 처리 상태 확인 필요"],
        ["고용산재 개시신고 확인", "고용산재", "월간", "경영지원", today + timedelta(days=4), "미완료", "보통", "예", "고용산재 토탈서비스", "현장별 신고 필요 여부 확인"],
        ["KISCON 등록 일정 확인", "KISCON", "월간", "경영지원", today - timedelta(days=3), "미완료", "높음", "예", "KISCON", "공사 일정 변경 반영 필요"],
        ["공사 계약서 PDF 정리", "공무", "주간", "경영지원", today + timedelta(days=5), "진행중", "보통", "아니오", "PDF", "현장명 기준으로 파일명 정리"],
        ["인건비 계산서 발행 여부 확인", "경리", "월간", "경영지원", today + timedelta(days=6), "미완료", "보통", "예", "홈택스", "월말 전 누락 여부 확인"],
        ["월별 지출현황 정리", "경리", "월간", "경영지원", today + timedelta(days=7), "진행중", "높음", "예", "Excel", "대표님 보고용 요약 포함"],
        ["미완료 업무 대표님 보고", "총무", "매일", "경영지원", today, "미완료", "높음", "예", "기타", "오늘 우선 처리 목록과 지연 업무 보고"],
    ]
    return pd.DataFrame(rows, columns=TASK_COLUMNS)


def ensure_task_columns(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in TASK_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = ""
    return prepared[TASK_COLUMNS]


def normalize_choice(value: object, choices: list[str], default: str) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return default
    compact = text.replace(" ", "").lower()
    for choice in choices:
        if compact == choice.replace(" ", "").lower():
            return choice
    for choice in choices:
        if compact in choice.replace(" ", "").lower() or choice.replace(" ", "").lower() in compact:
            return choice
    return default


def normalize_report_flag(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if text in ["예", "y", "yes", "true", "1", "필요", "보고", "o"]:
        return "예"
    if text in ["아니오", "n", "no", "false", "0", "불필요", "x"]:
        return "아니오"
    return "아니오"


def parse_due_date(value: object) -> date:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return date.today()
    return parsed.date()


def normalize_uploaded_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    renamed: dict[str, str] = {}
    source_columns = {str(column).strip().lower(): column for column in raw_df.columns}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = alias.strip().lower()
            if key in source_columns:
                renamed[source_columns[key]] = target
                break

    prepared = raw_df.rename(columns=renamed)
    prepared = ensure_task_columns(prepared)
    prepared["업무명"] = prepared["업무명"].astype(str).str.strip()
    prepared["업무명"] = prepared["업무명"].replace(["", "nan", "None"], "이름 없는 업무")
    prepared["업무구분"] = prepared["업무구분"].apply(lambda value: normalize_choice(value, CATEGORIES, "기타"))
    prepared["반복주기"] = prepared["반복주기"].apply(lambda value: normalize_choice(value, REPEAT_TYPES, "일회성"))
    prepared["담당자"] = prepared["담당자"].fillna("").astype(str).str.strip().replace("", "경영지원")
    prepared["마감일"] = prepared["마감일"].apply(parse_due_date)
    prepared["진행상태"] = prepared["진행상태"].apply(lambda value: normalize_choice(value, STATUSES, "미완료"))
    prepared["중요도"] = prepared["중요도"].apply(lambda value: normalize_choice(value, IMPORTANCES, "보통"))
    prepared["대표님보고"] = prepared["대표님보고"].apply(normalize_report_flag)
    prepared["관련시스템"] = prepared["관련시스템"].apply(lambda value: normalize_choice(value, SYSTEMS, "기타"))
    prepared["메모"] = prepared["메모"].fillna("").astype(str).str.strip()
    return prepared


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="cp949")
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    if name.endswith((".txt", ".md")):
        text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        lines = [line.strip("-* 	") for line in text.splitlines() if line.strip()]
        return pd.DataFrame({"업무명": lines, "메모": ["TXT/MD에서 가져온 업무"] * len(lines)})
    raise ValueError("CSV, Excel, TXT, MD 파일만 업로드할 수 있습니다.")


def get_overdue_tasks(df: pd.DataFrame, today: date) -> pd.DataFrame:
    return df[(df["마감일"] < today) & (df["진행상태"] != "완료")].copy()


def get_today_priority_tasks(df: pd.DataFrame, today: date) -> pd.DataFrame:
    candidates = df[
        (df["진행상태"].isin(["미완료", "진행중"]))
        & ((df["마감일"] <= today) | (df["중요도"] == "높음") | (df["대표님보고"] == "예"))
    ].copy()
    candidates["정렬_중요도"] = candidates["중요도"].map({"높음": 0, "보통": 1, "낮음": 2}).fillna(3)
    candidates["정렬_상태"] = candidates["진행상태"].map({"미완료": 0, "진행중": 1, "보류": 2, "완료": 3}).fillna(3)
    return candidates.sort_values(["정렬_중요도", "마감일", "정렬_상태"]).drop(columns=["정렬_중요도", "정렬_상태"])


def get_incomplete_tasks(df: pd.DataFrame) -> pd.DataFrame:
    ordering = {"높음": 0, "보통": 1, "낮음": 2}
    incomplete = df[df["진행상태"].isin(["미완료", "진행중", "보류"])].copy()
    incomplete["정렬_중요도"] = incomplete["중요도"].map(ordering).fillna(3)
    return incomplete.sort_values(["정렬_중요도", "마감일"]).drop(columns=["정렬_중요도"])


def generate_report_summary(df: pd.DataFrame, today: date) -> str:
    total = len(df)
    done = int((df["진행상태"] == "완료").sum())
    incomplete = get_incomplete_tasks(df)
    priority = get_today_priority_tasks(df, today)
    overdue = get_overdue_tasks(df, today)
    public_work = df[df["업무구분"].isin(["공무", "KISCON", "4대보험", "고용산재"])]
    crm_work = df[df["업무구분"].isin(["고객상담", "CRM"])]
    needs_report = df[(df["대표님보고"] == "예") & (df["진행상태"] != "완료")]

    def bullet_lines(items: pd.DataFrame, limit: int = 5) -> str:
        if items.empty:
            return "- 해당 사항 없음"
        lines = []
        for _, row in items.head(limit).iterrows():
            lines.append(f"- {row['업무명']} / {row['업무구분']} / {row['마감일']} / {row['진행상태']} / {row['중요도']}")
        if len(items) > limit:
            lines.append(f"- 외 {len(items) - limit}건 추가 확인 필요")
        return "\n".join(lines)

    report = f"""[경영지원 업무 보고 요약]
작성일: {today.strftime('%Y-%m-%d')}

1. 오늘 우선 처리 업무
{bullet_lines(priority, 7)}

2. 마감일 지난 업무
{bullet_lines(overdue, 5)}

3. 미완료 업무
{bullet_lines(incomplete, 7)}

4. 공무 관련 확인사항
{bullet_lines(public_work[public_work['진행상태'] != '완료'], 5)}

5. 고객상담/CRM 관련 확인사항
{bullet_lines(crm_work[crm_work['진행상태'] != '완료'], 5)}

6. 대표님 확인 요청
{bullet_lines(needs_report, 5)}

7. 이어서 확인할 업무
- 전체 업무 {total}건 중 완료 {done}건, 미완료/진행/보류 {len(incomplete)}건입니다.
- 오늘은 마감일이 임박했거나 중요도가 높은 업무부터 처리하는 것을 권장합니다.
- 홈택스, 4대보험 EDI, 고용산재, KISCON은 실제 시스템 연동 전까지 담당자가 직접 처리 완료 여부를 확인해야 합니다.
"""
    return report


def generate_result_with_ai_later(prompt: str) -> str:
    """Future extension point: replace the rule-based report with an AI API call later."""
    return prompt


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue().encode("utf-8-sig")


def prepare_download_df(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared["마감일"] = prepared["마감일"].astype(str)
    return prepared


def read_local_secrets_file() -> dict:
    secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}
    return tomllib.loads(secrets_path.read_text(encoding="utf-8-sig"))


def get_google_sheet_settings() -> tuple[str, str, dict | None]:
    try:
        secrets_data = {
            "google_sheets": dict(st.secrets.get("google_sheets", {})),
            "gcp_service_account": dict(st.secrets.get("gcp_service_account", {})),
        }
    except Exception:
        secrets_data = {}

    if not secrets_data.get("google_sheets") or not secrets_data.get("gcp_service_account"):
        try:
            secrets_data = read_local_secrets_file()
        except Exception:
            secrets_data = {}

    spreadsheet_id = secrets_data.get("google_sheets", {}).get("spreadsheet_id", "")
    worksheet_name = secrets_data.get("google_sheets", {}).get("worksheet_name", "tasks")
    service_account_info = dict(secrets_data.get("gcp_service_account", {}))
    if not spreadsheet_id or not service_account_info:
        return "", worksheet_name or "tasks", None
    return spreadsheet_id, worksheet_name or "tasks", service_account_info


def google_sheets_is_configured() -> bool:
    spreadsheet_id, _, service_account_info = get_google_sheet_settings()
    return bool(spreadsheet_id and service_account_info)


def get_google_worksheet():
    spreadsheet_id, worksheet_name, service_account_info = get_google_sheet_settings()
    if not spreadsheet_id or not service_account_info:
        raise RuntimeError("Google Sheets 설정이 아직 없습니다.")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise RuntimeError("Google Sheets 연동 패키지가 설치되지 않았습니다. requirements.txt 설치가 필요합니다.") from exc

    credentials = Credentials.from_service_account_info(service_account_info, scopes=GOOGLE_SHEETS_SCOPE)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        return spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=worksheet_name, rows=200, cols=len(TASK_COLUMNS) + 3)


def load_tasks_from_google_sheets() -> pd.DataFrame:
    worksheet = get_google_worksheet()
    records = worksheet.get_all_records()
    if not records:
        worksheet.update([TASK_COLUMNS])
        return pd.DataFrame(columns=TASK_COLUMNS)
    return normalize_uploaded_dataframe(pd.DataFrame(records))


def save_tasks_to_google_sheets(df: pd.DataFrame) -> None:
    worksheet = get_google_worksheet()
    prepared = prepare_download_df(normalize_uploaded_dataframe(df))
    values = [TASK_COLUMNS] + prepared[TASK_COLUMNS].fillna("").astype(str).values.tolist()
    worksheet.clear()
    worksheet.update(values)


def add_tasks(new_tasks: pd.DataFrame) -> None:
    current = st.session_state.get("tasks", pd.DataFrame(columns=TASK_COLUMNS))
    st.session_state.tasks = normalize_uploaded_dataframe(pd.concat([current, new_tasks], ignore_index=True))


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.header("필터")
        repeat_filter = st.multiselect("반복주기", REPEAT_TYPES, default=REPEAT_TYPES)
        category_filter = st.multiselect("업무구분", CATEGORIES, default=CATEGORIES)
        status_filter = st.multiselect("진행상태", STATUSES, default=STATUSES)
        importance_filter = st.multiselect("중요도", IMPORTANCES, default=IMPORTANCES)
        report_filter = st.multiselect("대표님 보고", REPORT_FLAGS, default=REPORT_FLAGS)
        keyword = st.text_input("검색어", placeholder="업무명, 메모, 시스템 검색")

    filtered = df[
        df["반복주기"].isin(repeat_filter)
        & df["업무구분"].isin(category_filter)
        & df["진행상태"].isin(status_filter)
        & df["중요도"].isin(importance_filter)
        & df["대표님보고"].isin(report_filter)
    ].copy()

    if keyword.strip():
        text = keyword.strip().lower()
        mask = (
            filtered["업무명"].str.lower().str.contains(text, na=False)
            | filtered["메모"].str.lower().str.contains(text, na=False)
            | filtered["관련시스템"].str.lower().str.contains(text, na=False)
        )
        filtered = filtered[mask]
    return filtered


def show_metrics(df: pd.DataFrame, today: date) -> None:
    overdue_count = len(get_overdue_tasks(df, today))
    priority_count = len(get_today_priority_tasks(df, today))
    incomplete_count = len(get_incomplete_tasks(df))
    done_count = int((df["진행상태"] == "완료").sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 업무", f"{len(df)}건")
    c2.metric("오늘 우선 처리", f"{priority_count}건")
    c3.metric("마감 지연", f"{overdue_count}건")
    c4.metric("완료", f"{done_count}건", delta=f"미완료 {incomplete_count}건")


def render_storage_panel() -> None:
    with st.sidebar:
        st.header("저장소")
        if google_sheets_is_configured():
            st.success("Google Sheets 연결 설정 있음")
            if st.button("Google Sheets에서 새로고침", use_container_width=True):
                try:
                    st.session_state.tasks = load_tasks_from_google_sheets()
                    st.session_state.google_loaded = True
                    st.success("Google Sheets에서 업무를 불러왔습니다.")
                except Exception as exc:
                    st.error(f"불러오기 실패: {exc}")
            if st.button("현재 업무를 Google Sheets에 저장", use_container_width=True):
                try:
                    save_tasks_to_google_sheets(st.session_state.tasks)
                    st.success("Google Sheets에 저장했습니다.")
                except Exception as exc:
                    st.error(f"저장 실패: {exc}")
        else:
            st.warning("Google Sheets 설정 전입니다.")
            with st.expander("3기기 연동 준비"):
                st.write("집 노트북, 사무실 PC, 휴대폰에서 함께 쓰려면 Streamlit Cloud와 Google Sheets 설정이 필요합니다.")
                st.write("설정 전에는 CSV 다운로드/업로드 방식으로 계속 사용할 수 있습니다.")


def render_task_editor(df: pd.DataFrame) -> pd.DataFrame:
    return st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "업무구분": st.column_config.SelectboxColumn("업무구분", options=CATEGORIES),
            "반복주기": st.column_config.SelectboxColumn("반복주기", options=REPEAT_TYPES),
            "마감일": st.column_config.DateColumn("마감일", format="YYYY-MM-DD"),
            "진행상태": st.column_config.SelectboxColumn("진행상태", options=STATUSES),
            "중요도": st.column_config.SelectboxColumn("중요도", options=IMPORTANCES),
            "대표님보고": st.column_config.SelectboxColumn("대표님보고", options=REPORT_FLAGS),
            "관련시스템": st.column_config.SelectboxColumn("관련시스템", options=SYSTEMS),
        },
        key="task_editor",
    )


def get_week_range(selected_day: date) -> tuple[date, date]:
    week_start = selected_day - timedelta(days=selected_day.weekday())
    return week_start, week_start + timedelta(days=6)


def get_month_tasks(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    return df[(pd.to_datetime(df["마감일"]).dt.year == year) & (pd.to_datetime(df["마감일"]).dt.month == month)].copy()


def get_week_tasks(df: pd.DataFrame, selected_day: date) -> pd.DataFrame:
    week_start, week_end = get_week_range(selected_day)
    return df[(df["마감일"] >= week_start) & (df["마감일"] <= week_end)].copy()


def get_day_tasks(df: pd.DataFrame, selected_day: date) -> pd.DataFrame:
    return df[df["마감일"] == selected_day].copy()


def render_month_calendar(df: pd.DataFrame, year: int, month: int) -> None:
    month_tasks = get_month_tasks(df, year, month)
    tasks_by_day = {
        day: group.sort_values(["중요도", "진행상태", "업무명"])
        for day, group in month_tasks.groupby("마감일")
    }
    status_class = {"완료": "done", "진행중": "doing", "미완료": "todo", "보류": "hold"}
    cal = calendar.Calendar(firstweekday=0)
    week_names = ["월", "화", "수", "목", "금", "토", "일"]

    html_parts = [
        "<div class='calendar-grid calendar-weekdays'>",
        *[f"<div>{name}</div>" for name in week_names],
        "</div>",
        "<div class='calendar-grid'>",
    ]

    for week in cal.monthdatescalendar(year, month):
        for day in week:
            muted = " muted" if day.month != month else ""
            today_class = " today-cell" if day == date.today() else ""
            day_tasks = tasks_by_day.get(day, pd.DataFrame(columns=TASK_COLUMNS))
            chips = []
            for _, row in day_tasks.head(4).iterrows():
                css = status_class.get(row["진행상태"], "todo")
                label = escape(f"{row['반복주기']} · {row['업무명']}")
                chips.append(f"<div class='task-chip {css}' title='{label}'>{label}</div>")
            if len(day_tasks) > 4:
                chips.append(f"<div class='task-more'>+{len(day_tasks) - 4}건 더 있음</div>")
            count_badge = f"<span class='task-count'>{len(day_tasks)}</span>" if len(day_tasks) else ""
            html_parts.append(
                f"<div class='calendar-cell{muted}{today_class}'>"
                f"<div class='day-number'>{day.day}{count_badge}</div>"
                f"{''.join(chips)}"
                "</div>"
            )

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_calendar_tab(df: pd.DataFrame, today: date) -> None:
    st.subheader("달력으로 업무 확인")
    if df.empty:
        st.info("표시할 업무가 없습니다. 업무 입력 탭에서 샘플 또는 새 업무를 추가해 주세요.")
        return

    control_cols = st.columns([1, 1, 2])
    selected_day = control_cols[0].date_input("확인할 날짜", value=today, key="calendar_selected_day")
    month_anchor = control_cols[1].date_input("달력 월", value=selected_day.replace(day=1), key="calendar_month_anchor")
    repeat_filter = control_cols[2].multiselect(
        "달력에 표시할 반복주기",
        REPEAT_TYPES,
        default=["매일", "주간", "월간"],
        key="calendar_repeat_filter",
    )

    calendar_df = df[df["반복주기"].isin(repeat_filter)].copy()
    selected_year = month_anchor.year
    selected_month = month_anchor.month

    st.caption("마감일 기준으로 업무를 달력에 배치합니다. 필터는 사이드바 조건과 이 탭의 반복주기 조건을 함께 적용합니다.")
    render_month_calendar(calendar_df, selected_year, selected_month)

    week_start, week_end = get_week_range(selected_day)
    day_tasks = get_day_tasks(calendar_df, selected_day)
    week_tasks = get_week_tasks(calendar_df, selected_day)
    month_tasks = get_month_tasks(calendar_df, selected_year, selected_month)

    day_col, week_col, month_col = st.columns(3)
    day_col.metric("선택 날짜 업무", f"{len(day_tasks)}건")
    week_col.metric("선택 주 업무", f"{len(week_tasks)}건", f"{week_start:%m/%d}~{week_end:%m/%d}")
    month_col.metric("선택 월 업무", f"{len(month_tasks)}건", f"{selected_year}-{selected_month:02d}")

    detail_tabs = st.tabs(["일간 업무", "주간 업무", "월간 업무"])
    with detail_tabs[0]:
        st.write(f"{selected_day:%Y-%m-%d} 마감 업무")
        st.dataframe(day_tasks.sort_values(["중요도", "진행상태", "업무명"]), use_container_width=True, hide_index=True)
    with detail_tabs[1]:
        st.write(f"{week_start:%Y-%m-%d} ~ {week_end:%Y-%m-%d} 마감 업무")
        st.dataframe(week_tasks.sort_values(["마감일", "중요도", "업무명"]), use_container_width=True, hide_index=True)
    with detail_tabs[2]:
        st.write(f"{selected_year}년 {selected_month}월 마감 업무")
        st.dataframe(month_tasks.sort_values(["마감일", "중요도", "업무명"]), use_container_width=True, hide_index=True)


def render_mobile_tab(df: pd.DataFrame, today: date) -> None:
    st.subheader("휴대폰 간단 화면")
    st.caption("휴대폰에서는 넓은 표보다 오늘 할 일, 지연 업무, 빠른 상태 변경 위주로 사용하세요.")

    priority_tasks = get_today_priority_tasks(df, today)
    overdue_tasks = get_overdue_tasks(df, today)

    c1, c2 = st.columns(2)
    c1.metric("오늘 할 일", f"{len(priority_tasks)}건")
    c2.metric("지연 업무", f"{len(overdue_tasks)}건")

    st.markdown("#### 오늘 먼저 볼 업무")
    if priority_tasks.empty:
        st.success("오늘 우선 처리할 업무가 없습니다.")
    else:
        for original_index, row in priority_tasks.head(8).iterrows():
            with st.container(border=True):
                st.write(f"**{row['업무명']}**")
                st.write(f"{row['업무구분']} · {row['반복주기']} · 마감 {row['마감일']} · {row['진행상태']} · {row['중요도']}")
                if row["메모"]:
                    st.caption(row["메모"])
                new_status = st.selectbox(
                    "상태 변경",
                    STATUSES,
                    index=STATUSES.index(row["진행상태"]) if row["진행상태"] in STATUSES else 2,
                    key=f"mobile_status_{original_index}",
                )
                if st.button("이 업무 상태 저장", key=f"mobile_save_{original_index}", use_container_width=True):
                    st.session_state.tasks.loc[original_index, "진행상태"] = new_status
                    st.success("상태를 변경했습니다. Google Sheets를 쓰는 경우 사이드바에서 저장 버튼을 눌러 주세요.")
                    st.rerun()

    st.markdown("#### 마감일 지난 업무")
    if overdue_tasks.empty:
        st.success("마감일 지난 업무가 없습니다.")
    else:
        overdue_view = overdue_tasks.copy()
        overdue_view["지연일"] = overdue_view["마감일"].apply(lambda due: (today - due).days)
        st.dataframe(
            overdue_view[["업무명", "업무구분", "마감일", "지연일", "진행상태", "중요도"]],
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="✅", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
        [data-testid="stMetric"] {border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #ffffff;}
        div[data-testid="stTabs"] button {font-weight: 600;}
        .calendar-grid {display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px;}
        .calendar-weekdays {margin-top: 8px; margin-bottom: 6px; color: #4b5563; font-size: 13px; font-weight: 700; text-align: center;}
        .calendar-cell {min-height: 132px; border: 1px solid #d1d5db; border-radius: 8px; padding: 8px; background: #ffffff; overflow: hidden;}
        .calendar-cell.muted {background: #f9fafb; color: #9ca3af;}
        .calendar-cell.today-cell {border: 2px solid #2563eb;}
        .day-number {display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; font-weight: 700; color: #111827;}
        .task-count {min-width: 22px; height: 22px; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: 12px; text-align: center; line-height: 22px;}
        .task-chip {margin-top: 4px; padding: 4px 6px; border-radius: 6px; font-size: 12px; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-left: 4px solid #9ca3af; background: #f3f4f6; color: #111827;}
        .task-chip.todo {border-left-color: #dc2626; background: #fef2f2;}
        .task-chip.doing {border-left-color: #2563eb; background: #eff6ff;}
        .task-chip.done {border-left-color: #16a34a; background: #f0fdf4;}
        .task-chip.hold {border-left-color: #d97706; background: #fffbeb;}
        .task-more {margin-top: 4px; color: #4b5563; font-size: 12px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "tasks" not in st.session_state:
        st.session_state.tasks = create_sample_tasks()
    if "report_text" not in st.session_state:
        st.session_state.report_text = ""
    if "google_loaded" not in st.session_state:
        st.session_state.google_loaded = False
    if "google_sync_message" not in st.session_state:
        st.session_state.google_sync_message = ""

    if google_sheets_is_configured() and not st.session_state.google_loaded:
        try:
            loaded_tasks = load_tasks_from_google_sheets()
            if not loaded_tasks.empty:
                st.session_state.tasks = loaded_tasks
                st.session_state.google_sync_message = "Google Sheets에서 업무를 자동으로 불러왔습니다."
            else:
                st.session_state.google_sync_message = "Google Sheets가 비어 있어 샘플 업무로 시작합니다."
        except Exception as exc:
            st.session_state.google_sync_message = f"Google Sheets 자동 불러오기 실패: {exc}"
        finally:
            st.session_state.google_loaded = True

    logo = find_logo_file()
    header_cols = st.columns([1, 7]) if logo else None
    if logo and header_cols:
        header_cols[0].image(str(logo), width=92)
        header_cols[1].title(APP_TITLE)
        header_cols[1].caption(APP_SUBTITLE)
    else:
        st.title(APP_TITLE)
        st.caption(APP_SUBTITLE)

    today = date.today()
    st.info("이 버전은 OpenAI/Gemini API Key 없이 동작합니다. 홈택스, CRM, 4대보험 EDI, 고용산재, KISCON은 실제 연동이 아니라 업무 확인용 체크리스트로 관리합니다.")
    if st.session_state.google_sync_message:
        st.caption(st.session_state.google_sync_message)

    render_storage_panel()
    filtered_df = apply_filters(st.session_state.tasks)
    show_metrics(filtered_df, today)

    with st.expander("사용 순서", expanded=False):
        st.write("1. 샘플 업무를 불러오거나 직접 업무를 입력합니다.")
        st.write("2. 전체 업무 표에서 상태와 마감일을 확인하고 수정합니다.")
        st.write("3. 오늘 우선 처리, 지연, 미완료 업무를 확인합니다.")
        st.write("4. 대표님 보고 요약을 생성하고 CSV/TXT로 내려받습니다.")

    input_tab, mobile_tab, table_tab, calendar_tab, cycle_tab, priority_tab, overdue_tab, report_tab, chart_tab = st.tabs(
        ["업무 입력", "모바일", "전체 업무", "달력", "주기별 확인", "오늘 할 일", "지연/미완료", "보고 요약", "통계"]
    )

    with input_tab:
        left, right = st.columns([1, 1])
        with left:
            st.subheader("샘플 데이터")
            if st.button("샘플 업무 15건 다시 불러오기", use_container_width=True):
                st.session_state.tasks = create_sample_tasks()
                st.success("샘플 업무 목록을 다시 불러왔습니다.")
            st.download_button(
                "샘플 CSV 내려받기",
                data=to_csv_bytes(prepare_download_df(create_sample_tasks())),
                file_name="sample_tasks.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.subheader("파일 업로드")
            uploaded_file = st.file_uploader("CSV, Excel, TXT, MD 파일", type=["csv", "xlsx", "xls", "txt", "md"])
            if uploaded_file is not None:
                try:
                    uploaded_df = normalize_uploaded_dataframe(read_uploaded_file(uploaded_file))
                    st.success(f"{len(uploaded_df)}건을 읽었습니다. 아래 미리보기를 확인하세요.")
                    st.dataframe(uploaded_df, use_container_width=True, hide_index=True)
                    if st.button("업로드한 업무 목록에 반영", use_container_width=True):
                        add_tasks(uploaded_df)
                        st.success("업로드한 업무를 현재 목록에 추가했습니다.")
                except Exception as exc:
                    st.warning(f"파일을 읽는 중 문제가 있었습니다. 샘플 데이터로 계속 사용할 수 있습니다. 상세: {exc}")

        with right:
            st.subheader("업무 직접 입력")
            with st.form("manual_task_form", clear_on_submit=True):
                task_name = st.text_input("업무명", placeholder="예: 고객상담 전화 내용 CRM 등록")
                category = st.selectbox("업무구분", CATEGORIES)
                repeat_type = st.selectbox("반복주기", REPEAT_TYPES)
                owner = st.text_input("담당자", value="경영지원")
                due_date = st.date_input("마감일", value=today)
                status = st.selectbox("진행상태", STATUSES, index=2)
                importance = st.selectbox("중요도", IMPORTANCES)
                need_report = st.selectbox("대표님 보고 필요", REPORT_FLAGS)
                system = st.selectbox("관련시스템", SYSTEMS)
                memo = st.text_area("메모", placeholder="처리 기준이나 확인할 내용을 적어주세요.")
                submitted = st.form_submit_button("업무 추가", use_container_width=True)
            if submitted:
                if not task_name.strip():
                    st.warning("업무명을 입력해 주세요.")
                else:
                    new_task = pd.DataFrame(
                        [[task_name, category, repeat_type, owner, due_date, status, importance, need_report, system, memo]],
                        columns=TASK_COLUMNS,
                    )
                    add_tasks(new_task)
                    st.success("업무가 추가되었습니다.")

    with mobile_tab:
        render_mobile_tab(filtered_df, today)

    with table_tab:
        st.subheader("전체 업무 목록")
        edited = render_task_editor(filtered_df)
        if st.button("표 수정 내용 저장", use_container_width=True):
            remaining = st.session_state.tasks.drop(filtered_df.index, errors="ignore")
            st.session_state.tasks = normalize_uploaded_dataframe(pd.concat([remaining, edited], ignore_index=True))
            st.success("표에서 수정한 내용을 저장했습니다.")
        st.download_button(
            "전체 업무 CSV 다운로드",
            data=to_csv_bytes(prepare_download_df(st.session_state.tasks)),
            file_name=f"all_tasks_{today:%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "필터 적용 업무 CSV 다운로드",
            data=to_csv_bytes(prepare_download_df(filtered_df)),
            file_name=f"filtered_tasks_{today:%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with calendar_tab:
        render_calendar_tab(filtered_df, today)

    with cycle_tab:
        st.subheader("매일 / 주간 / 월간 / 일회성 업무")
        for repeat_type in REPEAT_TYPES:
            part = filtered_df[filtered_df["반복주기"] == repeat_type]
            with st.expander(f"{repeat_type} 업무: 전체 {len(part)}건 / 완료 {(part['진행상태'] == '완료').sum()}건 / 미완료 {(part['진행상태'] != '완료').sum()}건", expanded=repeat_type == "매일"):
                st.dataframe(part, use_container_width=True, hide_index=True)

    with priority_tab:
        st.subheader("오늘 우선 처리 추천")
        priority_tasks = get_today_priority_tasks(filtered_df, today)
        if priority_tasks.empty:
            st.success("오늘 기준으로 급한 업무가 없습니다.")
        else:
            st.dataframe(priority_tasks, use_container_width=True, hide_index=True)

    with overdue_tab:
        st.subheader("마감일 지난 업무")
        overdue_tasks = get_overdue_tasks(filtered_df, today)
        if overdue_tasks.empty:
            st.success("마감일이 지난 미완료 업무가 없습니다.")
        else:
            overdue_view = overdue_tasks.copy()
            overdue_view["지연일"] = overdue_view["마감일"].apply(lambda due: (today - due).days)
            st.dataframe(overdue_view.sort_values("지연일", ascending=False), use_container_width=True, hide_index=True)

        st.subheader("미완료 업무")
        incomplete_tasks = get_incomplete_tasks(filtered_df)
        st.dataframe(incomplete_tasks, use_container_width=True, hide_index=True)

    with report_tab:
        st.subheader("대표님 보고 요약")
        if st.button("보고 요약 생성", use_container_width=True):
            st.session_state.report_text = generate_report_summary(st.session_state.tasks, today)
        if not st.session_state.report_text:
            st.session_state.report_text = generate_report_summary(st.session_state.tasks, today)
        st.text_area("복사해서 보고할 내용", value=st.session_state.report_text, height=420)
        st.download_button(
            "보고 요약 TXT 다운로드",
            data=st.session_state.report_text.encode("utf-8-sig"),
            file_name=f"report_summary_{today:%Y%m%d}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with chart_tab:
        st.subheader("간단 통계")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("진행상태별")
            st.bar_chart(filtered_df["진행상태"].value_counts().reindex(STATUSES, fill_value=0))
        with c2:
            st.write("업무구분별")
            st.bar_chart(filtered_df["업무구분"].value_counts())
        with c3:
            st.write("반복주기별")
            st.bar_chart(filtered_df["반복주기"].value_counts().reindex(REPEAT_TYPES, fill_value=0))


if __name__ == "__main__":
    main()
