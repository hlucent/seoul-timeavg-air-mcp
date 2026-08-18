# seoul-timeavg-air-mcp

서울시 기간별 시간평균 대기환경 정보를 조회하는 MCP(Model Context Protocol) 서버입니다.
미세먼지, 초미세먼지, 오존, 이산화질소, 일산화탄소, 아황산가스의 시간평균 데이터를
측정소/권역 단위로 제공합니다.

## 데이터 출처

- **제공기관**: 서울특별시 기후환경본부 대기정책과
- **플랫폼**: [서울 열린데이터광장](https://data.seoul.go.kr) — 서비스ID: OA-221,
  서비스명: 서울시 기간별 시간평균 대기환경 정보 (TimeAverageCityAir)
- **이용허락범위**: 공공누리 1유형 (출처표시, 상업적 이용 및 변경 가능)

## 제공 도구 (Tools)

### `get_time_average_air`
지정한 측정일시(YYYYMMDDHHmm)의 시간평균 대기환경 정보를 조회합니다.

- `msrmt_dt` (필수): 측정일시, **YYYYMMDDHHmm 12자리 형식이며 분(mm)은 항상 `00`**
  (예: `202401011200`). 실측 결과 10자리(YYYYMMDDHH)로는 조회되지 않음.
- `start_index` (선택, 기본 1): 조회 시작 위치
- `end_index` (선택, 기본 25): 조회 종료 위치 (한 번에 최대 1000건)
- `sarea_nm` (선택): 권역명 (예: 도심권, 서북권)
- `msrstn_nm` (선택): 측정소명 (예: 종로구, 용산구)

반환 필드: 측정일시, 권역코드/명, 측정소코드/명, 미세먼지 1시간(㎍/㎥), 미세먼지 24시간(㎍/㎥),
초미세먼지(㎍/㎥), 오존(ppm), 이산화질소농도(ppm), 일산화탄소농도(ppm), 아황산가스농도(ppm)

### `search_stations`
측정소명 또는 권역명으로 특정 시점의 대기환경 데이터를 검색합니다.

- `msrmt_dt` (필수)
- `sarea_nm` (선택)
- `msrstn_nm` (선택)

## 설치 및 로컬 실행

```bash
git clone https://github.com/hlucent/seoul-timeavg-air-mcp.git
cd seoul-timeavg-air-mcp
pip install -r requirements.txt
cp .env.example .env
# .env에 SEOUL_API_KEY=발급받은키 입력
python server.py
```

## 환경변수

| 변수명 | 설명 |
|---|---|
| `SEOUL_API_KEY` | 서울 열린데이터광장에서 발급받은 인증키 |
| `PORT` | 서버 포트 (기본 8000) |

## 배포 (fly.io)

```bash
fly launch --no-deploy
fly secrets set SEOUL_API_KEY=발급받은키
flyctl deploy
```

배포 후 Claude.ai 커넥터 연결 주소:
```
https://seoul-timeavg-air-mcp.fly.dev/mcp
```

## 알려진 제약사항

- 인증키는 쿼리 파라미터가 아니라 **URL 경로 세그먼트**로 전달됩니다
  (`http://openAPI.seoul.go.kr:8088/{KEY}/{TYPE}/TimeAverageCityAir/...`).
- 한 번에 조회 가능한 최대 건수는 1000건입니다(`END_INDEX - START_INDEX ≤ 1000`, 초과 시 `ERROR-336`).
  샘플 키(`sample`) 사용 시에는 최대 5건입니다(`ERROR-335`).
- `MSRMT_DT`는 **12자리(YYYYMMDDHHmm, 분은 항상 00)** 만 정상 조회됩니다. 10자리는 `INFO-200`(데이터 없음)이 반환됩니다.
- 선택 파라미터(권역명/측정소명) 조합 실측 결과:
  - 둘 다 생략: 전체 반환
  - `sarea_nm`만 지정: 해당 권역으로 정상 필터링
  - `msrstn_nm`만 지정(권역명 생략): **필터가 무시되고 전체가 반환되는 API 특이 동작 확인**.
    이 서버는 이 경우를 감지해 응답을 측정소명으로 재필터링하여 반환합니다.
  - 둘 다 지정: 정상 필터링(교집합)
- HTTPS는 지원되지 않습니다(연결 실패). HTTP(포트 8088)만 사용합니다.
- 일부 에러 응답(예: `ERROR-335`, `ERROR-336`)은 `TYPE=json` 요청에도 XML로 반환됩니다.
  이 서버는 JSON 우선 파싱 후 실패 시 XML로 폴백합니다.
- 이 서버는 API 키 없이 누구나 커넥터로 연결할 수 있어, IP 기반 rate limit
  (분당 3회, 1시간 내 429 5회 이상 시 24시간 차단, 일일 30회 제한)이 적용되어 있습니다.

## 라이선스

- **코드**: MIT License
- **데이터**: 공공누리 1유형 (출처표시, 서울특별시)
