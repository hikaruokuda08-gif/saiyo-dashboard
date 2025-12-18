import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# 1. ページ設定（ブラウザのタブに表示される名前）
st.set_page_config(page_title="n8-Flow | Recruitment Analytics", layout="wide")

# 2. ログイン機能
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True

    st.markdown("<h2 style='text-align: center; color: #0366d6;'>🔐 n8-Flow LOGIN</h2>", unsafe_allow_html=True)
    try:
        target_id = st.secrets["USER_ID"]
        target_pass = st.secrets["USER_PASSWORD"]
    except Exception:
        st.error("システムエラー: Secretsの設定を確認してください。")
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

# --- ヘッダー部分：ロゴとプロダクト名 ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    # 先ほどGitHubにアップしたファイル名に合わせてください。
    # もし名前を "logo.jpg" に変えていない場合は、ここを "LOGO_Y(1).jpg" に書き換えてください。
    try:
        st.image("logo.jpg", width=150) 
    except:
        try:
            st.image("LOGO_Y(1).jpg", width=150)
        except:
            st.warning("ロゴ画像ファイルが見つかりません。GitHubのファイル名を確認してください。")

with col_title:
    # プロダクト名を大きく表示
    st.markdown("<h1 style='margin-bottom: 0;'>n8-Flow <span style='font-size: 0.6em; color: #666;'>（エイト・フロー）</span></h1>", unsafe_allow_html=True)
    st.caption("Strategic Recruitment Analytics Dashboard | powered by number eight Inc.")

st.divider()

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
    
    if uploaded_file is not None:
        with st.expander("🛠 CSV項目設定（カラムマッピング）"):
            df_raw = pd.read_csv(uploaded_file)
            all_cols = df_raw.columns.tolist()
            def get_idx(keywords, col_list, default=0):
                for i, col in enumerate(col_list):
                    if any(k in col for k in keywords): return i
                return default

            map_last_name = st.selectbox("「姓」の列", all_cols, index=get_idx(["姓", "氏名", "氏"], all_cols))
            map_first_name = st.selectbox("「名」の列", ["無し"] + all_cols, index=get_idx(["名"], ["無し"] + all_cols))
            map_b_date = st.selectbox("説明会予約日", all_cols, index=get_idx(["予約日", "説明会"], all_cols))
            map_b_st = st.selectbox("説明会参加状態", all_cols, index=get_idx(["参加", "出席"], all_cols))
            map_s_st = st.selectbox("選考希望状態", all_cols, index=get_idx(["希望", "ステータス"], all_cols))
            map_i1_d = st.selectbox("一次選考日程", all_cols, index=get_idx(["一次", "1次", "面接日"], all_cols))
            map_i1_r = st.selectbox("一次選考結果", all_cols, index=get_idx(["結果", "合否"], all_cols))
            map_n_d = st.selectbox("二次案内日", all_cols, index=get_idx(["案内", "送付"], all_cols))
            map_i2_d = st.selectbox("二次選考日程", all_cols, index=get_idx(["最終", "二次"], all_cols))
    
    st.divider()
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- メインコンテンツ ---
if uploaded_file is not None:
    try:
        df = df_raw.copy()
        # 姓名合体表示
        if map_first_name == "無し":
            df['Display_Name'] = df[map_last_name].fillna('Unknown')
        else:
            df['Display_Name'] = df[map_last_name].fillna('') + ' ' + df[map_first_name].fillna('')
        
        today = datetime.now()
        df['dt_b'] = pd.to_datetime(df[map_b_date].apply(parse_jp_date))
        df['dt_i1'] = pd.to_datetime(df[map_i1_d].apply(parse_jp_date))

        # --- 歩留率分析 ---
        st.subheader("📈 歩留まり（Conversion Rate）分析")
        c_sel1, c_sel2 = st.columns(2)
        with c_sel1:
            stage = st.selectbox("分析フェーズ", ["説明会", "選考希望", "1次選考"])
        with c_sel2:
            if stage == "説明会":
                m_type = st.selectbox("指標", ["参加率", "欠席率"])
            elif stage == "選考希望":
                m_type = st.selectbox("指標", ["希望率", "辞退・検討率"])
            else:
                m_type = st.selectbox("指標", ["面接参加率", "合格率", "辞退率"])

        is_attended = df[map_b_st].str.contains('参加|出席', na=False)
        is_wanted = df[map_s_st].str.contains('希望', na=False)
        is_interviewed = df[map_i1_d].notna()
        is_passed = df[map_i1_r].str.contains('合格|通過|次へ', na=False)
        is_withdrawn = df[map_i1_r].str.contains('辞退', na=False) | df[map_s_st].str.contains('辞退', na=False)

        num, den = 0, 0
        if stage == "説明会":
            den = df[map_b_date].notna().sum()
            num = is_attended.sum() if m_type == "参加率" else den - is_attended.sum()
        elif stage == "選考希望":
            den = is_attended.sum()
            num = is_wanted.sum() if m_type == "希望率" else den - is_wanted.sum()
        elif stage == "1次選考":
            if m_type == "面接参加率":
                den, num = is_wanted.sum(), is_interviewed.sum()
            elif m_type == "合格率":
                den, num = is_interviewed.sum(), is_passed.sum()
            else:
                den, num = is_interviewed.sum(), is_withdrawn.sum()

        if den > 0:
            val = (num / den) * 100
            st.metric(f"{stage}の{m_type}", f"{val:.1f}%", f"全体 {den} 名中 {num} 名")
            st.progress(val / 100)
        else:
            st.warning("データが不足しています。")

        # --- アラート ---
        st.divider()
        st.subheader("🔍 フォロー対象アラート")
        res1 = df[(df['dt_b'] < today) & (~is_attended) & (df['dt_b'].notna())]
        df_t2 = df[is_wanted].copy()
        res2 = df_t2[((today - df_t2['dt_b']).dt.days >= 14) & (df_t2[map_i1_d].isna())]
        
        ca1, ca2 = st.columns(2)
        with ca1:
            st.error(f"説明会欠席: {len(res1)}名")
            if len(res1) > 0: st.dataframe(res1[['Display_Name', map_b_date]], use_container_width=True)
        with ca2:
            st.warning(f"一次日程遅延: {len(res2)}名")
            if len(res2) > 0: st.dataframe(res2[['Display_Name', map_b_date]], use_container_width=True)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")
