# 파일 이름: create_station_file.py (최종 수정본)
import pandas as pd
import requests
import io
import xml.etree.ElementTree as ET # XML 분석을 위해 추가

def save_station_info_to_csv(auth_key="982914eaa83d65063ee96ed742ff474b9e7af25721725c9ab3dd812e16067396", output_file="station_info.csv"):
    """
    올바른 API 키와 오류 확인 로직을 사용하여 지점 정보를 수집하고 CSV 파일로 저장합니다.
    """
    print("✅ 1단계: 전국 관측소 정보 수집을 시작합니다.")
    
    stn_info_url = "https://apihub.kma.go.kr/api/typ02/openApi/SfcMtlyInfoService/getSfcStnLstTbl"
    params = {
        'authKey': auth_key,
        'pageNo': 1,
        'numOfRows': 1000,
        'dataType': 'XML'
    }
    
    try:
        response = requests.get(stn_info_url, params=params, timeout=120)
        response.raise_for_status()
        
        xml_text = response.text

        # ★★★★★ 해결책: API 응답이 정상인지 먼저 확인 ★★★★★
        root = ET.fromstring(xml_text)
        result_code = root.find('.//resultCode')
        
        if result_code is None or result_code.text != '00':
            result_msg = root.find('.//resultMsg').text
            raise Exception(f"API 서버가 오류를 반환했습니다: {result_msg}")

        # 모든 확인이 끝나면 pandas로 데이터 읽기
        stn_df = pd.read_xml(io.StringIO(xml_text), xpath=".//item")
        
        stn_df = stn_df[['stn_id', 'stn_ko', 'lat', 'lon']]
        stn_df.rename(columns={'stn_id': 'STN', 'stn_ko': '지점명', 'lat': '위도', 'lon': '경도'}, inplace=True)
        
        stn_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 성공! 총 {len(stn_df)}개 지점 정보를 '{output_file}' 파일로 저장했습니다.")
        print("   -> 다음 2단계(날씨 데이터 수집)를 진행해주세요.")

    except Exception as e:
        print(f"❌ 에러: 지점 정보 조회 중 문제가 발생했습니다: {e}")

if __name__ == "__main__":
    save_station_info_to_csv()