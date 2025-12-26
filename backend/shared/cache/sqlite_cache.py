"""SQLite 기반 API 캐시"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from contextlib import contextmanager

# 캐시 DB 경로
CACHE_DB_PATH = Path(__file__).parent.parent.parent / "data" / "cache.db"


def get_cache_path() -> Path:
    """캐시 DB 경로 반환 (환경변수 지원)"""
    import os
    return Path(os.environ.get("CACHE_DB_PATH", str(CACHE_DB_PATH)))


def init_db():
    """캐시 테이블 초기화"""
    db_path = get_cache_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL,
                params TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON api_cache(expires_at)")
        conn.commit()


@contextmanager
def get_connection():
    """DB 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(get_cache_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def make_cache_key(endpoint: str, params: dict) -> str:
    """캐시 키 생성"""
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(f"{endpoint}:{params_str}".encode()).hexdigest()


def get_cached(endpoint: str, params: dict) -> dict[str, Any] | None:
    """캐시된 응답 조회"""
    cache_key = make_cache_key(endpoint, params)
    now = datetime.now().isoformat()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT response FROM api_cache WHERE cache_key = ? AND expires_at > ?",
            (cache_key, now)
        ).fetchone()

        if row:
            return json.loads(row["response"])
    return None


def set_cached(endpoint: str, params: dict, response: dict, ttl_hours: int = 24):
    """응답 캐시 저장"""
    cache_key = make_cache_key(endpoint, params)
    now = datetime.now()
    expires_at = now + timedelta(hours=ttl_hours)

    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO api_cache
            (cache_key, endpoint, params, response, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            endpoint,
            json.dumps(params, sort_keys=True),
            json.dumps(response, ensure_ascii=False),
            now.isoformat(),
            expires_at.isoformat()
        ))
        conn.commit()


def cleanup_expired():
    """만료된 캐시 정리"""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute("DELETE FROM api_cache WHERE expires_at < ?", (now,))
        conn.commit()


def get_cache_stats() -> dict:
    """캐시 통계"""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
        valid = conn.execute(
            "SELECT COUNT(*) FROM api_cache WHERE expires_at > ?", (now,)
        ).fetchone()[0]
        return {"total": total, "valid": valid, "expired": total - valid}


# 초기화
init_db()
