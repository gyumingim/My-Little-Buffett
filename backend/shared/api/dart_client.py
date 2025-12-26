"""OpenDART API 클라이언트"""

import httpx
from typing import Any
from app.config import get_settings


class DartClient:
    """OpenDART API 클라이언트"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.dart_base_url
        self.api_key = self.settings.dart_api_key

    def _get_params(self, **kwargs) -> dict:
        """API 파라미터에 API 키 추가"""
        params = {"crtfc_key": self.api_key}
        params.update(kwargs)
        return params

    async def _request(self, endpoint: str, **params) -> dict[str, Any]:
        """API 요청 수행"""
        url = f"{self.base_url}/{endpoint}"
        request_params = self._get_params(**params)

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=request_params, timeout=30.0)
            response.raise_for_status()
            return response.json()

    # ========================
    # 단일회사 전체 재무제표
    # ========================
    async def get_financial_statements(
        self, corp_code: str, bsns_year: str, reprt_code: str = "11011", fs_div: str = "OFS"
    ) -> dict[str, Any]:
        """
        단일회사 전체 재무제표 조회

        Args:
            corp_code: 고유번호 (8자리)
            bsns_year: 사업연도 (4자리)
            reprt_code: 보고서 코드 (11011: 사업보고서, 11012: 반기, 11013: 1분기, 11014: 3분기)
            fs_div: 재무제표 구분 (OFS: 재무제표, CFS: 연결재무제표)
        """
        return await self._request(
            "fnlttSinglAcntAll.json",
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    # ========================
    # 주요사항보고
    # ========================
    async def get_paid_increase(
        self, corp_code: str, bgn_de: str, end_de: str
    ) -> dict[str, Any]:
        """유상증자 결정 조회"""
        return await self._request(
            "piicDecsn.json", corp_code=corp_code, bgn_de=bgn_de, end_de=end_de
        )

    async def get_convertible_bond(
        self, corp_code: str, bgn_de: str, end_de: str
    ) -> dict[str, Any]:
        """전환사채권 발행결정 조회"""
        return await self._request(
            "cvbdIsDecsn.json", corp_code=corp_code, bgn_de=bgn_de, end_de=end_de
        )

    async def get_treasury_stock(
        self, corp_code: str, bgn_de: str, end_de: str
    ) -> dict[str, Any]:
        """자기주식 취득 결정 조회"""
        return await self._request(
            "tsstkAqDecsn.json", corp_code=corp_code, bgn_de=bgn_de, end_de=end_de
        )

    async def get_lawsuit(
        self, corp_code: str, bgn_de: str, end_de: str
    ) -> dict[str, Any]:
        """소송 등의 제기 조회"""
        return await self._request(
            "lwstLg.json", corp_code=corp_code, bgn_de=bgn_de, end_de=end_de
        )

    # ========================
    # 지분공시
    # ========================
    async def get_executive_stock(self, corp_code: str) -> dict[str, Any]:
        """임원ㆍ주요주주 소유보고 조회"""
        return await self._request("elestock.json", corp_code=corp_code)

    # ========================
    # 사업보고서
    # ========================
    async def get_major_shareholders(
        self, corp_code: str, bsns_year: str, reprt_code: str = "11011"
    ) -> dict[str, Any]:
        """최대주주 현황 조회"""
        return await self._request(
            "hyslrSttus.json",
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
        )

    async def get_investment_in_others(
        self, corp_code: str, bsns_year: str, reprt_code: str = "11011"
    ) -> dict[str, Any]:
        """타법인 출자현황 조회"""
        return await self._request(
            "otrCprInvstmntSttus.json",
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
        )

    async def get_public_fund_usage(
        self, corp_code: str, bsns_year: str, reprt_code: str = "11011"
    ) -> dict[str, Any]:
        """공모자금의 사용내역 조회"""
        return await self._request(
            "pssrpCptalUseDtls.json",
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
        )

    # ========================
    # 기업 검색
    # ========================
    async def search_company(self, corp_name: str) -> dict[str, Any]:
        """기업 검색 (기업개황)"""
        return await self._request("company.json", corp_name=corp_name)


# 싱글톤 인스턴스
dart_client = DartClient()
