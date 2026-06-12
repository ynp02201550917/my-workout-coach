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
    
    # タブで「記録」と「次回の提案」を切り替え（スマホで押しやすい）
    tab1, tab2, tab3 = st.tabs(["筋トレ記録", "食事記録", "🔮 次回の提案"])

    # --- タブ1：筋トレ記録 ---
    with tab1:
        st.subheader("今日のトレーニング")
        w_date = st.date_input("日付", datetime.date.today(), key="w_date")
        part = st.selectbox("部位", ["胸", "背中", "脚", "肩", "腕", "腹筋"])
        menu = st.text_input("種目名（例: ベンチプレス）")
        details = st.text_input("回数・セット（例: 80kg 10回 3セット）")
        
        if st.button("筋トレを記録＆送信"):
            # DBに保存
            data = {"workout_date": str(w_date), "part": part, "menu_name": menu, "volume_details": details}
            supabase.table("workout_logs").insert(data).execute()
            
            # 直近の同じ種目のデータを取得してGeminiでフィードバック
            response = supabase.table("workout_logs").select("*").eq("menu_name", menu).order("workout_date", desc=True).limit(5).execute()
            history_text = "\n".join([f"・{r['workout_date']}: {r['volume_details']}" for r in response.data])
            
            prompt = f"ユーザーが今日の筋トレを記録しました：{menu}（{details}）。過去の履歴：\n{history_text}\n進捗を褒めつつ、次回に向けたアドバイスを150文字以内で論理的に述べてください。"
            ai_res = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt, config=genai.types.GenerateContentConfig(system_instruction="あなたは熱血トレーナーです。"))
            st.success("DBに保存しました！")
            st.info(ai_res.text)

    # --- タブ2：食事記録 ---
    with tab2:
        st.subheader("食事の記録とアドバイス")
        m_date = st.date_input("日付", datetime.date.today(), key="m_date")
        m_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"])
        content = st.text_area("食べた内容（例: ササミ、玄米、プロテイン）")
        
        if st.button("食事を記録＆アドバイスを貰う"):
            supabase.table("meal_logs").insert({"meal_date": str(m_date), "meal_type": m_type, "content": content}).execute()
            
            prompt = f"今日の{m_type}の内容：{content}。PFCバランスの観点から良かった点と、次の食事への改善点を150文字以内で辛口かつ論理的にアドバイスしてください。"
            ai_res = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt, config=genai.types.GenerateContentConfig(system_instruction="あなたはスポーツ栄養士です。"))
            st.success("DBに保存しました！")
            st.info(ai_res.text)

    # --- タブ3：次回のメニュー提案（今回の目玉！） ---
    with tab3:
        st.subheader("過去のデータから次回のメニューを生成")
        if st.button("AIに次回のメニューを提案してもらう"):
            # 直近2週間（14件）のトレーニング履歴をDBから全取得
            past_workouts = supabase.table("workout_logs").select("*").order("workout_date", desc=True).limit(14).execute()
            
            if past_workouts.data:
                history_text = "\n".join([f"・{r['workout_date']} [{r['part']}] {r['menu_name']}: {r['volume_details']}" for r in past_workouts.data])
            else:
                history_text = "過去の履歴はありません。新規の基本メニューを考えてください。"
                
            prompt = f"""
            ユーザーの直近のトレーニング履歴は以下の通りです：
            {history_text}
            
            【指示】
            1. 最後にどの部位をいつ鍛えたかを分析し、超回復の観点から今日（または次回）鍛えるべき最適な「部位」を特定してください。
            2. その部位の過去の重量・回数を踏まえ、過負荷の原則に従って、今回挑戦すべき「具体的な種目、セット数、目標重量と回数」を3つほど提案してください。
            """
            with st.spinner("過去のデータをスキャンしてメニューを計算中..."):
                ai_res = ai_client.models.generate_content(
                    model='gemini-1.5-flash', 
                    contents=prompt, 
                    config=genai.types.GenerateContentConfig(system_instruction="あなたは科学的根拠を重視するパーソナルトレーナーです。")
                )
            st.write(ai_res.text)
