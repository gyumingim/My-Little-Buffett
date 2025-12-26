"""공시 정보 API 라우터"""

from fastapi import APIRouter, HTTPException, Query
from shared.api.dart_client import dart_client
from shared.schemas.common import BaseResponse

router = APIRouter()


@router.get("/convertible-bonds/{corp_code}")
async def get_convertible_bonds(
    corp_code: str,
    bgn_de: str = Query(..., description="시작일 (YYYYMMDD)"),
    end_de: str = Query(..., description="종료일 (YYYYMMDD)"),
):
    """전환사채 발행 결정 공시 조회"""
    try:
        data = await dart_client.get_convertible_bond(corp_code, bgn_de, end_de)
        if data.get("status") != "000":
            return BaseResponse(success=True, message="조회된 데이터가 없습니다.", data=[])
        return BaseResponse(success=True, message="조회 완료", data=data.get("list", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paid-increase/{corp_code}")
async def get_paid_increase(
    corp_code: str,
    bgn_de: str = Query(..., description="시작일 (YYYYMMDD)"),
    end_de: str = Query(..., description="종료일 (YYYYMMDD)"),
):
    """유상증자 결정 공시 조회"""
    try:
        data = await dart_client.get_paid_increase(corp_code, bgn_de, end_de)
        if data.get("status") != "000":
            return BaseResponse(success=True, message="조회된 데이터가 없습니다.", data=[])
        return BaseResponse(success=True, message="조회 완료", data=data.get("list", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/treasury-stock/{corp_code}")
async def get_treasury_stock(
    corp_code: str,
    bgn_de: str = Query(..., description="시작일 (YYYYMMDD)"),
    end_de: str = Query(..., description="종료일 (YYYYMMDD)"),
):
    """자기주식 취득 결정 공시 조회"""
    try:
        data = await dart_client.get_treasury_stock(corp_code, bgn_de, end_de)
        if data.get("status") != "000":
            return BaseResponse(success=True, message="조회된 데이터가 없습니다.", data=[])
        return BaseResponse(success=True, message="조회 완료", data=data.get("list", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executive-stock/{corp_code}")
async def get_executive_stock(corp_code: str):
    """임원ㆍ주요주주 소유보고 조회"""
    try:
        data = await dart_client.get_executive_stock(corp_code)
        if data.get("status") != "000":
            return BaseResponse(success=True, message="조회된 데이터가 없습니다.", data=[])
        return BaseResponse(success=True, message="조회 완료", data=data.get("list", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lawsuit/{corp_code}")
async def get_lawsuit(
    corp_code: str,
    bgn_de: str = Query(..., description="시작일 (YYYYMMDD)"),
    end_de: str = Query(..., description="종료일 (YYYYMMDD)"),
):
    """소송 등의 제기 공시 조회"""
    try:
        data = await dart_client.get_lawsuit(corp_code, bgn_de, end_de)
        if data.get("status") != "000":
            return BaseResponse(success=True, message="조회된 데이터가 없습니다.", data=[])
        return BaseResponse(success=True, message="조회 완료", data=data.get("list", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/major-shareholders/{corp_code}")
async def get_major_shareholders(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    reprt_code: str = Query("11011", description="보고서 코드"),
):
    """최대주주 현황 조회"""
    try:
        data = await dart_client.get_major_shareholders(corp_code, bsns_year, reprt_code)
        if data.get("status") != "000":
            return BaseResponse(success=True, message="조회된 데이터가 없습니다.", data=[])
        return BaseResponse(success=True, message="조회 완료", data=data.get("list", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
