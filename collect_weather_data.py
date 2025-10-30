# 파일 이름: collect_weather_data.py (최종 키 수정본)
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. 설정 부분 ---
START_YEAR = 2024
START_MONTH = 1
END_YEAR = 2025
END_MONTH = 10
AUTH_KEY = "IV4wVIqyRMGeMFSKsiTBsg" # apihub.kma.go.kr 용 키
OUTPUT_FILE = f"kma_weather_{START_YEAR}{START_MONTH:02d}-{END_YEAR}{END_MONTH:02d}.csv"

# (이하 코드는 이전과 동일하며 수정할 필요 없습니다.)
# --- 2. 월별 데이터 수집 함수 ---
def fetch_monthly_data(year, month, auth_key):
    print(f"[{year}-{month:02d}] 데이터 수집 중...")
    manual_columns = ['TM', 'STN', 'WD', 'WS', 'GST_WD', 'GST_WS', 'GST_TM', 'PA', 'PS', 'PT', 'PR', 'TA', 'TD', 'HM', 'PV', 'RN', 'RN_DAY', 'RN_INT', 'SD_HR3', 'SD_DAY', 'SD_TOT', 'WC', 'WP', 'WW', 'CA_TOT', 'CA_MID', 'CH_MIN', 'CT', 'CT_TOP', 'CT_MID', 'CT_LOW', 'VS', 'SS', 'SI', 'TS', 'TE_005', 'TE_01', 'TE_02', 'TE_03', 'ST_SEA', 'WH', 'BF', 'IR', 'IX', 'RN_JUN']
    base_url = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
    start_dt = datetime(year, month, 1)
    end_dt = (start_dt.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    end_dt = end_dt.replace(hour=23, minute=0)
    params = {'tm1': start_dt.strftime('%Y%m%d%H%M'), 'tm2': end_dt.strftime('%Y%m%d%H%M'), 'stn': '0', 'authKey': auth_key}
    try:
        response = requests.get(base_url, params=params, timeout=300)
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        data_lines = [line for line in lines if not line.startswith('#')]
        if not data_lines:
            print(f"   - [{year}-{month:02d}] 데이터 없음.")
            return None
        parsed_data = [line.strip().split()[:len(manual_columns)] for line in data_lines if len(line.strip().split()) > 1]
        df = pd.DataFrame(parsed_data, columns=manual_columns)
        numeric_cols = [col for col in df.columns if col not in ['TM', 'STN', 'CT', 'WW']]
        for col in numeric_cols: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.replace([-9.0, -99.0, -9, -99], pd.NA, inplace=True)
        print(f"   - [{year}-{month:02d}] {len(df)}개 행 수집 완료.")
        return df
    except Exception as e:
        print(f"   - [{year}-{month:02d}] 데이터 수집 중 에러 발생: {e}")
        return None

# --- 3. 메인 실행 부분 ---
if __name__ == "__main__":
    all_monthly_dfs = []
    print("\n" + "="*50); print(f"✅ 2단계: 장기간 날씨 데이터 수집을 시작합니다."); print(f"   - 수집 기간: {START_YEAR}년 {START_MONTH}월 ~ {END_YEAR}년 {END_MONTH}월"); print("="*50)
    for year in range(START_YEAR, END_YEAR + 1):
        month_start = START_MONTH if year == START_YEAR else 1
        month_end = END_MONTH if year == END_YEAR else 12
        for month in range(month_start, month_end + 1):
            monthly_df = fetch_monthly_data(year, month, AUTH_KEY)
            if monthly_df is not None: all_monthly_dfs.append(monthly_df)
            time.sleep(2)
    if all_monthly_dfs:
        print("\n모든 월별 데이터를 하나로 병합 중...")
        final_df = pd.concat(all_monthly_dfs, ignore_index=True)
        final_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print("\n" + "="*50); print(f"✅ 성공! 최종 데이터 저장이 완료되었습니다."); print(f"   - 파일 이름: {OUTPUT_FILE}"); print(f"   - 총 데이터 행 수: {len(final_df)}"); print("="*50); print("   -> 다음 3단계(대시보드 실행)를 진행해주세요.")
    else:
        print("\n수집된 데이터가 없어 파일을 생성하지 않았습니다.")