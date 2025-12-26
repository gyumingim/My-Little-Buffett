"""주요 기업 데이터 사전 로딩 스크립트

사용법:
    python -m scripts.preload_data [--years 2023,2022,2021] [--limit 10]
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.companies.data import COMPANIES
from shared.api.dart_client import dart_client
from shared.cache import get_cache_stats


async def preload_company(corp_code: str, corp_name: str, years: list[str]):
    """단일 기업 데이터 로딩"""
    results = {"success": 0, "skip": 0, "fail": 0}

    for year in years:
        try:
            # 재무제표 (OFS/CFS)
            for fs_div in ["OFS", "CFS"]:
                data = await dart_client.get_financial_statements(
                    corp_code=corp_code, bsns_year=year, fs_div=fs_div
                )
                if data.get("status") == "000":
                    results["success"] += 1
                else:
                    results["skip"] += 1

            # 최대주주 현황
            data = await dart_client.get_major_shareholders(
                corp_code=corp_code, bsns_year=year
            )
            if data.get("status") == "000":
                results["success"] += 1
            else:
                results["skip"] += 1

        except Exception as e:
            results["fail"] += 1
            print(f"  [ERROR] {corp_name} {year}: {e}")

    # 임원 주식 현황 (연도 무관)
    try:
        data = await dart_client.get_executive_stock(corp_code=corp_code)
        if data.get("status") == "000":
            results["success"] += 1
        else:
            results["skip"] += 1
    except Exception:
        results["fail"] += 1

    return results


async def main(years: list[str], limit: int | None = None):
    """메인 로딩 함수"""
    companies = COMPANIES[:limit] if limit else COMPANIES
    total = len(companies)

    print(f"=== 데이터 사전 로딩 시작 ===")
    print(f"대상: {total}개 기업, 연도: {years}")
    print()

    stats = {"success": 0, "skip": 0, "fail": 0}

    for i, (corp_code, corp_name, stock_code, sector) in enumerate(companies, 1):
        print(f"[{i}/{total}] {corp_name} ({stock_code})...", end=" ", flush=True)

        result = await preload_company(corp_code, corp_name, years)
        stats["success"] += result["success"]
        stats["skip"] += result["skip"]
        stats["fail"] += result["fail"]

        print(f"✓ {result['success']} saved, {result['skip']} skipped")

        # Rate limit 방지 (1초 대기)
        await asyncio.sleep(1)

    print()
    print(f"=== 로딩 완료 ===")
    print(f"저장: {stats['success']}, 스킵: {stats['skip']}, 실패: {stats['fail']}")
    print()
    print("DB 통계:", get_cache_stats())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="주요 기업 데이터 사전 로딩")
    parser.add_argument(
        "--years", default="2023,2022,2021",
        help="로딩할 연도 (콤마 구분, 기본: 2023,2022,2021)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="로딩할 기업 수 제한 (기본: 전체)"
    )

    args = parser.parse_args()
    years = [y.strip() for y in args.years.split(",")]

    asyncio.run(main(years, args.limit))
