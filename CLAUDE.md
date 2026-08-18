# CLAUDE.md — seoul-timeavg-air-mcp

Claude Code는 이 문서만 먼저 읽고 시작한다. 다른 문서(README, DEVLOG) 재탐색 금지.
DEVPLAN.md는 API 스펙과 툴 설계를 위해 참고하되, 스펙 재해석/재설계는 하지 않는다.

## 0. 절대 규칙

- 웹서치 금지. API 스펙은 DEVPLAN.md에 이미 있다.
- 불확실하면 추측성 재설계 대신 기본값 1개로 구현 후 DEVLOG.md에 "확인 필요"로 기록한다.
- 동일 오류 최대 3회까지만 재시도. 3회 실패 시 기록하고 사용자에게 보고한다.
- **네 역할은 "코드 구현 + 로컬 실측 테스트"까지다.** `fly launch`, `fly secrets set`,
  `flyctl deploy`, `fly logs` 등 fly.io 관련 명령은 절대 스스로 실행하지 않는다.
- 배포 준비(코드 구현, 로컬 테스트, git commit/push)가 끝나면 아래 "정지 시점"에서 멈추고,
  "사용자 안내 문구"를 그대로 출력한다.

## 1. 기술적으로 반드시 적용할 것

### 1-1. `.env`
- 항상 UTF-8(BOM 없음)으로 저장한다. BOM이 있으면 `python-dotenv`가 키를 못 읽는 사례가 있었다.

### 1-2. `server.py`의 `mcp.run()`
```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
```
`stateless_http=True`를 반드시 포함한다. 빠뜨리면 fly.io 멀티머신 환경에서 세션 404가
발생하고 Claude.ai 커넥터에서 "사용 가능한 도구 없음"으로 보인다.

### 1-3. 응답 파싱 — JSON 우선, XML 폴백 필수
정상 응답은 TYPE에 따라 오지만, 일부 에러 응답은 TYPE=json 요청에도 XML로 돌아올 수 있다.
`response.json()`이 실패하면 정규식으로 `<CODE>`/`<MESSAGE>` 패턴을 추출하는 폴백을 구현한다.

```python
import re

def parse_response(text: str) -> dict:
    try:
        return json.loads(text)
    except ValueError:
        code_match = re.search(r"<CODE>(.*?)</CODE>", text)
        msg_match = re.search(r"<MESSAGE>(.*?)</MESSAGE>", text)
        return {
            "RESULT": {
                "CODE": code_match.group(1) if code_match else "UNKNOWN",
                "MESSAGE": msg_match.group(1) if msg_match else text[:200],
            }
        }
```

정상 XML 응답(TYPE=xml 요청 시)도 파싱해야 하므로, XML 파싱은 `xml.etree.ElementTree`로
`<row>` 반복 요소를 순회하는 로직을 별도로 둔다. 기본 TYPE은 `json`으로 요청하되, JSON 파싱
실패 시 XML 파서로 재시도하는 이중 폴백 구조를 권장한다.

### 1-4. 인증키는 URL 경로 세그먼트
쿼리 파라미터(`?KEY=`)가 아니라 경로 세그먼트다:
```
http://openAPI.seoul.go.kr:8088/{KEY}/{TYPE}/TimeAverageCityAir/{START}/{END}/{MSRMT_DT}
```
ERROR-300(필수값 누락)이 반복되면 이 구조부터 의심한다.

## 2. API 키 취급 원칙

- 실제 키 값은 코드에 하드코딩하지 않고 항상 `os.environ`으로 읽는다.
- `.env`를 갱신했다는 말을 들으면, 재테스트 전에 실제로 값이 바뀌었는지 파일 크기나 앞 몇 글자로
  비교 확인한다.
- 키를 표준출력에 그대로 찍지 않는다. 필요하면 앞 4자리 + `...` + 길이만 출력한다.
- 재테스트 요청을 받으면 "이전과 동일한 키인지, 새 키인지" 먼저 확인한다.

## 3. 작업 순서

1. `requirements.txt` (`fastmcp`, `httpx`, `python-dotenv`)
2. `seoul_api.py` — API 호출 + JSON/XML 이중 파싱 + 에러코드 매핑
   - 인증키를 경로 세그먼트로 조립하는 URL 빌더 함수
   - MSRMT_DT 자릿수(10자리 vs 12자리) 실측 확인 후 확정
3. `server.py` — 툴 2개 정의(`get_time_average_air`, `search_stations`),
   docstring에 각 필드 단위(㎍/㎥, ppm) 명시, `stateless_http=True` 필수,
   아래 5절 rate limit 미들웨어 포함 (이 서버는 API 키 없이 공개하는 서버임)
4. `.env.example`, `.gitignore`
5. 로컬 테스트 (실제 키로 각 툴 호출)
   - **가장 먼저 URL 구조(키의 경로 위치)를 확인한다.** ERROR-300이 계속 나면 키 위치부터 의심.
   - **선택 파라미터(SAREA_NM, MSRSTN_NM) 조합별 실측 필수**: 둘 다 생략 / 하나만 채움(부분 채움)
     / 둘 다 채움 — 각각 시도해서 어떤 조합이 정상 동작하는지 확인 (부분 채움에서 ERROR-500이
     나는 패턴이 과거 다른 서울시 API에서 실제로 있었음, 6절 "실측 필요 항목 처리 절차" 참고)
   - **MSRMT_DT 자릿수 확인**: 10자리(YYYYMMDDHH)와 12자리(YYYYMMDDHHmm, 분=00) 둘 다 시도
   - list_total_count와 실제 반환 row 수가 END_INDEX - START_INDEX + 1과 일치하는지 확인
   - TYPE=json 요청 시 실제 JSON이 오는지, HTTPS 지원 여부도 함께 확인
