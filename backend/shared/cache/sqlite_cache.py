"""SQLite 기반 API 데이터 영구 저장소

한번 호출한 API 데이터는 영구 저장되어 재호출 없이 사용됨.
- 재무제표: 연도별로 저장 (과거 데이터는 변하지 않음)
- 지분공시: 회사별로 저장 (조회시점 기록)
- 주요사항: 기간별로 저장
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent.parent / "data" / "api_data.db"


def get_db_path() -> Path:
    import os
    return Path(os.environ.get("CACHE_DB_PATH", str(DB_PATH)))


def init_db():
    """DB 테이블 초기화"""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        # API 응답 저장 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_key TEXT UNIQUE NOT NULL,
                endpoint TEXT NOT NULL,
                corp_code TEXT,
                bsns_year TEXT,
                params TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_corp_code ON api_data(corp_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bsns_year ON api_data(bsns_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_endpoint ON api_data(endpoint)")

        # 버핏 분석 결과 저장 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS buffett_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_code TEXT NOT NULL,
                corp_name TEXT NOT NULL,
                stock_code TEXT,
                sector TEXT,
                bsns_year TEXT NOT NULL,
                fs_div TEXT NOT NULL,
                total_score REAL,
                signal TEXT,
                filter_passed INTEGER,
                filter_reasons TEXT,
                indicators TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(corp_code, bsns_year, fs_div)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ba_year ON buffett_analysis(bsns_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ba_score ON buffett_analysis(total_score DESC)")
        conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def make_data_key(endpoint: str, params: dict) -> str:
    """데이터 키 생성"""
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(f"{endpoint}:{params_str}".encode()).hexdigest()


def get_stored(endpoint: str, params: dict) -> dict[str, Any] | None:
    """저장된 데이터 조회 (있으면 반환, 없으면 None)"""
    data_key = make_data_key(endpoint, params)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT response FROM api_data WHERE data_key = ?",
            (data_key,)
        ).fetchone()

        if row:
            return json.loads(row["response"])
    return None


def store_data(endpoint: str, params: dict, response: dict):
    """API 응답 영구 저장"""
    data_key = make_data_key(endpoint, params)

    # params에서 corp_code, bsns_year 추출
    corp_code = params.get("corp_code")
    bsns_year = params.get("bsns_year")

    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO api_data
            (data_key, endpoint, corp_code, bsns_year, params, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data_key,
            endpoint,
            corp_code,
            bsns_year,
            json.dumps(params, sort_keys=True),
            json.dumps(response, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        conn.commit()


def get_cache_stats() -> dict:
    """저장소 통계"""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM api_data").fetchone()[0]
        by_endpoint = {}
        for row in conn.execute(
            "SELECT endpoint, COUNT(*) as cnt FROM api_data GROUP BY endpoint"
        ):
            by_endpoint[row["endpoint"]] = row["cnt"]

        by_year = {}
        for row in conn.execute(
            "SELECT bsns_year, COUNT(*) as cnt FROM api_data WHERE bsns_year IS NOT NULL GROUP BY bsns_year"
        ):
            by_year[row["bsns_year"]] = row["cnt"]

        return {
            "total": total,
            "by_endpoint": by_endpoint,
            "by_year": by_year
        }


def get_stored_companies() -> list[str]:
    """저장된 회사 목록"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT corp_code FROM api_data WHERE corp_code IS NOT NULL"
        ).fetchall()
        return [row["corp_code"] for row in rows]


def cleanup_expired():
    """호환성을 위한 빈 함수 (영구 저장이므로 삭제 안함)"""
    pass


# ========================
# 버핏 분석 결과 저장/조회
# ========================

def save_buffett_analysis(
    corp_code: str,
    corp_name: str,
    stock_code: str,
    sector: str,
    bsns_year: str,
    fs_div: str,
    total_score: float,
    signal: str,
    filter_passed: bool,
    filter_reasons: list[str],
    indicators: dict
):
    """버핏 분석 결과 저장"""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO buffett_analysis
            (corp_code, corp_name, stock_code, sector, bsns_year, fs_div,
             total_score, signal, filter_passed, filter_reasons, indicators, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            corp_code,
            corp_name,
            stock_code,
            sector,
            bsns_year,
            fs_div,
            total_score,
            signal,
            1 if filter_passed else 0,
            json.dumps(filter_reasons, ensure_ascii=False),
            json.dumps(indicators, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        conn.commit()


def get_buffett_analysis(bsns_year: str, fs_div: str = "CFS") -> list[dict]:
    """저장된 버핏 분석 결과 조회 (점수순)"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT corp_code, corp_name, stock_code, sector, bsns_year, fs_div,
                   total_score, signal, filter_passed, filter_reasons, indicators, created_at
            FROM buffett_analysis
            WHERE bsns_year = ? AND fs_div = ?
            ORDER BY total_score DESC
        """, (bsns_year, fs_div)).fetchall()

        results = []
        for row in rows:
            results.append({
                "corp_code": row["corp_code"],
                "corp_name": row["corp_name"],
                "stock_code": row["stock_code"],
                "sector": row["sector"],
                "total_score": row["total_score"],
                "signal": row["signal"],
                "filter_passed": bool(row["filter_passed"]),
                "filter_reasons": json.loads(row["filter_reasons"]) if row["filter_reasons"] else [],
                "indicators": json.loads(row["indicators"]) if row["indicators"] else {},
                "created_at": row["created_at"]
            })
        return results


def get_buffett_analysis_count(bsns_year: str, fs_div: str = "CFS") -> int:
    """저장된 분석 결과 수"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM buffett_analysis WHERE bsns_year = ? AND fs_div = ?",
            (bsns_year, fs_div)
        ).fetchone()
        return row[0] if row else 0


def get_available_years() -> list[str]:
    """분석 결과가 있는 연도 목록"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT bsns_year FROM buffett_analysis ORDER BY bsns_year DESC"
        ).fetchall()
        return [row["bsns_year"] for row in rows]


def clear_buffett_analysis(bsns_year: str = None, fs_div: str = None):
    """분석 결과 삭제 (연도/재무제표 지정 가능)"""
    with get_connection() as conn:
        if bsns_year and fs_div:
            conn.execute(
                "DELETE FROM buffett_analysis WHERE bsns_year = ? AND fs_div = ?",
                (bsns_year, fs_div)
            )
        elif bsns_year:
            conn.execute(
                "DELETE FROM buffett_analysis WHERE bsns_year = ?",
                (bsns_year,)
            )
        else:
            conn.execute("DELETE FROM buffett_analysis")
        conn.commit()


# 하위 호환성
get_cached = get_stored
set_cached = lambda e, p, r, ttl=24: store_data(e, p, r)

# 초기화
init_db()
