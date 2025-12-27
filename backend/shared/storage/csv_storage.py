"""CSV 기반 저장소 - SQLite 대체

API 응답과 분석 결과를 CSV 파일로 저장합니다.
"""

import json
import hashlib
from pathlib import Path
from typing import Any
from datetime import datetime
import pandas as pd


class CSVStorage:
    """CSV 파일 기반 저장소"""

    def __init__(self, base_path: Path = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"

        self.csv_dir = base_path / "csv"
        self.results_dir = base_path / "results"

        # 디렉토리 생성
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 결과 버퍼 (100개씩 모아서 쓰기)
        self._results_buffer = []

    # ==========================================
    # API 응답 저장/조회
    # ==========================================

    def get_api_data(self, endpoint: str, params: dict) -> dict | None:
        """CSV에서 API 응답 조회

        Returns:
            dict: 저장된 API 응답 (없으면 None)
        """
        filepath = self._make_filepath(endpoint, params)

        if not filepath.exists():
            return None

        try:
            # CSV 읽기
            df = pd.read_csv(filepath, encoding="utf-8")

            # 메타데이터 읽기 (첫 줄 주석)
            with open(filepath, "r", encoding="utf-8") as f:
                first_line = f.readline()
                if first_line.startswith("#"):
                    metadata_str = first_line[1:].strip()
                    metadata = dict(item.split("=") for item in metadata_str.split(","))
                    status = metadata.get("status", "000")
                else:
                    status = "000"

            # DART API 응답 형식으로 재구성
            response = {
                "status": status,
                "message": "OK",
                "list": df.to_dict(orient="records")
            }

            return response

        except Exception as e:
            print(f"[CSV READ ERROR] {filepath}: {e}")
            return None

    def store_api_data(self, endpoint: str, params: dict, response: dict):
        """API 응답을 CSV로 저장

        Atomic write (temp → rename) 방식으로 파일 손상 방지
        """
        filepath = self._make_filepath(endpoint, params)
        temp_path = filepath.with_suffix(".csv.tmp")

        try:
            # API 응답에서 list 추출
            data_list = response.get("list", [])

            if not data_list:
                # 데이터 없음 - 빈 CSV 저장 (status는 메타데이터로)
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(data_list)

            # 메타데이터 (첫 줄 주석)
            status = response.get("status", "000")
            message = response.get("message", "")
            fetched_at = datetime.now().isoformat()

            metadata = f"# status={status},message={message},fetched_at={fetched_at}\n"

            # Temp 파일에 쓰기
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(metadata)

            # DataFrame append (header 포함)
            df.to_csv(temp_path, mode="a", index=False, encoding="utf-8")

            # Atomic rename
            temp_path.replace(filepath)

        except Exception as e:
            print(f"[CSV WRITE ERROR] {filepath}: {e}")
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
            raise

    def file_exists(self, endpoint: str, params: dict) -> bool:
        """CSV 파일 존재 여부 확인 (빠른 체크)

        파일을 읽지 않고 존재만 확인하므로 매우 빠릅니다.
        """
        filepath = self._make_filepath(endpoint, params)
        return filepath.exists()

    def _make_filepath(self, endpoint: str, params: dict) -> Path:
        """파라미터로부터 CSV 파일 경로 생성

        파일명 형식: {year}_{endpoint}_{corp_code}_{corp_name}_{fs_div}_{reprt_code}.csv
        """
        # Endpoint에서 .json 제거
        endpoint_name = endpoint.replace(".json", "")

        # 파라미터 추출
        corp_code = params.get("corp_code", "unknown")
        bsns_year = params.get("bsns_year", "unknown")
        fs_div = params.get("fs_div", "unknown")
        reprt_code = params.get("reprt_code", "unknown")

        # 회사명 추출 (있으면 추가, 없으면 생략)
        corp_name = params.get("corp_name", "")

        # 파일명 생성
        if corp_name:
            filename = f"{bsns_year}_{endpoint_name}_{corp_code}_{corp_name}_{fs_div}_{reprt_code}.csv"
        else:
            filename = f"{bsns_year}_{endpoint_name}_{corp_code}_{fs_div}_{reprt_code}.csv"

        return self.csv_dir / filename

    # ==========================================
    # 분석 결과 저장/조회
    # ==========================================

    def save_analysis_result(self,
                            corp_code: str,
                            corp_name: str,
                            stock_code: str,
                            sector: str,
                            bsns_year: str,
                            fs_div: str,
                            total_score: float,
                            signal: str,
                            filter_passed: bool,
                            filter_reasons: list,
                            indicators: dict,
                            data_source: str):
        """분석 결과를 버퍼에 추가 (100개씩 모아서 CSV 저장)"""

        # 지표별 value/score 추출
        result_row = {
            "corp_code": corp_code,
            "corp_name": corp_name,
            "stock_code": stock_code,
            "sector": sector,
            "bsns_year": bsns_year,
            "fs_div": fs_div,
            "total_score": round(total_score, 2),
            "signal": signal,
            "filter_passed": 1 if filter_passed else 0,
            "filter_reasons": json.dumps(filter_reasons, ensure_ascii=False),
            "data_source": data_source,
            "created_at": datetime.now().isoformat(),
        }

        # 9개 지표 추가
        for indicator_key, indicator_data in indicators.items():
            prefix = indicator_key
            result_row[f"{prefix}_value"] = indicator_data.get("value", 0)
            result_row[f"{prefix}_score"] = indicator_data.get("score", 0)
            result_row[f"{prefix}_grade"] = indicator_data.get("grade", "")

        # 버퍼에 추가
        self._results_buffer.append(result_row)

        # 100개 모이면 flush
        if len(self._results_buffer) >= 100:
            self._flush_results()

    def _flush_results(self):
        """버퍼에 쌓인 결과를 CSV에 일괄 저장"""
        if not self._results_buffer:
            return

        results_path = self.results_dir / "buffett_analysis.csv"
        df = pd.DataFrame(self._results_buffer)

        # 파일이 없으면 header 포함, 있으면 append
        if not results_path.exists():
            df.to_csv(results_path, index=False, encoding="utf-8")
        else:
            df.to_csv(results_path, mode="a", header=False, index=False, encoding="utf-8")

        print(f"[CSV] Flushed {len(self._results_buffer)} results to {results_path}")
        self._results_buffer.clear()

    def get_analysis_results(self, bsns_year: str, fs_div: str) -> list[dict]:
        """분석 결과 조회 (년도 + 재무제표 구분)

        Returns:
            list[dict]: 분석 결과 리스트 (점수 내림차순 정렬)
        """
        # 버퍼 flush (저장 안된 결과가 있을 수 있음)
        self._flush_results()

        results_path = self.results_dir / "buffett_analysis.csv"

        if not results_path.exists():
            return []

        try:
            df = pd.read_csv(results_path, encoding="utf-8")

            # 필터링
            df_filtered = df[(df["bsns_year"] == bsns_year) & (df["fs_div"] == fs_div)]

            # 점수 내림차순 정렬
            df_filtered = df_filtered.sort_values("total_score", ascending=False)

            # dict 리스트로 변환
            results = df_filtered.to_dict(orient="records")

            # filter_reasons를 JSON에서 list로 파싱
            for result in results:
                if isinstance(result.get("filter_reasons"), str):
                    try:
                        result["filter_reasons"] = json.loads(result["filter_reasons"])
                    except:
                        result["filter_reasons"] = []

            return results

        except Exception as e:
            print(f"[CSV READ ERROR] {results_path}: {e}")
            return []

    def get_buffett_analysis_count(self, bsns_year: str, fs_div: str) -> int:
        """분석 결과 개수 조회"""
        results = self.get_analysis_results(bsns_year, fs_div)
        return len(results)

    def clear_analysis_results(self, bsns_year: str = None, fs_div: str = None):
        """분석 결과 삭제

        Args:
            bsns_year: 삭제할 년도 (None이면 전체)
            fs_div: 삭제할 재무제표 구분 (None이면 전체)
        """
        # 버퍼도 clear
        self._results_buffer.clear()

        results_path = self.results_dir / "buffett_analysis.csv"

        if not results_path.exists():
            return

        # 전체 삭제
        if bsns_year is None and fs_div is None:
            results_path.unlink()
            print(f"[CSV] Deleted all results")
            return

        try:
            df = pd.read_csv(results_path, encoding="utf-8")

            # 필터링 (삭제할 행 제외)
            if bsns_year and fs_div:
                df = df[~((df["bsns_year"] == bsns_year) & (df["fs_div"] == fs_div))]
            elif bsns_year:
                df = df[df["bsns_year"] != bsns_year]
            elif fs_div:
                df = df[df["fs_div"] != fs_div]

            # 다시 저장
            df.to_csv(results_path, index=False, encoding="utf-8")
            print(f"[CSV] Cleared results for year={bsns_year}, fs_div={fs_div}")

        except Exception as e:
            print(f"[CSV CLEAR ERROR] {results_path}: {e}")

    def get_available_years(self) -> list[str]:
        """저장된 분석 결과의 년도 목록 조회"""
        self._flush_results()

        results_path = self.results_dir / "buffett_analysis.csv"

        if not results_path.exists():
            return []

        try:
            df = pd.read_csv(results_path, encoding="utf-8")
            years = df["bsns_year"].unique().tolist()
            years.sort(reverse=True)
            return years
        except Exception as e:
            print(f"[CSV READ ERROR] {results_path}: {e}")
            return []


# 싱글톤 인스턴스
csv_storage = CSVStorage()
