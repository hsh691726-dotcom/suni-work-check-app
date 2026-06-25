from __future__ import annotations

import calendar
import io
import tomllib
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


APP_TITLE = "경영지원팀 업무일지"
APP_SUBTITLE = "달력에서 날짜를 누르고 바로 기록하는 경영지원 업무일지"

BASE_DIR = Path(__file__).parent
JOURNAL_WORKSHEET = "journal_entries"

GOOGLE_SHEETS_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

JOURNAL_COLUMNS = [
    "id",
    "업무일자",
    "업무명",
    "업무유형",
    "진행상태",
    "중요도",
    "금액",
    "거래처",
    "반복월간",
    "반복일",
    "메모",
    "작성일시",
    "수정일시",
]

TASK_TYPES = ["회계", "총무", "세무", "인사", "계약", "결제", "입출금", "증빙", "보고", "기타"]
STATUSES = ["예정", "진행중", "완료", "보류"]
PRIORITIES = ["높음", "보통", "낮음"]
REPEAT_FLAGS = ["아니오", "예"]

STATUS_COLORS = {
    "예정": "#2563eb",
    "진행중": "#d97706",
    "완료": "#16a34a",
    "보류": "#6b7280",
}


def read_local_secrets_file() -> dict:
    secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}
    return tomllib.loads(secrets_path.read_text(encoding="utf-8-sig"))


def get_google_sheet_settings() -> tuple[str, dict | None]:
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
    service_account_info = dict(secrets_data.get("gcp_service_account", {}))
    if not spreadsheet_id or not service_account_info:
        return "", None
    return spreadsheet_id, service_account_info


def google_sheets_is_configured() -> bool:
    spreadsheet_id, service_account_info = get_google_sheet_settings()
    return bool(spreadsheet_id and service_account_info)


def get_journal_worksheet():
    spreadsheet_id, service_account_info = get_google_sheet_settings()
    if not spreadsheet_id or not service_account_info:
        raise RuntimeError("Google Sheets 설정이 없습니다.")

    import gspread
    from google.oauth2.service_account import Credentials

    credentials = Credentials.from_service_account_info(service_account_info, scopes=GOOGLE_SHEETS_SCOPE)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(JOURNAL_WORKSHEET)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=JOURNAL_WORKSHEET, rows=500, cols=len(JOURNAL_COLUMNS) + 2)
        worksheet.update([JOURNAL_COLUMNS])
    return worksheet


def parse_date(value: object, fallback: date | None = None) -> date:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return fallback or date.today()
    return parsed.date()


def normalize_money(value: object) -> int:
    if value is None or pd.isna(value):
        return 0
    text = str(value).replace(",", "").replace("원", "").strip()
    amount = pd.to_numeric(text, errors="coerce")
    if pd.isna(amount):
        return 0
    return int(amount)


def normalize_choice(value: object, choices: list[str], default: str) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip()
    return text if text in choices else default


