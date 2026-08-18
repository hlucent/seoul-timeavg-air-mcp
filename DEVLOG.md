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
