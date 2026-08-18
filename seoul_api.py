"""서울 열린데이터광장 TimeAverageCityAir API 호출 모듈."""

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

BASE_HOST = "openAPI.seoul.go.kr:8088"
SERVICE = "TimeAverageCityAir"


class SeoulApiError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _quote(segment: str) -> str:
    return urllib.parse.quote(segment, safe="")


def build_url(key: str, msrmt_dt: str, start_index: int, end_index: int,
              sarea_nm: str | None = None, msrstn_nm: str | None = None,
              type_: str = "json") -> str:
    """URL을 조립한다. 인증키는 쿼리 파라미터가 아니라 경로 세그먼트다.

    실측 확인: SAREA_NM을 생략하고 MSRSTN_NM만 채우면(부분 채움, 앞자리 생략)
    필터가 무시되고 전체 결과가 반환된다. 따라서 MSRSTN_NM만 지정된 경우
    SAREA_NM 자리에 빈 세그먼트를 넣지 않고, 두 값을 모두 채우거나 모두
    생략하는 방식으로만 안전하게 동작한다 (호출부에서 보정).
    """
    parts = [
        f"http://{BASE_HOST}",
        _quote(key),
        type_,
        SERVICE,
        str(start_index),
        str(end_index),
        _quote(msrmt_dt),
    ]
    if sarea_nm:
        parts.append(_quote(sarea_nm))
    if msrstn_nm:
        parts.append(_quote(msrstn_nm))
    return "/".join(parts)


def parse_response(text: str) -> dict:
    """JSON 우선 파싱, 실패 시 XML(에러 응답 포함)로 폴백한다."""
    try:
        return json.loads(text)
    except ValueError:
        pass

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        code_match = re.search(r"<CODE>(.*?)</CODE>", text, re.S)
        msg_match = re.search(r"<MESSAGE>(.*?)</MESSAGE>", text, re.S)
        return {
            "RESULT": {
                "CODE": code_match.group(1) if code_match else "UNKNOWN",
                "MESSAGE": (msg_match.group(1) if msg_match else text[:200]).strip(),
            }
        }

    if root.tag == "RESULT":
        code_el = root.find("CODE")
        msg_el = root.find("MESSAGE")
        return {
            "RESULT": {
                "CODE": code_el.text if code_el is not None else "UNKNOWN",
                "MESSAGE": (msg_el.text or "").strip() if msg_el is not None else "",
            }
        }

    result_el = root.find("RESULT")
    result = {
        "CODE": result_el.findtext("CODE", "UNKNOWN") if result_el is not None else "UNKNOWN",
        "MESSAGE": (result_el.findtext("MESSAGE", "") if result_el is not None else "").strip(),
    }
    rows = []
    for row_el in root.findall("row"):
        row = {child.tag: (child.text or "").strip() for child in row_el}
        rows.append(row)

    return {
        root.tag: {
            "list_total_count": int(root.findtext("list_total_count", "0")),
            "RESULT": result,
            "row": rows,
        }
    }


async def fetch_time_average_air(key: str, msrmt_dt: str, start_index: int,
                                  end_index: int, sarea_nm: str | None = None,
                                  msrstn_nm: str | None = None) -> dict:
    """TimeAverageCityAir API를 호출하고 파싱된 결과를 반환한다.

    성공 시 {"list_total_count": int, "rows": [...]} 형태로 반환하고,
    API 에러(INFO-100/200, ERROR-3xx/5xx/6xx)는 SeoulApiError로 발생시킨다.
    """
    url = build_url(key, msrmt_dt, start_index, end_index, sarea_nm, msrstn_nm)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        parsed = parse_response(resp.text)

    if "RESULT" in parsed:
        result = parsed["RESULT"]
    elif SERVICE in parsed:
        result = parsed[SERVICE]["RESULT"]
    else:
        result = {"CODE": "UNKNOWN", "MESSAGE": "알 수 없는 응답 형식"}

    code = result.get("CODE", "UNKNOWN")
    if code != "INFO-000":
        raise SeoulApiError(code, result.get("MESSAGE", ""))

    payload = parsed[SERVICE]
    return {
        "list_total_count": payload.get("list_total_count", 0),
        "rows": payload.get("row", []),
    }