def normalize_entries(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in JOURNAL_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = ""

    prepared = prepared[JOURNAL_COLUMNS]
    today = date.today()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prepared["id"] = prepared["id"].apply(lambda value: str(value).strip() if str(value).strip() else str(uuid.uuid4()))
    prepared["업무일자"] = prepared["업무일자"].apply(lambda value: parse_date(value, today))
    prepared["업무명"] = prepared["업무명"].fillna("").astype(str).str.strip()
    prepared = prepared[prepared["업무명"] != ""].copy()
    prepared["업무유형"] = prepared["업무유형"].apply(lambda value: normalize_choice(value, TASK_TYPES, "기타"))
    prepared["진행상태"] = prepared["진행상태"].apply(lambda value: normalize_choice(value, STATUSES, "예정"))
    prepared["중요도"] = prepared["중요도"].apply(lambda value: normalize_choice(value, PRIORITIES, "보통"))
    prepared["금액"] = prepared["금액"].apply(normalize_money)
    prepared["거래처"] = prepared["거래처"].fillna("").astype(str).str.strip()
    prepared["반복월간"] = prepared["반복월간"].apply(lambda value: normalize_choice(value, REPEAT_FLAGS, "아니오"))
    prepared["반복일"] = prepared.apply(
        lambda row: int(row["업무일자"].day) if row["반복월간"] == "예" and not str(row["반복일"]).strip() else normalize_money(row["반복일"]),
        axis=1,
    )
    prepared["반복일"] = prepared["반복일"].clip(lower=0, upper=31)
    prepared["메모"] = prepared["메모"].fillna("").astype(str).str.strip()
    prepared["작성일시"] = prepared["작성일시"].fillna("").astype(str).str.strip().replace("", now)
    prepared["수정일시"] = prepared["수정일시"].fillna("").astype(str).str.strip().replace("", now)
    return prepared.reset_index(drop=True)


def empty_entries() -> pd.DataFrame:
    return pd.DataFrame(columns=JOURNAL_COLUMNS)


def load_entries_from_google_sheets() -> pd.DataFrame:
    worksheet = get_journal_worksheet()
    records = worksheet.get_all_records()
    if not records:
        worksheet.update([JOURNAL_COLUMNS])
        return empty_entries()
    return normalize_entries(pd.DataFrame(records))


def save_entries_to_google_sheets(df: pd.DataFrame) -> None:
    worksheet = get_journal_worksheet()
    prepared = normalize_entries(df)
    output = prepared.copy()
    output["업무일자"] = output["업무일자"].astype(str)
    values = [JOURNAL_COLUMNS] + output[JOURNAL_COLUMNS].fillna("").astype(str).values.tolist()
    worksheet.clear()
    worksheet.update(values)


def default_entries() -> pd.DataFrame:
    today = date.today()
    rows = [
        new_entry(today, "통장 입출금 확인", "입출금", "예정", "높음", 0, "", "아니오", "일일 자금 흐름 확인"),
        new_entry(today, "오늘 결제 요청 검토", "결제", "예정", "높음", 0, "", "아니오", "증빙 누락 여부 같이 확인"),
        new_entry(today.replace(day=10), "원천세 신고/납부 확인", "세무", "예정", "높음", 0, "홈택스", "예", "매월 10일 반복 업무"),
        new_entry(today.replace(day=25), "부가세/월마감 자료 정리", "회계", "예정", "높음", 0, "", "예", "매월 25일 반복 업무"),
        new_entry(today.replace(day=1), "월초 고정비 결제 일정 확인", "회계", "예정", "보통", 0, "", "예", "매월 1일 반복 업무"),
    ]
    return normalize_entries(pd.DataFrame(rows))


def new_entry(
    entry_date: date,
    title: str,
    task_type: str,
    status: str,
    priority: str,
    amount: int,
    vendor: str,
    repeat_monthly: str,
    memo: str,
) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "id": str(uuid.uuid4()),
        "업무일자": entry_date,
        "업무명": title.strip(),
        "업무유형": task_type,
        "진행상태": status,
        "중요도": priority,
        "금액": int(amount or 0),
        "거래처": vendor.strip(),
        "반복월간": repeat_monthly,
        "반복일": entry_date.day if repeat_monthly == "예" else 0,
        "메모": memo.strip(),
        "작성일시": now,
        "수정일시": now,
    }


