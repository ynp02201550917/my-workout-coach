import streamlit as st
from supabase import create_client, Client
from google import genai
import datetime

# --- セキュリティ対策③：パスワード簡易認証 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    st.subheader("🔒 自分専用 AIコーチログイン")
    user_password = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if user_password == st.secrets["MY_APP_PASSWORD"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False

if check_password():
    # --- 安全なキーの読み込み（セキュリティ対策①） ---
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

    # クライアント初期化
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai_client = genai.Client(api_key=GEMINI_API_KEY)

    # スマホ対応UIの構築
    st.title("🏋️‍♂️ 専属AIコーチ（スマホ版）")
    
    # --- 【アップデート】Supabaseから「最新の」ユーザープロフィールを取得 ---
    try:
        profile_res = supabase.table("user_profiles").select("*").order("created_at", desc=True).limit(1).execute()
        if profile_res.data:
            db_profile = profile_res.data[0]
        else:
            db_profile = {
                "age": 31, "height": 170.0, "weight": 61.8, 
                "muscle_mass": 45.0, "fat_percentage": 18.0, 
                "purpose": "引き締め（ちょいムキ）", "activity": "低い（デスクワーク中心）"
            }
    except Exception as e:
        st.error(f"プロフィール読み込みエラー: {e}")
        db_profile = {
            "age": 31, "height": 170.0, "weight": 61.8, 
            "muscle_mass": 45.0, "fat_percentage": 18.0,
            "purpose": "引き締め（ちょいムキ）", "activity": "低い（デスクワーク中心）"
        }

    # --- ユーザープロフィール入力エリア（アコーディオンで開閉可能） ---
    with st.expander("👤 ユーザープロフィール設定（AI分析用）", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            age = st.number_input("年齢", min_value=0, max_value=120, value=int(db_profile["age"]), step=1)
        with col2:
            height = st.number_input("身長 (cm)", min_value=100.0, max_value=250.0, value=float(db_profile["height"]), step=0.1)
        with col3:
            weight = st.number_input("体重 (kg)", min_value=30.0, max_value=200.0, value=float(db_profile["weight"]), step=0.1)
            
        col4, col5 = st.columns(2)
        with col4:
            muscle_mass = st.number_input("筋肉量 (kg)", min_value=10.0, max_value=150.0, value=float(db_profile.get("muscle_mass", 45.0)), step=0.1)
        with col5:
            fat_percentage = st.number_input("体脂肪率 (%)", min_value=3.0, max_value=50.0, value=float(db_profile.get("fat_percentage", 18.0)), step=0.1)
            
        purpose_options = ["引き締め（ちょいムキ）", "バルクアップ（筋肥大）", "ダイエット（減量）", "現状維持"]
        activity_options = ["低い（デスクワーク中心）", "普通（立ち仕事・軽い運動）", "高い（活発な肉体労働・毎日ハードな運動）"]
        
        p_index = purpose_options.index(db_profile["purpose"]) if db_profile["purpose"] in purpose_options else 0
        a_index = activity_options.index(db_profile["activity"]) if db_profile["activity"] in activity_options else 0

        purpose = st.selectbox("トレーニングの目的", purpose_options, index=p_index)
        activity = st.selectbox("日々の活動量", activity_options, index=a_index)
        
        if st.button("プロフィールを更新して保存"):
            new_history_data = {
                "age": age,
                "height": height,
                "weight": weight,
                "muscle_mass": muscle_mass,   
                "fat_percentage": fat_percentage, 
                "purpose": purpose,
                "activity": activity
            }
            supabase.table("user_profiles").insert(new_history_data).execute()
            st.success("最新のプロフィールを履歴に保存しました！")
            st.rerun()

    # AIに渡すプロンプト用テキスト（タブ3の提案機能でのみ使用）
    user_profile_text =
