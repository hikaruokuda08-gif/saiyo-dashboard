import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import os

# 1. ページ設定
st.set_page_config(page_title="n8-Flow | Strategic Recruiting", layout="wide")

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

# --- ヘッダー（ロゴ固定） ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    logo_path = "logo.jpg" if os.path.exists("logo.jpg") else "LOGO_Y(1).jpg"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.info("LOGO AREA")

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
        try:
            df_raw = pd.read_csv(uploaded_file)
            all_cols = df_raw.columns.tolist()
        except Exception as e:
            st.error(f"CSV読み込みエラー: {e}")
            st.stop()

        with st.expander("🛠 詳細カラムマッピング", expanded=True):
            def get_idx(keywords, col_list, default=0):
                for i, col in enumerate(col_list):
                    if any(k in col for k in keywords): return i
                return default

            st.subheader("👤 基本情報")
            m_last = st.selectbox("姓（氏名）", all_cols, index=get_idx(["姓", "氏名"], all_cols))
            m_first = st.selectbox("名", ["無し"] + all_cols, index=get_idx(["名"], ["無し"] + all_cols))
            
            st.subheader("📅 説明会確認項目")
            m_b_date = st.selectbox("説明会予約日", all_cols, index=get_idx(["予約", "説明会"], all_cols))
            m_b_st = st.selectbox("説明会参加状態", all_cols, index=get_idx(["参加", "出席"], all_cols))
            m_chk_ank = st.selectbox("アンケート確認", all_cols, index=get_idx(["アンケート"], all_cols))
            m_chk_tel = st.selectbox("TEL確認", all_cols, index=get_idx(["TEL", "電話"], all_cols))
            m_chk_mail = st.selectbox("メール既読", all_cols, index=get_idx(["メール", "既読"], all_cols))
            
            st.subheader("⚖️ 選考・書類")
            m_s_st = st.selectbox("選考希望状態", all_cols, index=get_idx(["希望", "状態"], all_cols))
            m_resume = st.selectbox("履歴書回収", all_cols, index=get_idx(["履歴書"], all_cols))
            
            st.subheader("🏁 面接フェーズ")
            m_i1_d = st.selectbox("1次面接日", all_cols, index=get_idx(["一次", "1次"], all_cols))
            m_i1_r = st.selectbox("1次結果", all_cols, index=get_idx(["一次結果", "1次結果"], all_cols))
            m_i2_d = st.selectbox("2次面接日", all_cols, index=get_idx(["二次", "2次"], all_cols))
            m_i2_r = st.selectbox("2次結果", all_cols, index=get_idx(["二次結果", "2次結果"], all_cols))
            m_if_d = st.selectbox("最終面接日", all_cols, index=get_idx(["最終", "役員"], all_cols))
            m_if_r = st.selectbox("最終結果/承諾", all_cols, index=get_idx(["最終結果", "承諾"], all_cols))
    
    st.divider()
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- 解析実行 ---
if uploaded_file is not None:
    try:
        df = df_raw.dropna(subset=[m_last]).copy()
        df['FullName'] = df[m_last].fillna('') + (' ' + df[m_first].fillna('') if m_first != "無し" else '')
        today = datetime.now()

        # 【超重要】エラー対策：すべての判定用列を強制的に「文字列」に変換
        target_cols = [m_b_st, m_chk_ank, m_chk_tel, m_chk_mail, m_s_st, m_resume, m_i1_r, m_i2_r, m_if_r]
        for col in target_cols:
            df[col] = df[col].astype(str).replace('nan', '')

        # 日付変換
        df['dt_b'] = pd.to_datetime(df[m_b_date].apply(parse_jp_date))
        df['dt_i1'] = pd.to_datetime(df[m_i1_d].apply(parse_jp_date))
        df['dt_i2'] = pd.to_datetime(df[m_i2_d].apply(parse_jp_date))
        df['dt_if'] = pd.to_datetime(df[m_if_d].apply(parse_jp_date))

        # --- 判定フラグ ---
        # 1次欠席・当日欠席を辞退として扱う
        is_i1_absent = df[m_i1_r].str.contains('欠席|当日', na=False)
        is_withdrawn_any = (
            df[m_b_st].str.contains('辞退', na=False) | 
            df[m_s_st].str.contains('辞退', na=False) | 
            df[m_i1_r].str.contains('辞退', na=False) | 
            df[m_if_r].str.contains('辞退', na=False) |
            is_i1_absent
        )
        is_attended = df[m_b_st].str.contains('参加|出席', na=False) & ~df[m_b_st].str.contains('不参加|欠席|辞退', na=False)
        is_wanted = df[m_s_st].str.contains('希望', na=False) & ~is_withdrawn_any

        # --- 歩留まり分析 ---
        st.subheader("📈 歩留まり分析")
        cs1, cs2 = st.columns(2)
        with cs1: stage = st.selectbox("分析フェーズ", ["セミナー予約", "説明会参加", "一次選考", "内定/承諾"])
        with cs2:
            opts = {"セミナー予約":["出席率","欠席率"], "説明会参加":["希望率","辞退率"], "一次選考":["合格率","辞退率"], "内定/承諾":["内定率","承諾率"]}
            m_type = st.selectbox("指標", opts[stage])

        num, den = 0, 0
        if stage == "セミナー予約":
            den = len(df); num = is_attended.sum() if "出席率" in m_type else den - is_attended.sum()
        elif stage == "説明会参加":
            den = is_attended.sum(); num = is_wanted.sum() if "希望率" in m_type else is_withdrawn_any[is_attended].sum()
        elif stage == "一次選考":
            den = (df[m_i1_d].notna()).sum()
            num = (df[m_i1_r].str.contains('合格|通過', na=False)).sum() if "合格率" in m_type else is_withdrawn_any[df[m_i1_d].notna()].sum()
        elif stage == "内定/承諾":
            den = (df[m_if_r].str.contains('内定|合格', na=False)).sum()
            num = (df[m_if_r].str.contains('承諾|入社', na=False)).sum()

        if den > 0:
            val = (num / den) * 100
            st.metric(f"{stage} {m_type}", f"{val:.1f}%", f"母数: {den} / 対象: {num}")
            st.progress(val / 100)

        # --- 重点フォローアラート ---
        st.divider()
        st.subheader("🚨 重点フォローアラート")
        
        # 1. 開催3日前未確認
        alert1 = df[(df['dt_b'].notna()) & (df['dt_b'] <= today + timedelta(days=3)) & (df['dt_b'] >= today) &
                    (~df[m_chk_ank].str.contains('済|確', na=False)) & (~df[m_chk_tel].str.contains('済|確', na=False)) & (~df[m_chk_mail].str.contains('済|既', na=False))]
        # 2. 日程未設定10日経過
        alert2 = df[is_wanted & (df[m_i1_d].isna()) & ((today - df['dt_b']).dt.days >= 10)]
        # 3. 面接結果入力漏れ
        a3_i1 = df[(df['dt_i1'] <= today - timedelta(days=3)) & (df[m_i1_r] == '')]
        a3_i2 = df[(df['dt_i2'] <= today - timedelta(days=3)) & (df[m_i2_r] == '')]
        a3_if = df[(df['dt_if'] <= today - timedelta(days=3)) & (df[m_if_r] == '')]
        alert3 = pd.concat([a3_i1, a3_i2, a3_if]).drop_duplicates()
        # 4. 書類未回収
        alert4 = df[(df['dt_i1'] <= today - timedelta(days=3)) & (~df[m_resume].str.contains('済み', na=False)) & (~is_withdrawn_any)]

        t1, t2, t3, t4 = st.tabs([f"開催前未確認 ({len(alert1)})", f"日程未設定 ({len(alert2)})", f"結果未入力 ({len(alert3)})", f"書類未回収 ({len(alert4)})"])
        with t1: st.dataframe(alert1[['FullName', m_b_date, m_chk_ank, m_chk_tel, m_chk_mail]], use_container_width=True)
        with t2: st.dataframe(alert2[['FullName', m_b_date]], use_container_width=True)
        with t3: st.dataframe(alert3[['FullName', m_i1_d, m_i2_d, m_if_d]], use_container_width=True)
        with t4: st.dataframe(alert4[['FullName', m_i1_d, m_resume]], use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ 解析中にエラーが発生しました。設定を確認してください。")
        st.exception(e)
else:
    st.info("CSVをアップロードしてください。")
