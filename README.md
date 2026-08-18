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
지정한 측정일시(YYYYMMDDHH)의 시간평균 대기환경 정보를 조회합니다.

- `msrmt_dt` (필수): 측정일시, YYYYMMDDHH 형식 (예: `2026081711`)
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
- 한 번에 조회 가능한 최대 건수는 1000건입니다(`END_INDEX - START_INDEX ≤ 1000`).
  샘플 키(`sample`) 사용 시에는 최대 5건입니다.
- <!-- 실측 확인 후 아래 항목들을 실제 동작 기준으로 갱신할 것 -->
  선택 파라미터(권역명/측정소명) 부분 채움 시 정상 동작 여부는 로컬 실측 후 갱신됩니다.
- 이 서버는 API 키 없이 누구나 커넥터로 연결할 수 있어, IP 기반 rate limit
  (분당 3회, 반복 위반 시 24시간 차단, 일일 30회 제한)이 적용되어 있습니다.

## 라이선스

- **코드**: MIT License
- **데이터**: 공공누리 1유형 (출처표시, 서울특별시)
