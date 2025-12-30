"""
FastAPI Main Application
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from .analyzer import AlphaFinder

# 환경 변수 로드
load_dotenv()

# 앱 생성
app = FastAPI(
    title="My Little Buffett API",
    description="주식 분석 API - Alpha Finder",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 경로
DATA_PATH = Path(os.getenv("DATA_PATH", "../data"))


# Request/Response Models
class AnalyzeRequest(BaseModel):
    corp_codes: List[str]


class CompanyAnalysis(BaseModel):
    corp_code: str
    final_score: int
    grade: str
    recommendation: str
    stage1_filter: Optional[dict] = None
    stage2_score: Optional[dict] = None
    stage3_boost: Optional[dict] = None


# Global analyzer instance
analyzer = AlphaFinder(DATA_PATH)


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "status": "ok",
        "message": "My Little Buffett API is running",
        "data_path": str(DATA_PATH)
    }


@app.get("/api/analyze/{corp_code}", response_model=CompanyAnalysis)
async def analyze_single_company(corp_code: str):
    """
    단일 기업 분석

    Args:
        corp_code: 기업 코드 (예: 00100601)

    Returns:
        분석 결과
    """
    try:
        result = analyzer.analyze_company(corp_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/batch", response_model=List[CompanyAnalysis])
async def analyze_batch_companies(request: AnalyzeRequest):
    """
    여러 기업 일괄 분석

    Args:
        request: {"corp_codes": ["00100601", "00101220", ...]}

    Returns:
        분석 결과 리스트 (점수순 정렬)
    """
    try:
        results = analyzer.analyze_batch(request.corp_codes)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/top/{n}")
async def get_top_n_companies(
    n: int = Query(default=50, ge=1, le=200),
    min_score: int = Query(default=0, ge=0, le=100)
):
    """
    상위 N개 종목 조회

    Args:
        n: 조회할 종목 수 (기본 50)
        min_score: 최소 점수 (기본 0)

    Returns:
        상위 N개 종목 리스트
    """
    try:
        # 실제로는 모든 기업 코드를 DB나 파일에서 읽어와야 함
        # 여기서는 예시로 하드코딩
        all_corp_codes = get_all_corp_codes()

        # 분석 실행
        results = analyzer.analyze_batch(all_corp_codes)

        # 필터링 및 상위 N개 추출
        filtered = [r for r in results if r.get("final_score", 0) >= min_score]
        top_n = filtered[:n]

        return {
            "total_analyzed": len(results),
            "total_filtered": len(filtered),
            "results": top_n
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_all_corp_codes() -> List[str]:
    """
    모든 기업 코드 조회 (실제로는 DB나 파일에서 읽어와야 함)

    Returns:
        기업 코드 리스트
    """
    # 예시: CFS 폴더에서 기업 코드 추출
    corp_codes = []

    cfs_path = DATA_PATH / "CFS" / "2024"
    if cfs_path.exists():
        for file in cfs_path.glob("*.json"):
            corp_code = file.stem
            corp_codes.append(corp_code)

    return corp_codes


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
