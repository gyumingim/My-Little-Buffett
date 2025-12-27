from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from features.indicators.router import router as indicators_router
from features.disclosures.router import router as disclosures_router
from features.financial_statements.router import router as statements_router
from features.companies.router import router as companies_router
from features.backtest.router import router as backtest_router

settings = get_settings()

app = FastAPI(
    title="My Little Buffett API",
    description="5대 투자 지표 분석 API",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(indicators_router, prefix="/api/indicators", tags=["indicators"])
app.include_router(disclosures_router, prefix="/api/disclosures", tags=["disclosures"])
app.include_router(statements_router, prefix="/api/statements", tags=["statements"])
app.include_router(companies_router, prefix="/api/companies", tags=["companies"])
app.include_router(backtest_router, prefix="/api/backtest", tags=["backtest"])


@app.get("/")
async def root():
    return {"message": "My Little Buffett API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/cache/stats")
async def cache_stats():
    """캐시 통계 조회"""
    from shared.cache import get_cache_stats, cleanup_expired
    cleanup_expired()
    return get_cache_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
