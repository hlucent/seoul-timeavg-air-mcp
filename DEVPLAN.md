# DEVPLAN.md — 서울시 기간별 시간평균 대기환경 정보 MCP

## 1. 개요

- **서비스명(공공 API 기준)**: 서울시 기간별 시간평균 대기환경 정보 (TimeAverageCityAir)
- **제공기관/부서**: 서울특별시 기후환경본부 대기정책과
- **플랫폼**: 서울 열린데이터광장 (OA-221)
- **저장소 이름**: `seoul-timeavg-air-mcp`
- **저장소 설명(Description 제안)**: "서울시 기간별 시간평균 대기환경(미세먼지·오존·이산화질소 등) 정보 조회 MCP 서버 — 서울 열린데이터광장 TimeAverageCityAir API"
- **라이선스**: 공공누리 1유형 (출처표시, 상업적 이용 및 변경 가능) — 코드 자체는 MIT

## 2. API 스펙 요약

### 2-1. 요청 URL 구조

```
http://openAPI.seoul.go.kr:8088/{KEY}/{TYPE}/TimeAverageCityAir/{START_INDEX}/{END_INDEX}/{MSRMT_DT}/{SAREA_NM}/{MSRSTN_NM}
```

- **인증키(KEY)는 쿼리 파라미터가 아니라 URL 경로 세그먼트다** (샘플 URL 확인:
  `http://openAPI.seoul.go.kr:8088/sample/xml/TimeAverageCityAir/1/5/201303061100`)
- 샘플 URL에는 SAREA_NM, MSRSTN_NM(선택 파라미터)이 생략된 형태만 나와 있음 → **선택 파라미터를
  포함할 때 경로 순서가 이 순서(START_INDEX, END_INDEX, MSRMT_DT, SAREA_NM, MSRSTN_NM)가 맞는지,
  아니면 완전히 생략(경로 세그먼트 자체를 안 붙임)해야 하는지 실측 필요**
- HTTPS 미지원 가능성 있음 (샘플이 http, 포트 8088) — HTTPS 시도 후 실패 시 HTTP로 폴백

### 2-2. 요청 파라미터

| 변수명 | 타입 | 설명 | 비고 |
|---|---|---|---|
| KEY | STRING(필수) | 인증키 | 경로 세그먼트, 32자리 hex |
| TYPE | STRING(필수) | 응답 형식 | xml, xmlf, xls, json 중 선택 |
| SERVICE | STRING(필수) | 서비스명 | 고정값 `TimeAverageCityAir` |
| START_INDEX | INTEGER(필수) | 요청 시작 위치 | 정수 |
| END_INDEX | INTEGER(필수) | 요청 종료 위치 | 정수. END - START ≤ 1000 (ERROR-336) |
| MSRMT_DT | STRING(필수) | 측정일시 | **YYYYMMDDHH 형식(24시간 단위)**. 예: `201303061100`(2013-03-06 11시) |
| SAREA_NM | STRING(선택) | 권역명 | 예: 도심권, 서북권 |
| MSRSTN_NM | STRING(선택) | 측정소명 | 예: 종로구, 용산구 |

- **주의**: 명세서 표기는 `YYYYMMDDHH2400`이나, 실제 샘플 값 `201303061100`은 자릿수 12자리
  (YYYYMMDDHHmm처럼 보이지만 분(mm)이 항상 00) → **실측 시 이 필드가 정확히 몇 자리이고 마지막
  2자리가 항상 00인지, 아니면 시(HH)까지만 10자리인지 확인 필요**

### 2-3. 응답 필드 (출력값)

| 필드명 | 설명 | 단위 |
|---|---|---|
| MSRMT_DT | 측정일시 | - |
| SAREA_CD | 권역코드 | - |
| SAREA_NM | 권역명 | - |
| MSRSTN_CD | 측정소코드 | - |
| MSRSTN_NM | 측정소명 | - |
| PM_HOUR | 미세먼지 1시간 | ㎍/㎥ |
| PM_ALDY | 미세먼지 24시간(일평균) | ㎍/㎥ |
| FPM | 초미세먼지 | ㎍/㎥ |
| OZON | 오존 | ppm |
| NTDX | 이산화질소농도 | ppm |
| CBMX | 일산화탄소농도 | ppm |
| SPDX | 아황산가스농도 | ppm |

응답 최상단 공통 구조 (실측 샘플 확인):
```xml
<TimeAverageCityAir>
  <list_total_count>25</list_total_count>
  <RESULT><CODE>INFO-000</CODE><MESSAGE>정상 처리되었습니다</MESSAGE></RESULT>
  <row>...</row>
  ...
</TimeAverageCityAir>
```

### 2-4. 에러 코드

| 코드 | 의미 |
|---|---|
| INFO-000 | 정상 처리 |
| INFO-100 | 인증키 유효하지 않음 |
| INFO-200 | 해당 데이터 없음 |
| ERROR-300 | 필수 값 누락 |
| ERROR-301 | TYPE 값 누락/오류 |
| ERROR-310 | SERVICE 값 오류 |
| ERROR-331 | START_INDEX 오류 |
| ERROR-332 | END_INDEX 오류 |
| ERROR-333 | 요청위치 값 타입 오류(정수 아님) |
| ERROR-334 | START_INDEX > END_INDEX |
| ERROR-335 | 샘플키(`sample`) 사용 시 1회 최대 5건 초과 |
| ERROR-336 | 일반 키 사용 시 1회 최대 1000건 초과 |
| ERROR-500 | 서버 오류 |
| ERROR-600 | DB 연결 오류 |
| ERROR-601 | SQL 오류 |

