"""서울시 기간별 시간평균 대기환경 정보 MCP 서버."""

import os
import time
from collections import defaultdict

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from seoul_api import SeoulApiError, fetch_time_average_air

load_dotenv()

SEOUL_API_KEY = os.environ["SEOUL_API_KEY"]

MINUTE_LIMIT = 3
MINUTE_WINDOW = 60
VIOLATION_LIMIT = 5
VIOLATION_WINDOW = 3600
BLOCK_DURATION = 86400
DAILY_LIMIT = 30
DAILY_WINDOW = 86400


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 기반 3단계 rate limit: 분당 3회, 위반 누적 시 24시간 차단, 일일 30회."""

    _call_log: dict[str, list[float]] = defaultdict(list)
    _violation_log: dict[str, list[float]] = defaultdict(list)
    _blocked_until: dict[str, float] = {}

    async def dispatch(self, request, call_next):
        ip = self._get_ip(request)
        now = time.time()

        blocked_until = self._blocked_until.get(ip)
        if blocked_until and now < blocked_until:
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
            )

        calls = self._call_log[ip]
        calls[:] = [t for t in calls if now - t < DAILY_WINDOW]

        recent_minute = [t for t in calls if now - t < MINUTE_WINDOW]
        if len(recent_minute) >= MINUTE_LIMIT:
            self._record_violation(ip, now)
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
            )

        if len(calls) >= DAILY_LIMIT:
            self._record_violation(ip, now)
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
            )

        calls.append(now)
        return await call_next(request)

    def _record_violation(self, ip: str, now: float):
        violations = self._violation_log[ip]
        violations.append(now)
        violations[:] = [t for t in violations if now - t < VIOLATION_WINDOW]
        if len(violations) >= VIOLATION_LIMIT:
            self._blocked_until[ip] = now + BLOCK_DURATION

    @staticmethod
    def _get_ip(request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


mcp = FastMCP("seoul-timeavg-air-mcp")


@mcp.tool()
async def get_time_average_air(
    msrmt_dt: str,
    start_index: int = 1,
    end_index: int = 25,
    sarea_nm: str | None = None,
    msrstn_nm: str | None = None,
) -> dict:
    """서울시 기간별 시간평균 대기환경 정보를 조회한다.

    특정 측정일시(시간 단위)의 미세먼지, 초미세먼지, 오존, 이산화질소,
    일산화탄소, 아황산가스 농도를 권역/측정소별로 반환한다.

    Args:
        msrmt_dt: 측정일시. 형식은 YYYYMMDDHHmm이며 분(mm)은 항상 00 (예: "202401011200").
        start_index: 요청 시작 위치 (기본 1).
        end_index: 요청 종료 위치 (기본 25, 서울시 전체 측정소 수). end - start <= 1000.
        sarea_nm: 권역명 (선택, 예: "도심권", "서북권"). msrstn_nm과 함께 지정할 때만
            필터가 정상 적용된다 (msrstn_nm만 단독 지정 시 필터가 무시되는 API 특이 동작 확인됨).
        msrstn_nm: 측정소명 (선택, 예: "종로구", "용산구").

    Returns:
        list_total_count(전체 건수)와 rows(측정 결과 목록). 각 row의 필드:
        - MSRMT_DT: 측정일시
        - SAREA_NM: 권역명, MSRSTN_NM: 측정소명
        - PM_HOUR: 미세먼지 1시간 (㎍/㎥)
        - PM_ALDY: 미세먼지 24시간 일평균 (㎍/㎥)
        - FPM: 초미세먼지 (㎍/㎥)
        - OZON: 오존 (ppm)
        - NTDX: 이산화질소농도 (ppm)
        - CBMX: 일산화탄소농도 (ppm)
        - SPDX: 아황산가스농도 (ppm)
    """
    try:
        result = await fetch_time_average_air(
            SEOUL_API_KEY, msrmt_dt, start_index, end_index, sarea_nm, msrstn_nm
        )
    except SeoulApiError as e:
        return {"error": e.code, "message": e.message}

    if msrstn_nm and not sarea_nm:
        result["rows"] = [r for r in result["rows"] if r.get("MSRSTN_NM") == msrstn_nm]
        result["list_total_count"] = len(result["rows"])

    return result


@mcp.tool()
async def search_stations(
    msrmt_dt: str,
    sarea_nm: str | None = None,
    msrstn_nm: str | None = None,
) -> dict:
    """측정소명 또는 권역명으로 특정 시점의 대기환경 데이터를 검색한다.

    Args:
        msrmt_dt: 측정일시. 형식은 YYYYMMDDHHmm이며 분(mm)은 항상 00 (예: "202401011200").
        sarea_nm: 권역명 (선택, 예: "도심권", "서북권").
        msrstn_nm: 측정소명 (선택, 예: "종로구", "용산구").

    Returns:
        get_time_average_air와 동일한 형식. list_total_count와 rows(측정 결과 목록).
        각 row의 단위: PM_HOUR/PM_ALDY/FPM은 ㎍/㎥, OZON/NTDX/CBMX/SPDX는 ppm.
    """
    return await get_time_average_air(
        msrmt_dt=msrmt_dt,
        start_index=1,
        end_index=1000,
        sarea_nm=sarea_nm,
        msrstn_nm=msrstn_nm,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
        middleware=[Middleware(RateLimitMiddleware)],
    )
