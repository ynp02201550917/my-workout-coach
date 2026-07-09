import streamlit as st
from supabase import create_client, Client
from google import genai
import datetime
from collections import defaultdict

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
            age = st.number_input("年齢", min_value=0, max_value=120, value=int(db_profile["age"]), step=1, key="prof_age")
        with col2:
            height = st.number_input("身長 (cm)", min_value=100.0, max_value=250.0, value=float(db_profile["height"]), step=0.1, key="prof_height")
        with col3:
            weight = st.number_input("体重 (kg)", min_value=30.0, max_value=200.0, value=float(db_profile["weight"]), step=0.1, key="prof_weight")
            
        col4, col5 = st.columns(2)
        with col4:
            muscle_mass = st.number_input("筋肉量 (kg)", min_value=10.0, max_value=150.0, value=float(db_profile.get("muscle_mass", 45.0)), step=0.1, key="prof_muscle")
        with col5:
            fat_percentage = st.number_input("体脂肪率 (%)", min_value=3.0, max_value=50.0, value=float(db_profile.get("fat_percentage", 18.0)), step=0.1, key="prof_fat")
            
        purpose_options = ["引き締め（ちょいムキ）", "バルクアップ（筋肥大）", "ダイエット（減量）", "現状維持"]
        activity_options = ["低い（デスクワーク中心）", "普通（立ち仕事・軽い運動）", "高い（活発な肉体労働・毎日ハードな運動）"]
        
        p_index = purpose_options.index(db_profile["purpose"]) if db_profile["purpose"] in purpose_options else 0
        a_index = activity_options.index(db_profile["activity"]) if db_profile["activity"] in activity_options else 0

        purpose = st.selectbox("トレーニングの目的", purpose_options, index=p_index, key="prof_purpose")
        activity = st.selectbox("日々の活動量", activity_options, index=a_index, key="prof_activity")
        
        if st.button("プロフィールを更新して保存", key="prof_save_btn"):
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

    # --- ジム器具の管理エリア（アコーディオン） ---
    with st.expander("🏋️‍♂️ ジムの導入器具・設備登録＆編集", expanded=False):
        st.subheader("🆕 新しい器具の登録")
        eq_category = st.selectbox(
            "エリア・カテゴリ", 
            ["プレートロード", "マシンエリア", "フリーウエイト", "ファンクショナル", "カーディオエリア", "設備・その他"],
            key="eq_cat_select"
        )
        eq_name = st.text_input("器具・設備名（例: コンバージング・チェストプレス）", key="eq_name_input")
        
        if st.button("ジムの器具を登録する", key="eq_save_btn"):
            if eq_name:
                try:
                    supabase.table("gym_equipments").insert({"category": eq_category, "name": eq_name}).execute()
                    st.success(f"✅ 【{eq_category}】に「{eq_name}」を追加しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")
            else:
                st.warning("器具・設備名を入力してください。")
        
        st.markdown("---")
        st.subheader("🛠️ 登録済み器具の管理（編集・削除）")
        
        # データベースから最新の器具リストを取得
        try:
            eq_res = supabase.table("gym_equipments").select("*").order("category").execute()
            raw_equipments = eq_res.data if eq_res.data else []
        except Exception as e:
            st.error(f"器具データの取得失敗: {e}")
            raw_equipments = []

        if raw_equipments:
            # 1つずつの器具を編集・削除できるリストを生成
            for item in raw_equipments:
                # スマホでも並びが良いように3カラム構成（名前入力、カテゴリ、削除ボタン）
                edit_col1, edit_col2, edit_col3 = st.columns([2, 2, 1])
                
                with edit_col1:
                    new_name = st.text_input(
                        "器具名", value=item["name"], label_visibility="collapsed", key=f"name_{item['id']}"
                    )
                with edit_col2:
                    # カテゴリ変更用
                    cat_options = ["プレートロード", "マシンエリア", "フリーウエイト", "ファンクショナル", "カーディオエリア", "設備・その他"]
                    c_idx = cat_options.index(item["category"]) if item["category"] in cat_options else 0
                    new_cat = st.selectbox(
                        "カテゴリ", cat_options, index=c_idx, label_visibility="collapsed", key=f"cat_{item['id']}"
                    )
                with edit_col3:
                    # 削除ボタン
                    if st.button("🗑️", key=f"del_{item['id']}", help="この器具を削除します"):
                        supabase.table("gym_equipments").delete().eq("id", item["id"]).execute()
                        st.toast(f"🗑️ 「{item['name']}」を削除しました")
                        st.rerun()
                
                # もし名前やカテゴリが変更されていたら、自動（または裏側）で即時更新をかけられるようにフック
                if new_name != item["name"] or new_cat != item["category"]:
                    if new_name.strip():
                        supabase.table("gym_equipments").update({"name": new_name, "category": new_cat}).eq("id", item["id"]).execute()
                        st.toast(f"✏️ 「{new_name}」に更新しました")
                        # 連続タイピングを阻害しないよう、ここではあえて rerun() せずにトースト通知のみにします

        else:
            st.caption("ℹ️ 登録済みのジム器具はありません。")

    # AIに渡すプロンプト用プロセッシング（現在のラインナップを再集計）
    equip_dict = defaultdict(list)
    for item in raw_equipments:
        equip_dict[item["category"]].append(item["name"])

    # AIに渡すプロンプト用テキスト（タブ3の提案機能でのみ使用）
    user_profile_text = f"【ユーザー情報】年齢: {age}歳, 身長: {height}cm, 体重: {weight}kg, 筋肉量: {muscle_mass}kg, 体脂肪率: {fat_percentage}%, 目的: {purpose}, 活動量: {activity}"
    
    # --- 🛠️ セグメントコントロール（ボタン型UI） ---
    current_mode = st.radio(
        "メニューを選択してください",
        ["筋トレ記録", "食事記録", "🔮 次回の提案"],
        horizontal=True,
        key="app_mode_toggle"
    )

    # 画面上に現在の器具一覧をバッジ風・キャプション形式でコンパクトに常時表示
    if equip_dict:
        with st.container():
            st.markdown("<p style='font-size: 13px; font-weight: bold; margin-bottom: 5px;'>📍 現在のジム設備ラインナップ</p>", unsafe_allow_html=True)
            for cat, names in equip_dict.items():
                st.caption(f"**{cat}**: {', '.join(names)}")
    else:
        st.caption("ℹ️ 登録済みのジム器具はありません（上の登録メニューから追加できます）")

    st.markdown("---")

    # --- パターン1：筋トレ記録 ---
    if current_mode == "筋トレ記録":
        st.subheader("今日のトレーニング")
        w_date = st.date_input("日付", datetime.date.today(), key="w_date")
        part = st.selectbox("部位", ["胸", "背中", "脚", "肩", "腕", "腹筋"], key="workout_part")
        menu = st.text_input("種目名（例: ベンチプレス）", key="workout_menu")
        details = st.text_input("回数・セット（例: 80kg 10回 3セット）", key="workout_details")
        
        if st.button("筋トレを記録＆送信", key="workout_save_btn"):
            if menu and details:
                data = {"workout_date": str(w_date), "part": part, "menu_name": menu, "volume_details": details}
                supabase.table("workout_logs").insert(data).execute()
                st.success(f"💪 {menu} の記録をデータベースに保存しました！")
            else:
                st.warning("種目名と回数・セットを入力してください。")

    # --- パターン2：食事記録 ---
    elif current_mode == "食事記録":
        st.subheader("食事の記録")
        m_date = st.date_input("日付", datetime.date.today(), key="m_date")
        m_type = st.selectbox("タイミング", ["朝食", "昼食", "夕食", "間食"], key="meal_type")
        content = st.text_area("食べた内容（例: ササミ、玄米、プロテイン）", key="meal_content")
        
        if st.button("食事を記録して保存", key="meal_save_btn"):
            if content:
                try:
                    supabase.table("meal_logs").insert({"meal_date": str(m_date), "meal_type": m_type, "content": content}).execute()
                    st.success(f"🍳 {m_type} の食事内容をデータベースに保存しました！")
                except Exception as e:
                    st.error(f"❌ 接続エラー: {str(e)}")
            else:
                st.warning("食事内容を入力してください。")

    # --- パターン3：次回のメニュー提案 ---
    elif current_mode == "🔮 次回の提案":
        st.subheader("過去のデータと要望から次回のメニューを生成")
        
        user_request = st.text_area(
            "AIへの特別な要望（例: 「出張中なので自重のみ」「肩を痛めているので避けて」「時短15分で」など）",
            placeholder="特にない場合は空欄のままでOKです",
            key="ai_request"
        )
        
        if st.button("AIに次回のメニューを提案してもらう", key="ai_suggest_btn"):
            past_workouts = supabase.table("workout_logs").select("*").order("workout_date", desc=True).limit(14).execute()
            
            if past_workouts.data:
                history_text = "\n".join([f"・{r['workout_date']} [{r['part']}] {r['menu_name']}: {r['volume_details']}" for r in past_workouts.data])
            else:
                history_text = "過去の履歴はありません。新規の基本メニューを考えてください。"
                
            # 登録されたジム器具リストをテキスト化してプロンプトに内包
            gym_info = ""
            if equip_dict:
                gym_info = "\n".join([f"・{k}: {', '.join(v)}" for k, v in equip_dict.items()])
            else:
                gym_info = "一般的なジム器具（特定の指定なし）"
                
            prompt = f"【ユーザープロフィール】\n{user_profile_text}\n\n【利用可能なジムの器具・設備】\n{gym_info}\n\n【トレーニング履歴】\n{history_text}\n\n【個別要望】\n{user_request if user_request else '特になし'}\n\n【指示】\n1. ユーザーのプロフィールと過去の履歴を考慮し、個別要望がある場合はそれを最優先して、次回鍛えるべき最適なメニューを特定してください。\n2. 「利用可能なジムの器具・設備」に登録されている種目やマシンを最大限優先的に使用し、今回挑戦すべき具体的な種目、セット数、目標重量と回数を提案してください。"
            
            with st.spinner("過去のデータと要望、ジムの設備を分析してメニューを計算中..."):
                ai_res = ai_client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=prompt, 
                    config=genai.types.GenerateContentConfig(system_instruction="あなたは科学的根拠を重視し、ユーザーの状況に柔軟に寄り添うパーソナルトレーナーです。提供された『利用可能なジムの器具・設備』のリストにあるマシンや設備をベースに、具体的で実践しやすいメニューを作成してください。")
                )
            st.write(ai_res.text)
