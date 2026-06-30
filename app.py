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
    
    # --- 【アップデート】Supabaseからユーザープロフィールを取得 ---
    try:
        profile_res = supabase.table("user_profiles").select("*").eq("id", 1).execute()
        if profile_res.data:
            db_profile = profile_res.data[0]
        else:
            # 万が一データがない場合のデフォルト値
            db_profile = {"age": 31, "height": 170.0, "weight": 61.8, "purpose": "引き締め（ちょいムキ）", "activity": "低い（デスクワーク中心）"}
    except Exception as e:
        st.error(f"プロフィール読み込みエラー: {e}")
        db_profile = {"age": 31, "height": 170.0, "weight": 61.8, "purpose": "引き締め（ちょいムキ）", "activity": "低い（デスクワーク中心）"}

    # --- ユーザープロフィール入力エリア（アコーディオンで開閉可能） ---
    with st.expander("👤 ユーザープロフィール設定（AI分析用）", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            # DBから取得した値を value にセット
            age = st.number_input("年齢", min_value=0, max_value=120, value=int(db_profile["age"]), step=1)
        with col2:
            height = st.number_input("身長 (cm)", min_value=100.0, max_value=250.0, value=float(db_profile["height"]), step=0.1)
        with col3:
            weight = st.number_input("体重 (kg)", min_value=30.0, max_value=200.0, value=float(db_profile["weight"]), step=0.1)
            
        purpose_options = ["引き締め（ちょいムキ）", "バルクアップ（筋肥大）", "ダイエット（減量）", "現状維持"]
        activity_options = ["低い（デスクワーク中心）", "普通（立ち仕事・軽い運動）", "高い（活発な肉体労働・毎日ハードな運動）"]
        
        # DBに保存されている文字列がリストの何番目にあるかを探して初期選択にする
        p_index = purpose_options.index(db_profile["purpose"]) if db_profile["purpose"] in purpose_options else 0
        a_index = activity_options.index(db_profile["activity"]) if db_profile["activity"] in activity_options else 0

        purpose = st.selectbox("トレーニングの目的", purpose_options, index=p_index)
        activity = st.selectbox("日々の活動量", activity_options, index=a_index)
        
        # 保存ボタン
        if st.button("プロフィールを更新して保存"):
            updated_data = {
                "id": 1,
                "age": age,
                "height": height,
                "weight": weight,
                "purpose": purpose,
                "activity": activity
            }
            # id=1 のデータを上書き(upsert)
            supabase.table("user_profiles").upsert(updated_data).execute()
            st.success("プロファイルをSupabaseに保存しました！次回からもこの値が自動で読み込まれます。")
            st.rerun()

    # ユーザー情報をプロンプト用テキストにまとめる
    user_profile_text = f"【ユーザー情報】年齢: {age}歳, 身長: {height}cm, 体重: {weight}kg, 目的: {purpose}, 活動量: {activity}"

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
            data = {"workout_date": str(w_date), "part": part, "menu_name": menu, "volume_details": details}
            supabase.table("workout_logs").insert(data).execute()
            
            response = supabase.table("workout_logs").select("*").eq("menu_name", menu).order("workout_date", desc=True).limit(5).execute()
            history_text = "\n".join([f"・{r['workout_date']}: {r['volume_details']}" for r in response.data])
            
            prompt = f"{user_profile_text}\nユーザーが今日の筋トレを記録しました：{menu}（{details}）。過去の履歴：\n{history_text}\nユーザーの体型や目的に合わせて進捗を褒めつつ、次回に向けたアドバイスを150文字以内で論理的に述べてください。"
            ai_res = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=genai.types.GenerateContentConfig(system_instruction="あなたは熱血トレーナーです。"))
            st.success("DBに保存しました！")
            st.info(ai_res.text)

    # --- タブ2：食事記録 ---
    with tab2:
        st.subheader("食事の記録とアドバイス")
        m_date = st.date_input("日付", datetime.date.today(), key="m_date")
        m_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"])
        content = st.text_area("食べた内容（例: ササミ、玄米、プロテイン）")
        
        if st.button("食事を記録＆アドバイスを貰う"):
            if content:
                try:
                    st.write("📡 Supabaseに接続を試みています...")
                    
                    supabase.table("meal_logs").insert({"meal_date": str(m_date), "meal_type": m_type, "content": content}).execute()
                    st.success("DBに保存しました！")
                    
                    with st.spinner("AIコーチが食事内容を分析中..."):
                        prompt = f"{user_profile_text}\n今日の{m_type}の内容：{content}。このユーザーの年齢・体重・目的に対するPFCバランスの観点から良かった点と、次の食事への改善点を150文字以内で辛口かつ論理的にアドバイスしてください。"
                        ai_res = ai_client.models.generate_content(
                            model='gemini-2.5-flash', 
                            contents=prompt, 
                            config=genai.types.GenerateContentConfig(system_instruction="あなたはスポーツ栄養士です。")
                        )
                    st.info(ai_res.text)
                    
                except Exception as e:
                    st.error(f"❌ 接続エラーの本当の理由: {str(e)}")
            else:
                st.warning("食事内容を入力してください。")

    # --- タブ3：次回のメニュー提案 ---
    with tab3:
        st.subheader("過去のデータと要望から次回のメニューを生成")
        
        # 💡 追加：ユーザーが自由に要望を入力できるテキストエリア
        user_request = st.text_area(
            "AIへの特別な要望（例: 「出張中なので自重のみ」「肩を痛めているので避けて」「時短15分で」など）",
            placeholder="特にない場合は空欄のままでOKです"
        )
        
        if st.button("AIに次回のメニューを提案してもらう"):
            past_workouts = supabase.table("workout_logs").select("*").order("workout_date", desc=True).limit(14).execute()
            
            if past_workouts.data:
                history_text = "\n".join([f"・{r['workout_date']} [{r['part']}] {r['menu_name']}: {r['volume_details']}" for r in past_workouts.data])
            else:
                history_text = "過去の履歴はありません。新規の基本メニューを考えてください。"
                
            # 💡 アップデート：ユーザーの自由入力をプロンプトに組み込む
            prompt = f"""
            {user_profile_text}
            
            ユーザーの直近のトレーニング履歴は以下の通りです：
            {history_text}
            
            【ユーザーからの個別要望】
            {user_request if user_request else "特になし。履歴に基づき最適なメニューを提案してください。"}
            
            【指示】
            1. ユーザーのプロフィールと過去の履歴を考慮し、さらに「ユーザーからの個別要望」が記載されている場合はそれを最優先して、今日（または次回）鍛えるべき最適なメニューを特定してください。
            2. 過負荷の原則や超回復、およびユーザーのコンディションに配慮し、今回挑戦すべき「具体的な種目、セット数、目標重量と回数」を3つほど提案してください。
            """
            
            with st.spinner("過去のデータと要望を分析してメニューを計算中..."):
                ai_res = ai_client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=prompt, 
                    config=genai.types.GenerateContentConfig(system_instruction="あなたは科学的根拠を重視し、ユーザーの状況に柔軟に寄り添うパーソナルトレーナーです。")
                )
            st.write(ai_res.text)
