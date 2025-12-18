import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# 1. ページ設定
st.set_page_config(page_title="UNIVERSAL RECRUIT DASHBOARD", layout="wide")

# 2. ログイン機能（1人分用）
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True

    st.markdown("<h2 style='text-align: center; color: #0366d6;'>🔐 RECRUIT DASHBOARD LOGIN</h2>", unsafe_allow_html=True)
    
    try:
        target_id = st.secrets["USER_ID"]
        target_pass = st.secrets["USER_PASSWORD"]
    except Exception:
        st.error("システムエラー: 管理画面(Secrets)で USER_ID と USER_PASSWORD を設定してください。")
        return False

    with st.form("login_form"):
        user_input = st.text_input("USER ID")
        password_input = st.text_input("PASSWORD", type="password")
        if st.form_submit_button("LOGIN"):
            if user_input == target_id and password_input == target_pass:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("IDまたはパスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 日付変換ロジック ---
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

# --- サイドバー：データコントロール ---
with st.sidebar:
    st.header("📂 DATA IMPORT")
    uploaded_file = st.file_uploader("CSVをアップロード", type=['csv'])
    st.divider()
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

if uploaded_file is not None:
    try:
        df_raw = pd.read_csv(uploaded_file)
        all_cols = df_raw.columns.tolist()

        st.sidebar.header("🎯 COLUMN MAPPING")
        
        def get_idx(keywords, col_list, default=0):
            for i, col in enumerate(col_list):
                if any(k in col for k in keywords): return i
            return default

        # 【修正ポイント】姓名それぞれの列を選択できるように変更
        st.sidebar.subheader("👤 氏名設定")
        map_last_name = st.sidebar.selectbox("「姓」（または氏名）の列", all_cols, index=get_idx(["姓", "氏名", "氏", "名前"], all_cols))
        map_first_name = st.sidebar.selectbox("「名」の列（無い場合は『無し』を選択）", ["無し"] + all_cols, index=get_idx(["名"], ["無し"] + all_cols))

        st.sidebar.subheader("📅 日付・状態設定")
        map_b_date = st.sidebar.selectbox("説明会予約日", all_cols, index=get_idx(["説明会", "予約日", "セミナー"], all_cols))
        map_b_st = st.sidebar.selectbox("説明会参加状態", all_cols, index=get_idx(["参加", "出席"], all_cols))
        map_s_st = st.sidebar.selectbox("選考希望状態", all_cols, index=get_idx(["希望", "ステータス"], all_cols))
        map_i1_d = st.sidebar.selectbox("一次選考日程", all_cols, index=get_idx(["一次", "1次", "面接日"], all_cols))
        map_i1_r = st.sidebar.selectbox("一次選考結果", all_cols, index=get_idx(["結果", "合否"], all_cols))
        map_n_d = st.sidebar.selectbox("二次案内メール送付日", all_cols, index=get_idx(["案内", "送付"], all_cols))
        map_i2_d = st.sidebar.selectbox("二次選考日程", all_cols, index=get_idx(["二次", "最終"], all_cols))

        # 【修正ポイント】姓名を結合して「Display_Name」を作成
        df = df_raw.copy()
        if map_first_name == "無し":
            df['Display_Name'] = df[map_last_name].fillna('Unknown')
        else:
            df['Display_Name'] = df[map_last_name].fillna('') + ' ' + df[map_first_name].fillna('')
        
        today = datetime.now()

        # 日付変換
        df['dt_b'] = pd.to_datetime(df[map_b_date].apply(parse_jp_date))
        df['dt_i1'] = pd.to_datetime(df[map_i1_d].apply(parse_jp_date))
        df['dt_n'] = pd.to_datetime(df[map_n_d].apply(parse_jp_date))

        # --- 解析ロジック ---
        res1 = df[(df['dt_b'] < today) & (df[map_b_st] != '参加') & (df['dt_b'].notna())]
        df_t2 = df[df[map_s_st].str.contains('希望', na=False)].copy()
        df_t2['elap'] = (today - df_t2['dt_b']).dt.days
        res2 = df_t2[(df_t2['elap'] >= 14) & (df_t2[map_i1_d].isna())]
        df_t3 = df[df[map_s_st].str.contains('考え中|検討', na=False)].copy()
        res3 = df_t3[(today - df_t3['dt_b']).dt.days >= 10]
        res4 = df[(df['dt_i1'] <= (today - timedelta(days=3))) & (df[map_i1_r].isna()) & (df['dt_i1'].notna())]
        df_t5 = df.copy()
        df_t5['elap_n'] = (today - pd.to_datetime(df_t5[map_n_d].apply(parse_jp_date))).dt.days
        res5 = df_t5[(df_t5['elap_n'] >= 7) & (df[map_i2_d].isna()) & (df[map_n_d].notna())]

        # --- 表示 ---
        st.markdown(f"# 📊 採用進捗分析: {uploaded_file.name}")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("説明会欠席", len(res1))
        with c2: st.metric("一次日程遅延", len(res2))
        with c3: st.metric("検討中フォロー", len(res3))
        with c4: st.metric("結果未送付", len(res4))
        with c5: st.metric("二次未確定", len(res5))

        st.divider()
        tabs = st.tabs(["説明会欠席", "一次遅延", "検討中", "結果未送付", "二次未確定"])
        with tabs[0]: st.dataframe(res1[['Display_Name', map_b_date, map_b_st]], use_container_width=True)
        with tabs[1]: st.dataframe(res2[['Display_Name', map_b_date, map_i1_d]], use_container_width=True)
        with tabs[2]: st.dataframe(res3[['Display_Name', map_b_date, map_s_st]], use_container_width=True)
        with tabs[3]: st.dataframe(res4[['Display_Name', map_i1_d, map_i1_r]], use_container_width=True)
        with tabs[4]: st.dataframe(res5[['Display_Name', map_n_d, map_i2_d]], use_container_width=True)

    except Exception as e:
        st.error(f"解析エラー: 選択した列を確認してください。 ({e})")
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")
