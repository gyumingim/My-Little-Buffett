from pydantic import BaseModel
from typing import List, Optional

class FinancialIndicator(BaseModel):
    name: str
    value: str
    status: str  # "success", "warning", "danger"
    description: str
    threshold: str

class AnalysisResult(BaseModel):
    corp_name: str
    corp_code: str
    score: int
    grade: str  # S, A, B, C, D
    indicators: List[FinancialIndicator]
    total_comment: str