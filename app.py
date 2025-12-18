import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# 1. ページ設定
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
        st.error("Secretsの設定を確認してください。")
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

# --- ヘッダー ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo.jpg", width=150)
    except:
        try:
            st.image("LOGO_Y(1).jpg", width=150)
        except:
            st.write("---")

with col_title:
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

            st.subheader("👤 氏名設定")
            map_last_name = st.selectbox("「姓」の列", all_cols, index=get_idx(["姓", "氏名", "氏"], all_cols))
            map_first_name = st.selectbox("「名」の列", ["無し"] + all_cols, index=get_idx(["名"], ["無し"] + all_cols))
            
            st.subheader("📅 日程・状態設定")
            map_b_date = st.selectbox("説明会/セミナー予約日", all_cols, index=get_idx(["予約日", "説明会", "セミナー"], all_cols))
            map_b_st = st.selectbox("説明会参加状態", all_cols, index=get_idx(["参加", "出席"], all_cols))
            map_s_st = st.selectbox("選考希望/ステータス", all_cols, index=get_idx(["希望", "状態"], all_cols))
            map_i1_d = st.selectbox("一次選考日程", all_cols, index=get_idx(["一次", "1次", "面接"], all_cols))
            map_i1_r = st.selectbox("選考結果（合否）", all_cols, index=get_idx(["結果", "合否"], all_cols))
            map_final_st = st.selectbox("最終結果/承諾状態", all_cols, index=get_idx(["最終", "承諾", "ステータス"], all_cols))
    
    st.divider()
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- メインコンテンツ ---
if uploaded_file is not None:
    try:
        df = df_raw.copy()
        if map_first_name == "無し":
            df['Display_Name'] = df[map_last_name].fillna('Unknown')
        else:
            df['Display_Name'] = df[map_last_name].fillna('') + ' ' + df[map_first_name].fillna('')
        
        today = datetime.now()
        df['dt_b'] = pd.to_datetime(df[map_b_date].apply(parse_jp_date))

        # --- 1. 歩留率（Conversion Rate）分析 ---
        st.subheader("📈 歩留まり分析")
        c_sel1, c_sel2 = st.columns(2)
        with c_sel1:
            stage = st.selectbox("分析フェーズ", ["セミナー予約", "説明会参加", "一次選考", "内定/承諾"])
        with c_sel2:
            if stage == "セミナー予約":
                m_type = st.selectbox("指標", ["出席率（対予約）", "欠席率（対予約）"])
            elif stage == "説明会参加":
                m_type = st.selectbox("指標", ["選考希望率（対参加）", "辞退率（対参加）"])
            elif stage == "一次選考":
                m_type = st.selectbox("指標", ["一次合格率（対一次参加）", "一次辞退率（対一次参加）"])
            else:
                m_type = st.selectbox("指標", ["内定率（対一次合格）", "内定承諾率（対内定）"])

        # 判定用フラグの作成
        is_reserved = df[map_b_date].notna() # セミナー予約者
        is_attended = df[map_b_st].str.contains('参加|出席', na=False) # 説明会参加者
        is_wanted = df[map_s_st].str.contains('希望', na=False) # 選考希望者
        is_interviewed = df[map_i1_d].notna() # 一次面接実施者
        is_i1_passed = df[map_i1_r].str.contains('合格|通過|次へ', na=False) # 一次合格者
        is_offered = df[map_final_st].str.contains('内定|合格', na=False) # 内定者
        is_accepted = df[map_final_st].str.contains('承諾|入社', na=False) # 承諾者

        num, den = 0, 0
        if stage == "セミナー予約":
            den = len(df) # CSVの全体数 = 予約者数
            num = is_attended.sum() if "出席率" in m_type else den - is_attended.sum()
        elif stage == "説明会参加":
            den = is_attended.sum()
            num = is_wanted.sum() if "希望率" in m_type else den - is_wanted.sum()
        elif stage == "一次選考":
            den = is_interviewed.sum()
            num = is_i1_passed.sum() if "合格率" in m_type else den - is_i1_passed.sum()
        elif stage == "内定/承諾":
            if "内定率" in m_type:
                den = is_i1_passed.sum() # 一次合格者のうち
                num = is_offered.sum()   # 内定まで至った人
            else:
                den = is_offered.sum()   # 内定者のうち
                num = is_accepted.sum()  # 承諾した人

        if den > 0:
            val = (num / den) * 100
            st.metric(f"{stage} {m_type}", f"{val:.1f}%", f"母数: {den} 名 / 対象: {num} 名")
            st.progress(val / 100)
        else:
            st.warning("分母となるデータが0件のため、算出できません。")

        # --- 2. 異常検知アラート（従来機能） ---
        st.divider()
        st.subheader("🔍 フォロー対象アラート")
        res1 = df[(df['dt_b'] < today) & (~is_attended) & (df['dt_b'].notna())]
        res2 = df[is_wanted & (df[map_i1_d].isna()) & ((today - df['dt_b']).dt.days >= 14)]
        
        ca1, ca2 = st.columns(2)
        with ca1:
            st.error(f"説明会欠席: {len(res1)}名")
            if len(res1) > 0: st.dataframe(res1[['Display_Name', map_b_date]], use_container_width=True)
        with ca2:
            st.warning(f"一次日程未設定（希望後14日〜）: {len(res2)}名")
            if len(res2) > 0: st.dataframe(res2[['Display_Name', map_b_date]], use_container_width=True)

    except Exception as e:
        st.error(f"解析エラー: {e}")
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")