def month_last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def materialize_entries_for_month(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    if df.empty:
        return empty_entries()

    normal = df[(df["반복월간"] != "예") & (pd.to_datetime(df["업무일자"]).dt.year == year) & (pd.to_datetime(df["업무일자"]).dt.month == month)].copy()
    recurring = df[df["반복월간"] == "예"].copy()
    generated_rows = []
    last_day = month_last_day(year, month)
    for _, row in recurring.iterrows():
        repeat_day = int(row["반복일"] or row["업무일자"].day)
        target_day = min(max(repeat_day, 1), last_day)
        generated = row.to_dict()
        generated["업무일자"] = date(year, month, target_day)
        generated["id"] = f"{row['id']}::{year}-{month:02d}"
        generated_rows.append(generated)

    generated_df = pd.DataFrame(generated_rows) if generated_rows else empty_entries()
    return normalize_entries(pd.concat([normal, generated_df], ignore_index=True))


def get_week_range(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    return start, start + timedelta(days=6)


def entries_for_day(df: pd.DataFrame, target: date) -> pd.DataFrame:
    month_df = materialize_entries_for_month(df, target.year, target.month)
    return month_df[month_df["업무일자"] == target].copy()


def entries_for_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    months = {(start.year, start.month), (end.year, end.month)}
    frames = [materialize_entries_for_month(df, year, month) for year, month in sorted(months)]
    month_df = normalize_entries(pd.concat(frames, ignore_index=True)) if frames else empty_entries()
    return month_df[(month_df["업무일자"] >= start) & (month_df["업무일자"] <= end)].copy()


def money_text(amount: int) -> str:
    return f"{int(amount):,}원" if amount else "-"


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    output = io.StringIO()
    prepared = df.copy()
    if "업무일자" in prepared.columns:
        prepared["업무일자"] = prepared["업무일자"].astype(str)
    prepared.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue().encode("utf-8-sig")


def add_entry(entry: dict) -> None:
    st.session_state.entries = normalize_entries(pd.concat([st.session_state.entries, pd.DataFrame([entry])], ignore_index=True))
    st.session_state.last_save_notice = "업무일지를 추가했습니다. 다른 기기에도 반영하려면 왼쪽 저장 버튼을 눌러 주세요."


def update_status(entry_id: str, status: str) -> None:
    mask = st.session_state.entries["id"] == entry_id
    if mask.any():
        st.session_state.entries.loc[mask, "진행상태"] = status
        st.session_state.entries.loc[mask, "수정일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.entries = normalize_entries(st.session_state.entries)


def update_entry(entry_id: str, updated: dict) -> None:
    mask = st.session_state.entries["id"] == entry_id
    if not mask.any():
        return

    for key, value in updated.items():
        if key in JOURNAL_COLUMNS and key != "id":
            st.session_state.entries.loc[mask, key] = value
    st.session_state.entries.loc[mask, "수정일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.entries = normalize_entries(st.session_state.entries)
    st.session_state.last_save_notice = "업무일지를 수정했습니다. 다른 기기에도 반영하려면 왼쪽 저장 버튼을 눌러 주세요."


def delete_entry(entry_id: str) -> None:
    st.session_state.entries = st.session_state.entries[st.session_state.entries["id"] != entry_id].copy()
    st.session_state.last_save_notice = "업무일지를 삭제했습니다. 다른 기기에도 반영하려면 왼쪽 저장 버튼을 눌러 주세요."


def clear_edit_state() -> None:
    st.session_state.editing_entry_id = ""
    st.session_state.editing_display_id = ""
    for key in [
        "edit_date_value",
        "edit_title_value",
        "edit_type_value",
        "edit_status_value",
        "edit_priority_value",
        "edit_repeat_value",
        "edit_amount_value",
        "edit_vendor_value",
        "edit_memo_value",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def render_storage_panel() -> None:
    with st.sidebar:
        st.header("저장")
        if google_sheets_is_configured():
            st.success("Google Sheets 연결됨")
            if st.button("Google Sheets에서 불러오기", use_container_width=True):
                try:
                    loaded = load_entries_from_google_sheets()
                    st.session_state.entries = loaded
                    st.session_state.loaded_from_google = True
                    st.success("업무일지를 불러왔습니다.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"불러오기 실패: {exc}")
            if st.button("현재 업무일지 저장", use_container_width=True, type="primary"):
                try:
                    save_entries_to_google_sheets(st.session_state.entries)
                    st.success("Google Sheets에 저장했습니다.")
                except Exception as exc:
                    st.error(f"저장 실패: {exc}")
        else:
            st.warning("Google Sheets 설정 없음")
            st.caption("로컬 화면에서는 사용할 수 있지만, 다른 기기와 자동 연동되지는 않습니다.")

        st.divider()
        st.header("보기")
        st.session_state.show_done = st.checkbox("완료 업무 표시", value=st.session_state.get("show_done", True))
        st.session_state.selected_types = st.multiselect("업무유형", TASK_TYPES, default=st.session_state.get("selected_types", TASK_TYPES))


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    if not st.session_state.get("show_done", True):
        filtered = filtered[filtered["진행상태"] != "완료"]
    selected_types = st.session_state.get("selected_types", TASK_TYPES)
    if selected_types:
        filtered = filtered[filtered["업무유형"].isin(selected_types)]
    return filtered


def render_dashboard(df: pd.DataFrame, today: date) -> None:
    week_start, week_end = get_week_range(today)
    today_df = entries_for_day(df, today)
    week_df = entries_for_range(df, week_start, week_end)
    month_df = materialize_entries_for_month(df, today.year, today.month)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘 할 일", f"{len(today_df[today_df['진행상태'] != '완료'])}건")
    c2.metric("이번주 할 일", f"{len(week_df[week_df['진행상태'] != '완료'])}건")
    c3.metric("이달 할 일", f"{len(month_df[month_df['진행상태'] != '완료'])}건")
    c4.metric("이달 완료", f"{len(month_df[month_df['진행상태'] == '완료'])}건")


def render_calendar(df: pd.DataFrame, year: int, month: int) -> None:
    month_df = materialize_entries_for_month(df, year, month)
    tasks_by_day = {day: group for day, group in month_df.groupby("업무일자")}
    cal = calendar.Calendar(firstweekday=0)
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    header_cols = st.columns(7)
    for col, label in zip(header_cols, weekdays):
        col.markdown(f"<div class='weekday'>{label}</div>", unsafe_allow_html=True)

    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for col, day in zip(cols, week):
            day_tasks = tasks_by_day.get(day, empty_entries())
            is_current_month = day.month == month
            is_selected = day == st.session_state.selected_date
            button_label = f"{day.day}"
            if len(day_tasks):
                button_label += f" · {len(day_tasks)}건"
            button_type = "primary" if is_selected else "secondary"
            if col.button(button_label, key=f"day_{day.isoformat()}", use_container_width=True, type=button_type, disabled=not is_current_month):
                st.session_state.selected_date = day
                st.rerun()

            if is_current_month and len(day_tasks):
                for _, row in day_tasks.head(3).iterrows():
                    color = STATUS_COLORS.get(row["진행상태"], "#6b7280")
                    repeat = " ↻" if row["반복월간"] == "예" else ""
                    col.markdown(
                        f"<div class='calendar-item' style='border-left-color:{color}'>{row['업무명']}{repeat}</div>",
                        unsafe_allow_html=True,
                    )
                if len(day_tasks) > 3:
                    col.caption(f"+{len(day_tasks) - 3}건")


def render_entry_form(selected_date: date) -> None:
    st.subheader(f"{selected_date:%Y-%m-%d} 업무 입력")
    with st.form("entry_form", clear_on_submit=True):
        title = st.text_input("업무명", placeholder="예: 세금계산서 발행 확인")
        c1, c2 = st.columns(2)
        task_type = c1.selectbox("업무유형", TASK_TYPES)
        status = c2.selectbox("진행상태", STATUSES)
        c3, c4 = st.columns(2)
        priority = c3.selectbox("중요도", PRIORITIES, index=1)
        repeat_monthly = c4.selectbox("매월 같은 날짜 반복", REPEAT_FLAGS)
        c5, c6 = st.columns(2)
        amount = c5.number_input("금액", min_value=0, step=1000, value=0)
        vendor = c6.text_input("거래처/관련처", placeholder="예: 홈택스, 거래처명")
        memo = st.text_area("메모", placeholder="증빙, 결제 방법, 확인할 내용 등을 적어주세요.")
        submitted = st.form_submit_button("이 날짜에 업무 추가", use_container_width=True, type="primary")

    if submitted:
        if not title.strip():
            st.warning("업무명을 입력해 주세요.")
        else:
            add_entry(new_entry(selected_date, title, task_type, status, priority, amount, vendor, repeat_monthly, memo))
            st.rerun()


def render_day_entries(df: pd.DataFrame, selected_date: date) -> None:
    st.subheader("선택한 날짜 업무")
    day_df = entries_for_day(df, selected_date)
    if day_df.empty:
        st.info("이 날짜에 기록된 업무가 없습니다. 오른쪽 입력창에서 바로 추가하세요.")
        return

    for _, row in day_df.sort_values(["중요도", "진행상태", "업무명"]).iterrows():
        with st.container(border=True):
            top = st.columns([5, 1.5])
            repeat_label = " · 매월 반복" if row["반복월간"] == "예" else ""
            top[0].markdown(f"**{row['업무명']}**")
            top[0].caption(f"{row['업무유형']} · {row['중요도']} · {row['진행상태']}{repeat_label}")
            top[1].write(money_text(row["금액"]))
            if row["거래처"]:
                st.write(f"거래처/관련처: {row['거래처']}")
            if row["메모"]:
                st.write(row["메모"])

            real_entry_id = str(row["id"]).split("::")[0]
            is_generated = "::" in str(row["id"])
            if is_generated:
                st.caption("반복 업무는 원본 반복 일정에서 자동 표시됩니다. 상태 변경은 원본 반복 업무에 적용됩니다.")

            action_cols = st.columns([2, 1.4, 1.4, 1])
            new_status = action_cols[0].selectbox(
                "상태",
                STATUSES,
                index=STATUSES.index(row["진행상태"]) if row["진행상태"] in STATUSES else 0,
                key=f"status_{row['id']}",
            )
            if action_cols[1].button("상태 저장", key=f"save_status_{row['id']}", use_container_width=True):
                update_status(real_entry_id, new_status)
                st.rerun()
            if action_cols[2].button("수정 열기", key=f"open_edit_{row['id']}", use_container_width=True):
                st.session_state.editing_entry_id = real_entry_id
                st.session_state.editing_display_id = str(row["id"])
                st.session_state.edit_date_value = row["업무일자"]
                st.session_state.edit_title_value = row["업무명"]
                st.session_state.edit_type_value = row["업무유형"]
                st.session_state.edit_status_value = row["진행상태"]
                st.session_state.edit_priority_value = row["중요도"]
                st.session_state.edit_repeat_value = row["반복월간"]
                st.session_state.edit_amount_value = int(row["금액"])
                st.session_state.edit_vendor_value = row["거래처"]
                st.session_state.edit_memo_value = row["메모"]
                st.rerun()
            if action_cols[3].button("삭제", key=f"delete_{row['id']}", use_container_width=True):
                delete_entry(real_entry_id)
                clear_edit_state()
                st.rerun()

            if st.session_state.get("editing_entry_id") == real_entry_id:
                with st.form(f"edit_form_{st.session_state.get('editing_display_id', row['id'])}"):
                    st.markdown("**업무 내용 수정**")
                    edit_date = st.date_input("업무일자", key="edit_date_value")
                    edit_title = st.text_input("업무명", key="edit_title_value")
                    edit_cols_1 = st.columns(2)
                    edit_type = edit_cols_1[0].selectbox(
                        "업무유형",
                        TASK_TYPES,
                        key="edit_type_value",
                    )
                    edit_status = edit_cols_1[1].selectbox(
                        "진행상태",
                        STATUSES,
                        key="edit_status_value",
                    )
                    edit_cols_2 = st.columns(2)
                    edit_priority = edit_cols_2[0].selectbox(
                        "중요도",
                        PRIORITIES,
                        key="edit_priority_value",
                    )
                    edit_repeat = edit_cols_2[1].selectbox(
                        "매월 같은 날짜 반복",
                        REPEAT_FLAGS,
                        key="edit_repeat_value",
                    )
                    edit_cols_3 = st.columns(2)
                    edit_amount = edit_cols_3[0].number_input(
                        "금액",
                        min_value=0,
                        step=1000,
                        key="edit_amount_value",
                    )
                    edit_vendor = edit_cols_3[1].text_input("거래처/관련처", key="edit_vendor_value")
                    edit_memo = st.text_area("메모", key="edit_memo_value")
                    save_cols = st.columns(2)
                    save_edit = save_cols[0].form_submit_button("수정 저장", use_container_width=True, type="primary")
                    cancel_edit = save_cols[1].form_submit_button("취소", use_container_width=True)

                if save_edit:
                    if not edit_title.strip():
                        st.warning("업무명을 입력해 주세요.")
                    else:
                        update_entry(
                            real_entry_id,
                            {
                                "업무일자": edit_date,
                                "업무명": edit_title,
                                "업무유형": edit_type,
                                "진행상태": edit_status,
                                "중요도": edit_priority,
                                "금액": edit_amount,
                                "거래처": edit_vendor,
                                "반복월간": edit_repeat,
                                "반복일": edit_date.day if edit_repeat == "예" else 0,
                                "메모": edit_memo,
                            },
                        )
                        clear_edit_state()
                        st.rerun()
                if cancel_edit:
                    clear_edit_state()
                    st.rerun()


def render_summary_lists(df: pd.DataFrame, today: date) -> None:
    week_start, week_end = get_week_range(today)
    tabs = st.tabs(["오늘", "이번주", "이달", "반복 업무"])
    views = [
        entries_for_day(df, today),
        entries_for_range(df, week_start, week_end),
        materialize_entries_for_month(df, today.year, today.month),
        df[df["반복월간"] == "예"].copy(),
    ]
    for tab, view in zip(tabs, views):
        with tab:
            if view.empty:
                st.info("표시할 업무가 없습니다.")
            else:
                show_cols = ["업무일자", "업무명", "업무유형", "진행상태", "중요도", "금액", "거래처", "반복월간", "메모"]
                table = view[show_cols].copy()
                table["업무일자"] = table["업무일자"].astype(str)
                table["금액"] = table["금액"].apply(lambda value: f"{int(value):,}" if int(value) else "")
                st.dataframe(table.sort_values(["업무일자", "중요도", "업무명"]), use_container_width=True, hide_index=True)


def render_export(df: pd.DataFrame) -> None:
    st.download_button(
        "업무일지 CSV 다운로드",
        data=to_csv_bytes(df),
        file_name=f"journal_entries_{date.today():%Y%m%d}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def initialize_state() -> None:
    if "entries" not in st.session_state:
        st.session_state.entries = empty_entries()
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()
    if "calendar_anchor" not in st.session_state:
        st.session_state.calendar_anchor = date.today().replace(day=1)
    if "loaded_from_google" not in st.session_state:
        st.session_state.loaded_from_google = False
    if "last_save_notice" not in st.session_state:
        st.session_state.last_save_notice = ""
    if "editing_entry_id" not in st.session_state:
        st.session_state.editing_entry_id = ""

    if google_sheets_is_configured() and not st.session_state.loaded_from_google:
        try:
            loaded = load_entries_from_google_sheets()
            st.session_state.entries = loaded
            st.session_state.loaded_from_google = True
            if loaded.empty:
                st.session_state.last_save_notice = "새 업무일지 시트가 비어 있습니다. 달력에서 날짜를 눌러 업무를 추가하세요."
            else:
                st.session_state.last_save_notice = "Google Sheets에서 업무일지를 자동으로 불러왔습니다."
        except Exception as exc:
            st.session_state.entries = empty_entries()
            st.session_state.loaded_from_google = True
            st.session_state.last_save_notice = f"Google Sheets 자동 불러오기 실패: {exc}"


def render_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1480px;}
        [data-testid="stMetric"] {border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; background: #ffffff;}
        .weekday {font-weight: 700; text-align: center; color: #475569; padding: 4px 0 8px;}
        .calendar-item {font-size: 12px; line-height: 1.25; margin: 4px 0; padding: 4px 6px; border-left: 4px solid #2563eb; border-radius: 6px; background: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
        div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 8px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🗓️", layout="wide")
    render_styles()
    initialize_state()
    render_storage_panel()

    today = date.today()
    entries = apply_filters(st.session_state.entries)

    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    if st.session_state.last_save_notice:
        st.info(st.session_state.last_save_notice)

    render_dashboard(entries, today)

    nav_cols = st.columns([1, 2, 1, 1])
    if nav_cols[0].button("이전 달", use_container_width=True):
        anchor = st.session_state.calendar_anchor
        prev_month = anchor.month - 1 or 12
        prev_year = anchor.year - 1 if anchor.month == 1 else anchor.year
        st.session_state.calendar_anchor = date(prev_year, prev_month, 1)
        st.rerun()

    anchor = st.session_state.calendar_anchor
    nav_cols[1].markdown(f"### {anchor.year}년 {anchor.month}월")

    if nav_cols[2].button("오늘", use_container_width=True):
        st.session_state.selected_date = today
        st.session_state.calendar_anchor = today.replace(day=1)
        st.rerun()

    if nav_cols[3].button("다음 달", use_container_width=True):
        next_month = anchor.month + 1 if anchor.month < 12 else 1
        next_year = anchor.year + 1 if anchor.month == 12 else anchor.year
        st.session_state.calendar_anchor = date(next_year, next_month, 1)
        st.rerun()

    left, right = st.columns([1.35, 1])
    with left:
        render_calendar(entries, anchor.year, anchor.month)
        st.divider()
        render_summary_lists(entries, today)

    with right:
        render_entry_form(st.session_state.selected_date)
        st.divider()
        render_day_entries(entries, st.session_state.selected_date)
        st.divider()
        render_export(entries)


if __name__ == "__main__":
    main()