6. FastMCP 서버 스모크 테스트 (initialize 요청까지만)
7. `Dockerfile`, `fly.toml` — 아래 4절 표준 템플릿을 직접 작성 (fly launch 결과를 기다리지 않음)
8. README/DEVLOG 갱신 — 실측으로 확인된 제약사항을 실제 동작 기준으로 정확히 기술
9. `git add/commit/push`까지 수행 (push는 자동 진행 가능 — 본인 소유 저장소 백업일 뿐)
10. **여기서 정지** — 아래 "사용자 안내 문구" 출력

## 4. 표준 fly.toml 템플릿

```toml
app = 'seoul-timeavg-air-mcp'
primary_region = 'nrt'

[build]
  dockerfile = 'Dockerfile'

[env]
  PORT = '8000'

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

  [http_service.concurrency]
    type = 'connections'
    hard_limit = 256
    soft_limit = 200

[[vm]]
  memory = '1gb'
  cpu_kind = 'shared'
  cpus = 1
  memory_mb = 1024
```

구버전 `[[services]]` 방식은 TLS 자동 프로비저닝을 트리거하지 않으므로 절대 사용하지 않는다.

## 5. MCP 서버 보안 정책 (필수 적용 — API 키 없이 공개)

3단계 IP 기반 rate limit을 `server.py`(또는 별도 미들웨어 파일)에 구현한다.

1. 분당 호출 제한: 같은 IP 기준 60초 슬라이딩 윈도우 내 3회 초과 시 429
2. 반복 위반 시 임시 차단: 1시간 내 429 응답 5회 이상 IP는 24시간 완전 차단
3. 일일 총량 제한: IP당 24시간(rolling) 총 호출 30회 초과 시 429

- 저장 방식은 in-memory(dict)로 충분. 외부 저장소(Redis 등) 도입 금지.
- IP는 `X-Forwarded-For` 헤더에서 추출, 없으면 remote address 사용.
- 429 응답에 원인 메시지 포함 (예: "Rate limit exceeded. Try again later.").
- `stateless_http=True`와는 별개 — IP 카운터가 멀티 머신 환경에서 완벽히 동기화되지 않아도 무방.
- FastMCP + Starlette 조합에서는 `BaseHTTPMiddleware` 서브클래싱 후
  `mcp.run(..., middleware=[Middleware(RateLimitMiddleware)])` 형태로 `starlette.middleware.Middleware`로
  감싸서 전달한다 (클래스를 직접 리스트에 넣으면 타입 오류 발생).

## 6. 실측 필요 항목 처리 절차

명세서와 실제 API 동작이 다르다는 게 확인되면:

1. 같은 조건으로 최소 2회 이상 재현 확인 (우연 배제)
2. 코드/URL 구조 문제인지 API 자체 특이 동작인지 원인 분리 (sample 키 등으로 최소 재현 시도)
3. 사용자에게 묻지 말고 코드 레벨에서 확인 가능한 가설부터 순서대로 검증 (3회 재시도 원칙 내)
4. DEVLOG.md에 무엇을 시도했고 무엇이 확인됐는지 기록
5. 발견된 제약을 코드가 미리 걸러서 명확한 에러 메시지로 안내하도록 사전 검증 로직 추가
6. README.md/DEVPLAN.md를 실제 동작 기준으로 갱신 (이 갱신도 커밋 대상에 포함)

## 7. 하지 말 것

- 툴 개수를 DEVPLAN 범위(2개)보다 늘리지 않기
- 인증키 하드코딩 금지
- `stateless_http=True` 누락 금지
- `fly launch` / `fly secrets set` / `flyctl deploy` / `fly logs` 자동 실행 금지
- rate limit 미들웨어 누락 금지
- fly.toml을 구버전 `[[services]]` 방식으로 두지 않기

## 8. 정지 시점 — 사용자 안내 문구 (그대로 출력)

```
개발 및 로컬 실측 테스트가 끝났습니다. 이제 PowerShell 창에서 아래를 순서대로 실행하세요:

cd "C:\Users\hwang\Projects\seoul-timeavg-air-mcp"
fly launch --no-deploy

⚠️ flyctl deploy 전에, fly.toml을 열어 [[services]] 블록이 있는지 확인하세요.
있다면 저에게 "fly.toml을 http_service 방식으로 바꿔줘"라고 요청한 뒤 다음을 진행하세요.

fly secrets set SEOUL_API_KEY=발급받은키
flyctl deploy

배포 완료 메시지에 나온 주소 뒤에 "/mcp"를 붙여서
Claude.ai > 설정 > 커넥터 에서 연결하세요.
예: https://seoul-timeavg-air-mcp.fly.dev/mcp

연결 후 반드시 "새 대화창"을 열어서 도구 목록과 실제 호출을 확인하세요.
```
