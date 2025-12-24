import httpx
import os
from datetime import datetime, timedelta

# 실제 서비스 시 환경변수나 설정파일로 관리
DART_API_KEY = os.getenv("DART_API_KEY", "249398dc82582f09ede63603fc0cc73a11e530fd")

class DartService:
    BASE_URL = "https://opendart.fss.or.kr/api"

    async def get_financial_statement(self, corp_code: str, year: str = "2023"):
        """
        단일회사 전체 재무제표 (PDF Page 1, [cite: 574-579])
        URL: /fnlttSinglAcntAll.json
        """
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": "11011",  # 사업보고서
            "fs_div": "CFS" # 연결재무제표
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.BASE_URL}/fnlttSinglAcntAll.json", params=params)
            return res.json()

    async def get_cb_issuance(self, corp_code: str):
        """
        전환사채권 발행결정 (PDF Page 14, [cite: 495])
        URL: /cvbdIsDecsn.json
        """
        # 최근 1년 조회
        end_de = datetime.now().strftime("%Y%m%d")
        bgn_de = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.BASE_URL}/cvbdIsDecsn.json", params=params)
            return res.json()

    async def get_insider_trading(self, corp_code: str):
        """
        임원/주요주주 소유보고 (PDF Page 14, [cite: 496-497])
        URL: /elestock.json
        """
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.BASE_URL}/elestock.json", params=params)
            return res.json()