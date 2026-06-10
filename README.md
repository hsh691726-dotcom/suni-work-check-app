# 경영지원 업무 체크 도우미

인테리어 회사 경영지원 담당자가 매일 확인해야 하는 경리, 총무, 인사, 공무, 고객상담, CRM, 홈택스, 4대보험, 고용산재, KISCON 관련 업무를 한 화면에서 정리하는 Streamlit 앱입니다.

현재 버전은 OpenAI, Gemini, 외부 CRM, 홈택스, 4대보험 EDI, 고용산재, KISCON과 직접 연동하지 않습니다. API Key 없이 샘플 데이터, 직접 입력, CSV/Excel/TXT 업로드만으로 바로 실행됩니다.

집 노트북, 사무실 PC, 휴대폰에서 함께 쓰려면 Streamlit Cloud에 앱을 올리고 Google Sheets를 업무 저장소로 연결하는 방식을 권장합니다.

## 주요 기능

- 샘플 업무 15건 불러오기
- 업무 직접 입력
- CSV, Excel, TXT, MD 파일 업로드 및 pandas 기반 읽기
- 업무명, 업무구분, 반복주기, 담당자, 마감일, 진행상태, 중요도, 대표님보고, 관련시스템, 메모 관리
- 전체 업무 표 수정
- 반복주기, 업무구분, 진행상태, 중요도, 대표님 보고 여부 필터
- 매일, 주간, 월간, 일회성 업무 탭 분류
- 달력에서 일간, 주간, 월간 업무 확인
- 오늘 우선 처리 업무 자동 정리
- 마감일 지난 업무 자동 표시
- 미완료, 진행중, 보류 업무 별도 표시
- 대표님 보고 요약문 자동 생성
- 전체 업무 CSV, 필터 적용 CSV, 보고 요약 TXT 다운로드
- 진행상태별, 업무구분별, 반복주기별 막대 그래프
- 프로젝트 폴더 또는 `assets` 폴더에 로고 이미지가 있으면 자동 표시
- Google Sheets 불러오기/저장 버튼
- 휴대폰에서 보기 쉬운 `모바일` 탭

## 설치 방법

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행 방법

```powershell
streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

브라우저에서 아래 주소로 접속합니다.

```text
http://127.0.0.1:8501
```

## 사용 방법

1. `업무 입력` 탭에서 `샘플 업무 15건 다시 불러오기`를 누르거나 업무를 직접 입력합니다.
2. 휴대폰에서는 `모바일` 탭에서 오늘 할 일과 지연 업무를 먼저 확인합니다.
3. CSV, Excel, TXT, MD 파일이 있으면 업로드 후 미리보기를 확인하고 업무 목록에 반영합니다.
4. `전체 업무` 탭에서 상태, 마감일, 중요도 등을 수정하고 저장합니다.
5. 사이드바 필터로 필요한 업무만 좁혀 봅니다.
6. `달력` 탭에서 선택한 날짜, 주간 범위, 월간 업무를 확인합니다.
7. `오늘 할 일`, `지연/미완료`, `보고 요약`, `통계` 탭에서 결과를 확인합니다.
8. 필요한 결과는 CSV 또는 TXT로 다운로드합니다.

Google Sheets를 연결한 뒤에는 사이드바의 `저장소` 영역에서 `Google Sheets에서 새로고침`, `현재 업무를 Google Sheets에 저장` 버튼을 사용합니다.

## 집 노트북, 사무실 PC, 휴대폰에서 함께 쓰는 방식

3기기에서 같은 업무 목록을 쓰려면 아래 구조가 가장 쉽습니다.

```text
집 노트북 / 사무실 PC / 휴대폰
        ↓
Streamlit Cloud에 올린 앱
        ↓
