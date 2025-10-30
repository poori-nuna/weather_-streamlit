# dashboard.py (일일 전체 데이터 다운로드 기능 추가 최종본)
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import io

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="전국 날씨 대시보드")

# --- 데이터 로딩 함수 (수정 없음) ---
@st.cache_data
def get_station_info_from_file(station_file):
    try:
        return pd.read_csv(station_file)
    except FileNotFoundError:
        st.error(f"'{station_file}' 파일을 찾을 수 없습니다.")
        return None

@st.cache_data
def load_and_merge_data(weather_file, station_file):
    try:
        weather_df = pd.read_csv(weather_file)
    except FileNotFoundError:
        st.error(f"'{weather_file}' 파일을 찾을 수 없습니다.")
        return None

    station_df = get_station_info_from_file(station_file)
    if station_df is None: return None

    merged_df = pd.merge(weather_df, station_df, on='STN', how='left')
    
    merged_df['위도'] = pd.to_numeric(merged_df['위도'], errors='coerce')
    merged_df['경도'] = pd.to_numeric(merged_df['경도'], errors='coerce')
    merged_df['TM'] = pd.to_datetime(merged_df['TM'], format='%Y%m%d%H%M', errors='coerce')

    merged_df.dropna(subset=['위도', '경도', 'TM'], inplace=True)
    merged_df.sort_values('TM', inplace=True)
    return merged_df

# ★★★★★ 기능 추가: 엑셀 변환 함수를 상단으로 이동하여 재사용성 높임 ★★★★★
@st.cache_data
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 전역 변수 및 데이터 로딩 ---
WEATHER_CSV_FILE = "kma_weather_202401-202510.csv"
STATION_INFO_FILE = "station_info.csv"
df = load_and_merge_data(WEATHER_CSV_FILE, STATION_INFO_FILE)

# --- 대시보드 UI 구성 ---
st.title("🗺️ 전국 기상 관측 대시보드")

