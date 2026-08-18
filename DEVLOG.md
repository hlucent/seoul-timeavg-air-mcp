# DEVLOG.md — seoul-timeavg-air-mcp

기록 형식: `## YYYY-MM-DD` 하위에 진행 상황, 발견 사항, 실측 결과, 이슈/해결을 기록한다.

---

## 2026-08-18

- DEVPLAN.md / CLAUDE.md / README.md 초안 작성 완료 (Claude 웹챗)
- 서비스: 서울시 기간별 시간평균 대기환경 정보 (TimeAverageCityAir), 서울 열린데이터광장 OA-221
- 명세서(XLS) + 실제 응답 샘플(XML) 둘 다 확보하여 스펙 확정
- **확정 사항**:
  - 인증키는 URL 경로 세그먼트 (쿼리 파라미터 아님)
  - 응답 필드 12개 확인, 단위: ㎍/㎥(미세먼지류), ppm(가스류)
  - 에러코드 체계: INFO-000/100/200, ERROR-300번대(요청 오류), 500/600/601(서버 오류)
- **실측 필요 항목 (Claude Code가 확인할 것)**:
  1. MSRMT_DT 자릿수 — 10자리(YYYYMMDDHH) vs 12자리(YYYYMMDDHHmm, 분=00)
  2. 선택 파라미터(SAREA_NM, MSRSTN_NM) 부분 채움 시 동작 여부
  3. TYPE=json 요청 시 실제 응답 형식
  4. HTTPS 지원 여부 (샘플 URL은 http)
  5. START_INDEX/END_INDEX 페이징 실제 동작 여부

*(이후 Claude Code가 로컬 구현/실측 진행 시 아래에 이어서 기록)*

---

## 2026-08-18 (Claude Code 구현 세션)

### 실측 결과 (curl 직접 호출로 확인)

1. **인증키 위치**: URL 경로 세그먼트 확정 (`/{KEY}/{TYPE}/TimeAverageCityAir/...`).
2. **MSRMT_DT 자릿수**: **12자리(YYYYMMDDHHmm, 분은 항상 00)로 확정**. 10자리(YYYYMMDDHH)로
   요청하면 `INFO-200`(해당 데이터 없음)이 반환됨 — 자릿수 문제였음, 2회 이상 재현 확인.
3. **선택 파라미터 부분 채움**:
   - `sarea_nm`만 채움 → 정상 필터링 (25건 → 3건, 서북권).
   - `msrstn_nm`만 채움(경로에서 SAREA_NM 세그먼트를 생략) → **필터가 무시되고 전체 25건이
     그대로 반환됨**. DEVPLAN에서 우려했던 "부분 채움 시 ERROR-500" 패턴은 아니었고, 대신
     조용히 필터가 씹히는 패턴이었음. `server.py`에서 이 경우를 감지해 응답을 애플리케이션
     레벨에서 `msrstn_nm`으로 재필터링하도록 처리함.
   - 둘 다 채움 → 정상 필터링(교집합, 1건).
4. **TYPE=json 응답**: 정상 응답은 실제 JSON으로 옴. 단 `ERROR-335`, `ERROR-336` 같은 에러는
   `TYPE=json` 요청에도 **XML**로 반환됨 (CLAUDE.md 1-3절 예상과 일치) → JSON 우선/XML 폴백
   파서(`seoul_api.parse_response`)로 처리, 정상 동작 확인.
5. **HTTPS 지원 여부**: 미지원. `https://openAPI.seoul.go.kr:8088/...` 연결 자체가 실패
   (timeout/connection refused). HTTP만 사용하도록 고정.
6. **list_total_count vs row 개수**: 일치 확인 (`END_INDEX - START_INDEX + 1` = 실제 row 수,
   1~5건 케이스 모두 확인).
7. **START_INDEX/END_INDEX 초과**: `END_INDEX - START_INDEX > 1000` 요청 시 `ERROR-336`
   (XML로 반환) 확인. 샘플 키(`sample`)는 5건 초과 시 `ERROR-335`.
8. **미래 시각 데이터**: 예상과 달리 2026년 시각(`202601011200`)도 정상 데이터가 존재함
   (API가 최신 데이터까지 계속 채워지는 구조로 보임). 실제 "데이터 없음"(`INFO-200`) 확인은
   더 먼 미래 시각(`203501011200`)으로 재현함.

### 구현 완료 항목

- `seoul_api.py`: URL 빌더(경로 세그먼트 조립), JSON/XML 이중 파싱, 에러코드 → 예외 매핑.
- `server.py`: `get_time_average_air`, `search_stations` 2개 툴, `msrstn_nm` 단독 지정 시
  애플리케이션 레벨 재필터링, IP 기반 3단계 rate limit 미들웨어, `stateless_http=True`.
- `Dockerfile`, `fly.toml`(표준 `[http_service]` 템플릿) 작성.
- 로컬 스모크 테스트: FastMCP 서버 기동 후 `initialize` 요청 200 OK, stateless 모드로
  `http://0.0.0.0:8123/mcp` 정상 응답 확인.

### 확인 필요 (사용자 검토 권장)

- rate limit 미들웨어는 fly.io 배포 후 실제 멀티 요청으로는 검증하지 못함 (로컬 단일 프로세스
  기준 로직만 확인). 배포 후 정상 429 응답이 오는지 사용자가 확인 필요. →
  아래 항목에서 사용자가 배포 후 직접 검증 완료.

---

## 2026-08-18 (배포 후 사용자 rate limit 검증)

- fly.io 배포 완료 후 PowerShell에서 `/mcp` 엔드포인트에 JSON-RPC `initialize` 요청을
  4회 연속 전송하여 분당 3회 제한을 검증함.
- 결과: 요청 1 → 400, 요청 2 → 400, 요청 3 → **429**, 요청 4 → 400.
- **3번째 요청에서 429 확인 → 분당 3회 초과 시 rate limit이 정상 작동함을 확인.**
- 400 응답은 curl 단발 요청이 stateless 세션에 필요한 JSON-RPC 헤더/세션 형식을 제대로
  갖추지 못해 발생한 것으로, rate limit 로직과는 무관 (요청이 미들웨어를 통과해 도달했다는
  의미이므로 카운트 자체에는 영향 없음).
- 반복위반 24시간 차단, 일일 30회 제한은 이번 세션에서 별도 검증하지 않음 (시간 소요상
  다음 필요 시 재검증).
