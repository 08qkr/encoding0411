"""
Korea Gold Exchange 금 시세 크롤러
https://koreagoldx.co.kr/price/gold 에서 1년치 금 시세를 가져옵니다.

필요 패키지 설치:
    pip install requests pandas openpyxl
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import time


def fetch_gold_price_1year() -> pd.DataFrame:
    """
    코리아골드익스체인지에서 최근 1년치 금 시세를 가져옵니다.

    Returns:
        pd.DataFrame: 금 시세 데이터프레임
            - date         : 고시 일시
            - s_pure       : 순금 내가 살 때 (원/3.75g)
            - p_pure       : 순금 내가 팔 때 (원/3.75g)
            - p_18k        : 18K 내가 팔 때 (원/3.75g)
            - p_14k        : 14K 내가 팔 때 (원/3.75g)
    """
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)

    date_end   = today.strftime("%Y.%m.%d")
    date_start = one_year_ago.strftime("%Y.%m.%d")

    # 1) 세션 쿠키 획득 (JSESSIONID)
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://koreagoldx.co.kr/price/gold",
    })

    print("세션 초기화 중...")
    try:
        session.get("https://koreagoldx.co.kr/price/gold", timeout=15)
    except requests.RequestException as e:
        print(f"[경고] 세션 초기화 실패: {e} — 쿠키 없이 계속 시도합니다.")
    time.sleep(1)

    # 2) API 호출
    api_url = "https://koreagoldx.co.kr/api/price/chart/list"
    payload = {
        "srchDt": "1Y",
        "type": "Au",
        "dataDateStart": date_start,
        "dataDateEnd": date_end,
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }

    print(f"기간: {date_start} ~ {date_end}")
    print("금 시세 데이터 요청 중...")

    resp = session.post(api_url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()

    # 3) 응답 파싱
    raw_list = None
    if isinstance(data, dict):
        # 키 탐색 (list / data / result / rows 등)
        for key in ("list", "data", "result", "rows", "items"):
            if key in data and isinstance(data[key], list):
                raw_list = data[key]
                break
        if raw_list is None:
            # 첫 번째 list 타입 값 사용
            for v in data.values():
                if isinstance(v, list):
                    raw_list = v
                    break
    elif isinstance(data, list):
        raw_list = data

    if not raw_list:
        print("[오류] 데이터를 찾을 수 없습니다. 원본 응답:")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        raise ValueError("API 응답에서 데이터 리스트를 찾을 수 없습니다.")

    print(f"수신된 데이터 건수: {len(raw_list):,}건")

    # 4) DataFrame 변환
    df = pd.DataFrame(raw_list)

    # 컬럼 이름 정리
    rename_map = {
        "date":   "고시일시",
        "s_pure": "순금_살때(원/3.75g)",
        "p_pure": "순금_팔때(원/3.75g)",
        "p_18k":  "18K_팔때(원/3.75g)",
        "p_14k":  "14K_팔때(원/3.75g)",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # 날짜 파싱
    if "고시일시" in df.columns:
        df["고시일시"] = pd.to_datetime(df["고시일시"], errors="coerce")
        df.sort_values("고시일시", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)

    # 숫자형 변환
    numeric_cols = [c for c in df.columns if c != "고시일시"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    return df


def save_results(df: pd.DataFrame, filename_prefix: str = "gold_price_1year") -> None:
    """결과를 CSV와 Excel 파일로 저장합니다."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path   = f"{filename_prefix}_{timestamp}.csv"
    excel_path = f"{filename_prefix}_{timestamp}.xlsx"

    # CSV (UTF-8 BOM — Excel에서 한글 깨짐 방지)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV 저장 완료: {csv_path}")

    # Excel
    try:
        df.to_excel(excel_path, index=False, engine="openpyxl")
        print(f"Excel 저장 완료: {excel_path}")
    except ImportError:
        print("[알림] openpyxl이 설치되지 않아 Excel 저장을 건너뜁니다.")
        print("       pip install openpyxl 으로 설치하세요.")


def main():
    print("=" * 55)
    print("  코리아골드익스체인지 1년치 금 시세 크롤러")
    print("=" * 55)

    df = fetch_gold_price_1year()

    print("\n--- 데이터 미리보기 (최신 5건) ---")
    print(df.head().to_string(index=False))

    print("\n--- 기초 통계 ---")
    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        print(numeric_df.describe().to_string())

    save_results(df)

    print("\n크롤링 완료!")
    return df


if __name__ == "__main__":
    main()
