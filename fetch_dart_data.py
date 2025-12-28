"""
DART API 데이터 수집 스크립트 (독립 실행)

웹사이트와 완전히 분리된 데이터 수집 전용 프로그램

사용법:
    python fetch_dart_data.py --year 2024 --limit 100 --batch-size 10 --delay 1.0

옵션:
    --year: 사업연도 (예: 2024)
    --limit: 수집할 기업 수 (기본: 100)
    --batch-size: 배치 크기 (기본: 10, 동시 요청 수)
    --delay: 배치 간 대기 시간 초 (기본: 1.0, DART API rate limit 방지)
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# backend 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from shared.api.dart_client import dart_client
from shared.storage.csv_storage import csv_storage
from features.companies.data import COMPANIES


async def fetch_company_data(corp_code: str, corp_name: str, year: str, semaphore: asyncio.Semaphore):
    """개별 기업 재무제표 데이터 수집"""
    async with semaphore:
        try:
            # CFS (연결재무제표) 시도
            print(f"[FETCH] {corp_name} ({corp_code}) - CFS")
            cfs_data = await dart_client.fetch_financial_statement(
                corp_code=corp_code,
                bsns_year=year,
                reprt_code="11011",  # 사업보고서
                fs_div="CFS"
            )

            # CFS가 없으면 OFS (개별재무제표) 시도
            if not cfs_data or cfs_data.get("status") != "000":
                print(f"[FETCH] {corp_name} ({corp_code}) - OFS (CFS 없음)")
                ofs_data = await dart_client.fetch_financial_statement(
                    corp_code=corp_code,
                    bsns_year=year,
                    reprt_code="11011",
                    fs_div="OFS"
                )

            print(f"[OK] {corp_name}")
            return {"corp_name": corp_name, "success": True}

        except Exception as e:
            print(f"[ERROR] {corp_name}: {e}")
            return {"corp_name": corp_name, "success": False, "error": str(e)}


async def fetch_all_data(year: str, limit: int, batch_size: int, delay: float):
    """모든 기업 데이터 수집"""

    print(f"""
╔════════════════════════════════════════════════════════════╗
║  DART API 데이터 수집 시작                                ║
╠════════════════════════════════════════════════════════════╣
║  사업연도:     {year}년                                    ║
║  수집 기업 수: {limit}개                                   ║
║  배치 크기:    {batch_size}개 (동시 요청)                  ║
║  배치 간 대기: {delay}초                                   ║
╚════════════════════════════════════════════════════════════╝
    """)

    # 수집할 기업 목록
    companies_to_fetch = COMPANIES[:limit]
    total = len(companies_to_fetch)

    # 세마포어 (동시 요청 수 제한)
    semaphore = asyncio.Semaphore(batch_size)

    # 배치 단위로 처리
    results = []
    for i in range(0, total, batch_size):
        batch = companies_to_fetch[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n[BATCH {batch_num}/{total_batches}] {len(batch)}개 기업 처리 중...")

        # 배치 실행
        tasks = [
            fetch_company_data(corp_code, corp_name, year, semaphore)
            for corp_code, corp_name, _, _ in batch
        ]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

        # 성공/실패 카운트
        success = sum(1 for r in batch_results if r["success"])
        failed = len(batch_results) - success
        print(f"[BATCH {batch_num}] 완료 - 성공: {success}, 실패: {failed}")

        # 다음 배치 전 대기 (마지막 배치 제외)
        if i + batch_size < total:
            print(f"[WAIT] {delay}초 대기 중... (DART API rate limit 방지)")
            await asyncio.sleep(delay)

    # 최종 결과
    total_success = sum(1 for r in results if r["success"])
    total_failed = len(results) - total_success

    print(f"""
╔════════════════════════════════════════════════════════════╗
║  데이터 수집 완료                                          ║
╠════════════════════════════════════════════════════════════╣
║  전체 기업 수: {total}개                                   ║
║  성공:        {total_success}개                            ║
║  실패:        {total_failed}개                             ║
║  완료 시각:   {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ║
╚════════════════════════════════════════════════════════════╝
    """)

    # 실패한 기업 목록
    if total_failed > 0:
        print("\n[실패한 기업 목록]")
        for r in results:
            if not r["success"]:
                print(f"  - {r['corp_name']}: {r.get('error', 'Unknown error')}")

    # CSV 파일 위치 안내
    csv_dir = Path(__file__).parent / "backend" / "data" / "csv"
    print(f"\n✅ CSV 파일 저장 위치: {csv_dir}")
    print(f"   → 웹사이트에서 이 CSV 파일들을 읽어서 분석합니다.")


def main():
    parser = argparse.ArgumentParser(description="DART API 데이터 수집 스크립트")
    parser.add_argument("--year", type=str, required=True, help="사업연도 (예: 2024)")
    parser.add_argument("--limit", type=int, default=100, help="수집할 기업 수 (기본: 100)")
    parser.add_argument("--batch-size", type=int, default=10, help="배치 크기 (기본: 10)")
    parser.add_argument("--delay", type=float, default=1.0, help="배치 간 대기 시간 초 (기본: 1.0)")

    args = parser.parse_args()

    # 검증
    if args.limit <= 0:
        print("❌ 오류: --limit는 1 이상이어야 합니다.")
        sys.exit(1)

    if args.batch_size <= 0 or args.batch_size > 100:
        print("❌ 오류: --batch-size는 1~100 사이여야 합니다.")
        sys.exit(1)

    if args.delay < 0:
        print("❌ 오류: --delay는 0 이상이어야 합니다.")
        sys.exit(1)

    # 실행
    try:
        asyncio.run(fetch_all_data(args.year, args.limit, args.batch_size, args.delay))
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
