"""재무제표 API 라우터"""

from fastapi import APIRouter, HTTPException, Query
from shared.api.dart_client import dart_client
from shared.schemas.common import BaseResponse

router = APIRouter()


@router.get("/{corp_code}")
async def get_financial_statements(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도 (예: 2023)"),
    reprt_code: str = Query("11011", description="보고서 코드 (11011: 사업보고서)"),
    fs_div: str = Query("OFS", description="재무제표 구분 (OFS: 개별, CFS: 연결)"),
):
    """
    단일회사 전체 재무제표 조회

    보고서 코드:
    - 11011: 사업보고서
    - 11012: 반기보고서
    - 11013: 1분기보고서
    - 11014: 3분기보고서
    """
    try:
        data = await dart_client.get_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

        if data.get("status") != "000":
            return BaseResponse(
                success=False,
                message=data.get("message", "데이터를 가져오는데 실패했습니다."),
                data=None,
            )

        return BaseResponse(
            success=True, message="조회 완료", data=data.get("list", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}/balance-sheet")
async def get_balance_sheet(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    reprt_code: str = Query("11011", description="보고서 코드"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """재무상태표(BS) 조회"""
    try:
        data = await dart_client.get_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

        if data.get("status") != "000":
            return BaseResponse(success=False, message="데이터 없음", data=None)

        # BS만 필터링
        bs_items = [item for item in data.get("list", []) if item.get("sj_div") == "BS"]

        return BaseResponse(success=True, message="조회 완료", data=bs_items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}/income-statement")
async def get_income_statement(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    reprt_code: str = Query("11011", description="보고서 코드"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """손익계산서(IS) 조회"""
    try:
        data = await dart_client.get_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

        if data.get("status") != "000":
            return BaseResponse(success=False, message="데이터 없음", data=None)

        # IS만 필터링
        is_items = [item for item in data.get("list", []) if item.get("sj_div") == "IS"]

        return BaseResponse(success=True, message="조회 완료", data=is_items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}/cash-flow")
async def get_cash_flow(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    reprt_code: str = Query("11011", description="보고서 코드"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """현금흐름표(CF) 조회"""
    try:
        data = await dart_client.get_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

        if data.get("status") != "000":
            return BaseResponse(success=False, message="데이터 없음", data=None)

        # CF만 필터링
        cf_items = [item for item in data.get("list", []) if item.get("sj_div") == "CF"]

        return BaseResponse(success=True, message="조회 완료", data=cf_items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