- 일부 에러 응답은 TYPE=json 요청에도 XML로 반환될 수 있음(과거 실측 사례) → JSON 우선, XML 폴백 파서 필수

## 3. 실측 필요 항목 (Claude Code가 로컬 테스트에서 반드시 확인)

1. **인증키 위치**: URL 경로 세그먼트가 맞는지, 쿼리 파라미터(`?KEY=`)는 통하지 않는지 확인
   (실패 시 ERROR-300 발생 예상 — 트러블슈팅 표 참고)
2. **MSRMT_DT 자릿수**: 10자리(YYYYMMDDHH)인지 12자리(YYYYMMDDHHmm, 분은 항상 00)인지 확인
3. **선택 파라미터(SAREA_NM, MSRSTN_NM) 처리 방식**:
   - 값을 넣지 않을 때 경로 세그먼트 자체를 생략해야 하는지, 빈 문자열로 채워야 하는지
   - 하나만 채우고 하나는 생략(부분 채움)했을 때 ERROR-500이 발생하는지 (과거 개별공시지가 API
     사례와 동일 패턴 의심 — 전부 채움/전부 생략만 되는지 조합별 테스트)
4. **TYPE=json 요청 시 실제로 JSON이 오는지**, 에러 응답만 XML로 오는지
5. **START_INDEX/END_INDEX가 실제 페이징에 사용되는지**, 아니면 최신 데이터만 반환하는지
6. **HTTPS 지원 여부** (샘플 URL이 http이므로 https 우선 시도 후 실패 시 http 폴백 로직 필요)
7. **list_total_count와 실제 row 개수가 END_INDEX - START_INDEX + 1과 일치하는지**

## 4. MCP 툴 설계 (최소 개수 원칙)

총 2개 툴로 설계.

### 4-1. `get_time_average_air`
- 설명: 기간별 시간평균 대기환경 정보를 조회한다 (미세먼지, 초미세먼지, 오존, 이산화질소,
  일산화탄소, 아황산가스). 측정일시(YYYYMMDDHH)를 기준으로 특정 시점의 전체/권역별/측정소별
  데이터를 반환한다.
- 파라미터:
  - `msrmt_dt` (str, 필수): 측정일시 YYYYMMDDHH (예: "2026081711")
  - `start_index` (int, 기본 1)
  - `end_index` (int, 기본 25 — 서울시 측정소 수 기준)
  - `sarea_nm` (str, 선택): 권역명
  - `msrstn_nm` (str, 선택): 측정소명
- docstring에 각 필드 단위(㎍/㎥, ppm) 명시 필수

### 4-2. `search_stations`
- 설명: 측정소명 또는 권역명으로 최근 대기환경 데이터를 검색한다. 특정 측정소/권역의 데이터만
  빠르게 조회하고 싶을 때 사용.
- 파라미터:
  - `msrmt_dt` (str, 필수)
  - `sarea_nm` (str, 선택)
  - `msrstn_nm` (str, 선택)
- 내부적으로 4-1 함수를 재사용하되 필수 파라미터 조합을 다르게 노출 (사용성 목적) —
  구현 시 `get_time_average_air`를 감싸는 얇은 래퍼로 구현해 코드 중복 최소화

## 5. 기술 스택 & 디렉토리 구조

```
seoul-timeavg-air-mcp/
├── requirements.txt      (fastmcp, httpx, python-dotenv)
├── seoul_api.py          (API 호출 + JSON/XML 파싱 + 에러코드 매핑)
├── server.py             (MCP 툴 정의 + rate limit 미들웨어 + stateless_http=True)
├── .env.example
├── .gitignore
├── Dockerfile
├── fly.toml              (표준 [http_service] 템플릿, 6절 참고)
├── LICENSE (MIT)
├── README.md
├── CLAUDE.md
└── DEVLOG.md
```

- 환경변수명: `SEOUL_API_KEY`
- 공개 서버(API 키 없이 커넥터 연결)이므로 2-7절 rate limit 미들웨어 필수 적용

## 6. 진행 순서

1. 사용자: 문서 4종을 `mcp-docs` 폴더에 저장 후 `run-new-mcp-project.bat` 실행
2. Claude Code: `CLAUDE.md` 기준 구현 → 실측 테스트 → git commit/push까지 → 정지
3. 사용자: PowerShell에서 `fly launch --no-deploy` → fly.toml 점검 → `fly secrets set` →
   `flyctl deploy`
4. 사용자: Claude.ai 커넥터에 `https://seoul-timeavg-air-mcp.fly.dev/mcp` 연결, 새 대화창에서 테스트

## 7. 사용자가 먼저 할 일

- 서울 열린데이터광장에서 `TimeAverageCityAir` 서비스 인증키 발급(또는 기존 키 재사용 가능 여부 확인)
- 문서 4종을 `C:\Users\hwang\Downloads\mcp-docs`에 저장