if df is not None and not df.empty:
    st.sidebar.header("🗓️ 조회 옵션")
    
    variable_map = {'기온 (°C)': 'TA', '상대습도 (%)': 'HM', '풍속 (m/s)': 'WS', '강수량 (mm)': 'RN'}
    station_list = sorted(df['지점명'].unique())
    
    selected_variable_name = st.sidebar.selectbox("📍 지도 표시 데이터 선택", list(variable_map.keys()))
    selected_variable_col = variable_map[selected_variable_name]

    min_date, max_date = df['TM'].min().date(), df['TM'].max().date()
    selected_date = st.sidebar.date_input("날짜 선택", value=max_date, min_value=min_date, max_value=max_date)
    selected_hour = st.sidebar.slider("시간 선택 (24시)", 0, 23, 9)

    selected_datetime = datetime.combine(selected_date, datetime.min.time()).replace(hour=selected_hour)
    target_df = df[df['TM'] == selected_datetime].copy()

    st.header(f"{selected_date.strftime('%Y년 %m월 %d일')} 날씨 현황")
    
    # --- 일별 요약 및 전체 데이터 다운로드 섹션 ---
    daily_df = df[df['TM'].dt.date == selected_date].copy()
    if daily_df.empty:
        st.warning("선택하신 날짜에 해당하는 데이터가 없습니다.")
    else:
        daily_summary = daily_df.groupby('지점명').agg(
            max_temp=('TA', 'max'), min_temp=('TA', 'min'), total_rain=('RN', 'sum')
        ).reset_index()
        
        nation_avg_max_temp = daily_summary['max_temp'].mean()
        nation_avg_min_temp = daily_summary['min_temp'].mean()
        nation_avg_rain = daily_summary['total_rain'].mean()
        
        st.subheader("📊 일일 요약")
        col1, col2, col3 = st.columns(3)
        col1.metric("전국 평균 최고기온", f"{nation_avg_max_temp:.1f} °C")
        col2.metric("전국 평균 최저기온", f"{nation_avg_min_temp:.1f} °C")
        col3.metric("전국 평균 강수량", f"{nation_avg_rain:.1f} mm")

        # ★★★★★ 기능 추가: 선택일 전체 데이터 다운로드 버튼 ★★★★★
        # 다운로드할 데이터 준비 (가독성 좋은 컬럼명으로 변경)
        rename_map = {
            'TM': '시간', 'STN': '지점번호', '지점명': '지점명', 'TA': '기온(°C)', 
            'HM': '습도(%)', 'WS': '풍속(m/s)', 'RN': '강수량(mm)', 'WD': '풍향(16방위)', 
            'PA': '현지기압(hPa)', 'PS': '해면기압(hPa)', '위도': '위도', '경도': '경도'
        }
        # daily_df에 있는 컬럼만 선택하여 에러 방지
        cols_to_download = [col for col in rename_map.keys() if col in daily_df.columns]
        daily_download_df = daily_df[cols_to_download].rename(columns=rename_map)

        daily_excel_data = to_excel(daily_download_df)
        st.download_button(
            label="📥 **선택일 전체 데이터 다운로드 (Excel)**",
            data=daily_excel_data,
            file_name=f"daily_weather_{selected_date.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.markdown("---")

    # --- 특정 시간 데이터 시각화 (지도, 테이블 등) ---
    if target_df.empty:
        st.warning(f"{selected_hour:02d}시 데이터가 없습니다. 다른 시간을 선택해주세요.")
    else:
        st.subheader(f"📍 {selected_hour:02d}시 전국 {selected_variable_name} 분포 지도")
        # (이하 지도, 상세 테이블, 시간별 다운로드 기능은 이전과 동일)
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)

        color_map = {
            'TA': {'blue': '<= 0°C', 'green': '0-15°C', 'orange': '15-25°C', 'red': '> 25°C'},
            'HM': {'orange': '<= 40%', 'green': '40-70%', 'blue': '> 70%'},
            'WS': {'green': '<= 2m/s', 'orange': '2-5m/s', 'red': '> 5m/s'},
            'RN': {'purple': '> 0mm', 'gray': '0mm'}
        }
        
        def get_color(value, var_name):
            if pd.isna(value): return 'gray'
            if var_name == 'TA':
                if value <= 0: return 'blue'
                elif value <= 15: return 'green'
                elif value <= 25: return 'orange'
                else: return 'red'
            elif var_name == 'HM':
                if value <= 40: return 'orange'
                elif value <= 70: return 'green'
                else: return 'blue'
            elif var_name == 'WS':
                if value <= 2: return 'green'
                elif value <= 5: return 'orange'
                else: return 'red'
            else: return 'purple' if value > 0 else 'gray'
        
        for _, row in target_df.iterrows():
            folium.CircleMarker(
                location=[row['위도'], row['경도']], radius=7,
                color=get_color(row[selected_variable_col], selected_variable_col),
                fill=True, fill_color=get_color(row[selected_variable_col], selected_variable_col),
                fill_opacity=0.8,
                popup=folium.Popup(f"<b>{row['지점명']}</b><br>{selected_variable_name}: {row[selected_variable_col]}", max_width=200)
            ).add_to(m)

        legend_html = '<div style="position: fixed; bottom: 50px; left: 50px; width: 150px; z-index:9999; font-size:14px; background-color:white; border:2px solid grey; padding: 10px;"><b>범례</b><br>'
        current_legend = color_map.get(selected_variable_col, {})
        for color, label in current_legend.items(): legend_html += f'<i class="fa fa-circle" style="color:{color}"></i>&nbsp;{label}<br>'
        legend_html += '</div>'
        m.get_root().html.add_child(folium.Element(legend_html))

        map_data = st_folium(m, width='100%', height=500)
        
        if map_data and map_data['last_object_clicked_popup']:
            popup_content = map_data['last_object_clicked_popup']
            try:
                clicked_station = popup_content.split('<b>')[1].split('</b>')[0]
                if clicked_station in station_list:
                    st.session_state['selected_stations'] = [clicked_station]
            except IndexError:
                pass

        st.subheader(f"📋 {selected_hour:02d}시 상세 데이터")
        display_cols = ['지점명', 'TM', 'TA', 'HM', 'WS', 'RN', '위도', '경도']
        display_df = target_df[display_cols].rename(columns={'TM':'시간', 'TA':'기온', 'HM':'습도', 'WS':'풍속', 'RN':'강수량'}).set_index('지점명')
        st.dataframe(display_df)
        
        hourly_excel_data = to_excel(display_df)
        st.download_button(label="📥 현재 시간 데이터 다운로드 (Excel)", data=hourly_excel_data,
                           file_name=f"hourly_weather_{selected_date.strftime('%Y%m%d')}_{selected_hour:02d}h.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # --- 지점별 추이 그래프 섹션 ---
    st.markdown("---")
    st.header(f"📈 지점별 최근 30일 날씨 비교")
    
    default_stations = st.session_state.get('selected_stations', ['서울', '부산'])
    selected_stations = st.multiselect(
        "비교할 관측 지점을 선택하세요 (지도에서 클릭하여 추가 가능)", 
        station_list, default=default_stations
    )
    
    if selected_stations:
        start_date_for_chart = selected_date - timedelta(days=30)
        chart_df = df[(df['지점명'].isin(selected_stations)) & (df['TM'].dt.date >= start_date_for_chart) & (df['TM'].dt.date <= selected_date)].copy()
        if not chart_df.empty:
            pivot_df_temp = chart_df.pivot_table(index='TM', columns='지점명', values='TA')
            st.subheader("기온 (°C) 비교")
            st.line_chart(pivot_df_temp)
            pivot_df_humidity = chart_df.pivot_table(index='TM', columns='지점명', values='HM')
            st.subheader("상대습도 (%) 비교")
            st.line_chart(pivot_df_humidity)
        else:
            st.warning("선택하신 지점의 데이터가 부족하여 그래프를 표시할 수 없습니다.")
    else:
        st.info("비교할 지점을 한 곳 이상 선택해주세요.")

else:
    st.error("데이터를 불러오지 못했습니다. 앱을 재시작하거나 CSV 파일을 확인해주세요.")