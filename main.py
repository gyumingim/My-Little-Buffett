from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from analysis import StockAnalyzer

app = FastAPI(title="Stock Insight Pro")
templates = Jinja2Templates(directory="templates")
analyzer = StockAnalyzer()

# 기업코드 매핑 (예시용, 실제론 별도 DB나 API 필요)
CORP_MAP = {
    "삼성전자": "00126380",
    "SK하이닉스": "000660", 
    # 필요한 만큼 추가하거나 DART 고유번호 API 연동 필요
}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_stock(request: Request, stock_name: str = Form(...)):
    # 1. 기업 코드 찾기
    corp_code = CORP_MAP.get(stock_name)
    
    if not corp_code:
        # 실제 DART API에서는 회사명으로 코드 검색 기능 구현 필요
        # 여기서는 예시로 삼성전자 코드를 fallback으로 사용하거나 에러 처리
        if stock_name == "삼성전자": corp_code = "00126380"
        else:
            return templates.TemplateResponse("report.html", {
                "request": request, 
                "error": f"'{stock_name}'을(를) 찾을 수 없습니다. (지원: 삼성전자)"
            })

    # 2. 분석 실행
    try:
        result = await analyzer.analyze(corp_code, stock_name)
        return templates.TemplateResponse("report.html", {"request": request, "result": result})
    except Exception as e:
        return templates.TemplateResponse("report.html", {
            "request": request, 
            "error": f"분석 중 오류 발생: {str(e)}"
        })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)