Google Sheets 업무 목록
```

이 방식에서는 앱 주소 하나만 알면 됩니다.

```text
https://내앱이름.streamlit.app
```

휴대폰에서도 이 주소로 들어가면 `모바일` 탭에서 오늘 할 일과 지연 업무를 확인할 수 있습니다.

## Google Sheets 연결 준비

왕초보 기준으로 순서는 아래처럼 이해하면 됩니다.

1. Google Sheets에 새 스프레드시트를 만듭니다.
2. 첫 번째 시트 이름을 `tasks`로 바꿉니다.
3. 첫 줄에 아래 컬럼명을 넣습니다.

```text
업무명, 업무구분, 반복주기, 담당자, 마감일, 진행상태, 중요도, 대표님보고, 관련시스템, 메모
```

4. Google Cloud에서 서비스 계정을 만들고 JSON 키를 발급합니다.
5. Google Sheets의 공유 버튼을 눌러 서비스 계정 이메일에 편집 권한을 줍니다.
6. Streamlit Cloud의 앱 설정에서 `Secrets`에 `.streamlit/secrets.toml.example` 형식으로 값을 넣습니다.

구글시트 ID는 주소에서 확인할 수 있습니다.

```text
https://docs.google.com/spreadsheets/d/여기가_스프레드시트_ID/edit
```

로컬에서 테스트하려면 `.streamlit/secrets.toml.example`을 복사해서 `.streamlit/secrets.toml`로 만들고 실제 값을 넣습니다.

주의: `.streamlit/secrets.toml`은 비밀번호 같은 파일입니다. GitHub에 올리면 안 됩니다.

## Streamlit Cloud 배포 준비

배포할 때 필요한 파일은 아래입니다.

```text
app.py
requirements.txt
README.md
sample_tasks.csv
.streamlit/secrets.toml.example
```

기본 흐름은 이렇습니다.

1. GitHub에 새 저장소를 만듭니다.
2. 이 프로젝트 파일을 GitHub에 올립니다.
3. Streamlit Community Cloud에 로그인합니다.
4. `New app`을 누릅니다.
5. GitHub 저장소를 선택합니다.
6. Main file path를 `app.py`로 지정합니다.
7. 앱 설정의 `Secrets`에 Google Sheets 정보를 넣습니다.
8. 배포된 주소를 집 노트북, 사무실 PC, 휴대폰에서 같이 사용합니다.

Google Sheets 설정을 아직 못 해도 앱은 샘플 데이터와 CSV 방식으로 실행됩니다. 다만 3기기 자동 연동은 Google Sheets 설정 후부터 제대로 됩니다.

## 업로드 파일 준비 방법

권장 컬럼은 아래와 같습니다.

| 컬럼명 | 설명 | 예시 |
| --- | --- | --- |
| 업무명 | 처리할 업무 이름 | 고객상담 전화 내용 CRM 등록 |
| 업무구분 | 경리, 총무, 인사 등 | CRM |
| 반복주기 | 매일, 주간, 월간, 일회성 | 매일 |
| 담당자 | 업무 담당자 | 경영지원 |
| 마감일 | 마감 날짜 | 2026-06-10 |
| 진행상태 | 완료, 진행중, 미완료, 보류 | 미완료 |
| 중요도 | 높음, 보통, 낮음 | 높음 |
| 대표님보고 | 예, 아니오 | 예 |
| 관련시스템 | 홈택스, CRM 앱, KISCON 등 | CRM 앱 |
| 메모 | 추가 설명 | 상담 누락 방지 |

컬럼명이 조금 달라도 최대한 자동 매핑합니다. 예를 들어 `구분`은 `업무구분`, `상태`는 `진행상태`, `보고`는 `대표님보고`, `시스템`은 `관련시스템`으로 인식합니다.

필수 컬럼이 부족해도 앱이 멈추지 않도록 기본값을 채웁니다. 날짜 변환에 실패하면 오늘 날짜를 사용합니다.

## 샘플 업무 목록

`sample_tasks.csv`에 기본 샘플 업무가 들어 있습니다. 앱 안에서도 같은 데이터를 불러오거나 다운로드할 수 있습니다.

샘플에는 입출금 내역 확인, 통장 결제요청 확인, 텔레그램 결제요청 확인 및 입금 처리, 홈택스 지출 입력 확인, 고객상담 전화 내용 CRM 등록, 미팅 일정 CRM 등록, 4대보험 취득신고 확인, 고용산재 개시신고 확인, KISCON 등록 일정 확인 등이 포함됩니다.

## 로고 이미지 교체 방법

프로젝트 폴더 또는 `assets` 폴더에 `logo`, `로고`, `brand`, `icon`이 포함된 이름의 PNG, JPG, JPEG, WEBP 파일을 넣으면 앱 상단에 자동 표시됩니다.

예시:

```text
assets/logo.png
brand_logo.jpg
```

로고 파일이 없어도 앱은 정상 실행되며 텍스트 제목만 표시됩니다.

## 자주 발생할 수 있는 문제

- `ModuleNotFoundError: streamlit`: `pip install -r requirements.txt`를 다시 실행합니다.
- `ModuleNotFoundError: gspread`: `pip install -r requirements.txt`를 다시 실행합니다.
- Excel 업로드 오류: `openpyxl`이 설치되어 있는지 확인합니다.
- 한글 CSV가 깨짐: 앱이 UTF-8과 CP949를 순서대로 시도합니다. 그래도 깨지면 Excel에서 UTF-8 CSV로 다시 저장해 주세요.
- 브라우저가 자동으로 열리지 않음: 직접 `http://127.0.0.1:8501`로 접속합니다.
- 업로드 컬럼명이 맞지 않음: README의 권장 컬럼명에 맞추면 가장 안정적입니다.
- Google Sheets 저장 실패: 서비스 계정 이메일이 Google Sheets에 공유되어 있는지 확인합니다.
- Streamlit Cloud에서 Google Sheets 오류: Secrets에 `private_key` 줄바꿈이 `\n` 형태로 들어갔는지 확인합니다.

## 나중에 추가하면 좋은 기능

- 실제 CRM, 홈택스, 4대보험 EDI, 고용산재, KISCON 연동
- 로그인과 권한 관리
- 더 강한 권한 관리와 데이터베이스 저장
- AI API 기반 보고문 고도화
- 담당자별 알림, 카카오톡/문자 발송
- 반복 업무 자동 생성
- 앱 구조를 여러 파일로 분리
