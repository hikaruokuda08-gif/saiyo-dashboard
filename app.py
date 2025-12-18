import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# 1. ページ設定
st.set_page_config(page_title="RECRUIT ANALYTICS DASHBOARD", layout="wide")

# 2. ログイン機能
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

# --- サイドバー ---
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

        # カラムマッピング
        map_last_name = st.sidebar.selectbox("「姓」の列", all_cols, index=get_idx(["姓", "氏名", "氏"], all_cols))
        map_first_name = st.sidebar.selectbox("「名」の列", ["無し"] + all_cols, index=get_idx(["名"], ["無し"] + all_cols))
        map_b_date = st.sidebar.selectbox("説明会予約日", all_cols, index=get_idx(["予約日", "説明会"], all_cols))
        map_b_st = st.sidebar.selectbox("説明会参加状態", all_cols, index=get_idx(["参加", "出席"], all_cols))
        map_s_st = st.sidebar.selectbox("選考希望状態", all_cols, index=get_idx(["希望", "ステータス"], all_cols))
        map_i1_d = st.sidebar.selectbox("一次選考日程", all_cols, index=get_idx(["一次", "面接日"], all_cols))
        map_i1_r = st.sidebar.selectbox("一次選考結果", all_cols, index=get_idx(["結果", "合否"], all_cols))
        map_n_d = st.sidebar.selectbox("二次案内日", all_cols, index=get_idx(["案内", "送付"], all_cols))
        map_i2_d = st.sidebar.selectbox("二次選考日程", all_cols, index=get_idx(["最終", "二次"], all_cols))

        # データ加工
        df = df_raw.copy()
        if map_first_name == "無し":
            df['Display_Name'] = df[map_last_name].fillna('Unknown')
        else:
            df['Display_Name'] = df[map_last_name].fillna('') + ' ' + df[map_first_name].fillna('')
        
        today = datetime.now()
        df['dt_b'] = pd.to_datetime(df[map_b_date].apply(parse_jp_date))
        df['dt_i1'] = pd.to_datetime(df[map_i1_d].apply(parse_jp_date))

        # --- 歩留率分析セクション ---
        st.markdown("## 📈 歩留率（歩留まり）分析")
        
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            stage = st.selectbox("1. 分析するフェーズを選択", ["説明会", "選考希望", "1次選考"])
        with col_sel2:
            if stage == "説明会":
                metric_type = st.selectbox("2. 指標を選択", ["参加率", "キャンセル・欠席率"])
            elif stage == "選考希望":
                metric_type = st.selectbox("2. 指標を選択", ["希望率", "検討・辞退率"])
            else:
                metric_type = st.selectbox("2. 指標を選択", ["面接参加率", "合格率", "辞退率"])

        # --- 計算ロジック ---
        # 共通フラグ
        is_reserved = df[map_b_date].notna()
        is_attended = df[map_b_st].str.contains('参加|出席', na=False)
        is_wanted = df[map_s_st].str.contains('希望', na=False)
        is_interviewed = df[map_i1_d].notna()
        is_passed = df[map_i1_r].str.contains('合格|通過|次へ', na=False)
        is_rejected = df[map_i1_r].str.contains('不合格|お見送り', na=False)
        is_withdrawn = df[map_i1_r].str.contains('辞退', na=False) | df[map_s_st].str.contains('辞退', na=False)

        val = 0.0
        label = f"{stage}の{metric_type}"
        num, den = 0, 0

        if stage == "説明会":
            den = is_reserved.sum()
            if metric_type == "参加率":
                num = is_attended.sum()
            else:
                num = den - is_attended.sum()
        elif stage == "選考希望":
            den = is_attended.sum()
            if metric_type == "希望率":
                num = is_wanted.sum()
            else:
                num = den - is_wanted.sum()
        elif stage == "1次選考":
            if metric_type == "面接参加率":
                den = is_wanted.sum()
                num = is_interviewed.sum()
            elif metric_type == "合格率":
                den = is_interviewed.sum()
                num = is_passed.sum()
            else:
                den = is_interviewed.sum()
                num = is_withdrawn.sum()

        if den > 0:
            val = (num / den) * 100
            st.metric(label, f"{val:.1f}%", help=f"分母: {den}名 / 分子: {num}名")
            st.progress(val / 100)
        else:
            st.warning("データが不足しているため算出できません。")

        st.divider()

        # --- アラート表示セクション（従来機能） ---
        st.markdown("## 🔍 異常検知・フォローアラート")
        res1 = df[(df['dt_b'] < today) & (~is_attended) & (df['dt_b'].notna())]
        df_t2 = df[is_wanted].copy()
        res2 = df_t2[((today - df_t2['dt_b']).dt.days >= 14) & (df_t2[map_i1_d].isna())]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("説明会欠席", len(res1))
        c2.metric("一次日程遅延", len(res2))
        # (他のメトリクスも同様に追加可能)

        tabs = st.tabs(["説明会欠席リスト", "一次日程遅延リスト"])
        with tabs[0]: st.dataframe(res1[['Display_Name', map_b_date, map_b_st]], use_container_width=True)
        with tabs[1]: st.dataframe(res2[['Display_Name', map_b_date, map_i1_d]], use_container_width=True)

    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")
