import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# ページ設定
st.set_page_config(page_title="RECRUITING DASHBOARD", layout="wide")

# --- CSS: プロフェッショナル・ダッシュボード・スタイル ---
st.markdown("""
    <style>
    /* 全体背景とフォント */
    .stApp { background-color: #f0f2f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* カードのデザイン */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e1e4e8;
        text-align: center;
    }
    .metric-label { font-size: 0.9rem; color: #586069; font-weight: 600; margin-bottom: 5px; }
    .metric-value { font-size: 1.8rem; color: #0366d6; font-weight: 800; }
    
    /* アラートセクション */
    .alert-section {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        margin-top: 10px;
        border-left: 5px solid #0366d6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 判定ロジック関数 ---
def parse_jp_date(text, base_year=2025):
    if pd.isna(text) or text == '': return pd.NaT
    text = str(text)
    match_ymd = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', text)
    if match_ymd: return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
    match_md = re.search(r'(\d{1,2})月(\d{1,2})日', text)
    if match_md:
        m, d = int(match_md.group(1)), int(match_md.group(2))
        return datetime(base_year + 1 if m <= 3 else base_year, m, d)
    return pd.NaT

# --- ヘッダー ---
st.markdown("# 📊 採用進捗エグゼクティブ・ダッシュボード")
st.markdown("---")

# サイドバー
with st.sidebar:
    st.header("⚙️ DATA CONTROL")
    uploaded_file = st.file_uploader("CSVをアップロード", type=['csv'])
    today = datetime.now()
    st.info(f"基準日: {today.strftime('%Y/%m/%d')}")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df['氏名'] = df['姓'].fillna('') + ' ' + df['名'].fillna('')
        
        # カラム設定
        COL_B = '説明会\n予約日'
        COL_B_ST = '説明会参加\nオープンカンパニー'
        COL_S_ST = '選考希望'
        COL_I1_D = '【一次選考】\n日程\n（入力例：11月4日(火)14:00開始）'
        COL_I1_R = '【一次選考】\n結果'
        COL_N_D = '【二次選考】\n案内メール\n送付' 
        COL_I2_D = '【二次選考】\n最終選考日程\n（入力例：11月4日(火)14:00開始）'

        # 日付変換
        df['dt_b'] = pd.to_datetime(df[COL_B].apply(parse_jp_date))
        df['dt_i1'] = pd.to_datetime(df[COL_I1_D].apply(parse_jp_date))
        df['dt_n'] = pd.to_datetime(df[COL_N_D].apply(parse_jp_date))
        df['dt_i2'] = pd.to_datetime(df[COL_I2_D].apply(parse_jp_date))

        # --- データの抽出計算 ---
        res1 = df[(df['dt_b'] < today) & (df[COL_B_ST] != '参加') & (df['dt_b'].notna())]
        
        df_t2 = df[df[COL_S_ST] == '希望'].copy()
        df_t2['gap'] = (df_t2['dt_i1'] - df_t2['dt_b']).dt.days
        df_t2['elap'] = (today - df_t2['dt_b']).dt.days
        res2 = df_t2[(df_t2['gap'] >= 14) | ((df_t2['dt_i1'].isna()) & (df_t2['elap'] >= 14))]
        
        df_t3 = df[df[COL_S_ST] == '考え中'].copy()
        df_t3['elap'] = (today - df_t3['dt_b']).dt.days
        res3 = df_t3[df_t3['elap'] >= 10]
        
        res4 = df[(df['dt_i1'] <= (today - timedelta(days=3))) & (df[COL_I1_R].isna()) & (df['dt_i1'].notna())]
        
        df_t5 = df.copy()
        df_t5['elap_n'] = (today - df_t5['dt_n']).dt.days
        res5 = df_t5[(df_t5['elap_n'] >= 7) & (df_t5['dt_i2'].isna()) & (df_t5['dt_n'].notna())]

        # --- 1. サマリーメトリクス (横並びカード) ---
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>説明会欠席</div><div class='metric-value'>{len(res1)}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>一次日程遅延</div><div class='metric-value'>{len(res2)}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>検討中フォロー</div><div class='metric-value'>{len(res3)}</div></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='metric-card'><div class='metric-label'>結果未送付</div><div class='metric-value'>{len(res4)}</div></div>", unsafe_allow_html=True)
        with c5: st.markdown(f"<div class='metric-card'><div class='metric-label'>二次未確定</div><div class='metric-value'>{len(res5)}</div></div>", unsafe_allow_html=True)

        st.markdown("### 🔍 アラート詳細分析")

        # --- 2. グラフとリストの並列表示 ---
        col_main, col_chart = st.columns([3, 1])

        with col_main:
            target_tab = st.radio("表示するアラートを選択してください", 
                                  ["説明会欠席", "一次日程遅延", "検討中フォロー", "結果未送付", "二次未確定"],
                                  horizontal=True)
            
            if target_tab == "説明会欠席":
                st.write("**対象者リスト**")
                st.dataframe(res1[['氏名', COL_B, COL_B_ST]], use_container_width=True)
            elif target_tab == "一次日程遅延":
                st.write("**対象者リスト**")
                st.dataframe(res2[['氏名', COL_B, COL_I1_D]], use_container_width=True)
            elif target_tab == "検討中フォロー":
                st.write("**対象者リスト**")
                st.dataframe(res3[['氏名', COL_B, COL_S_ST]], use_container_width=True)
            elif target_tab == "結果未送付":
                st.write("**対象者リスト**")
                st.dataframe(res4[['氏名', COL_I1_D, COL_I1_R]], use_container_width=True)
            elif target_tab == "二次未確定":
                st.write("**対象者リスト**")
                st.dataframe(res5[['氏名', COL_N_D, COL_I2_D]], use_container_width=True)

        with col_chart:
            st.write("**アラート比率**")
            chart_data = pd.DataFrame({
                'Category': ["欠席", "一次遅", "検討中", "未送付", "二次未"],
                'Count': [len(res1), len(res2), len(res3), len(res4), len(res5)]
            })
            st.bar_chart(chart_data.set_index('Category'))

    except Exception as e:
        st.error(f"データ解析エラー: {e}")
else:
    st.info("左側のサイドバーから管理シート(CSV)をアップロードしてください。")