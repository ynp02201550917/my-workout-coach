import streamlit as st
from supabase import create_client, Client
from google import genai
import datetime
import time
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

# 💡 ログイン成功時のみ、以下のすべての処理を実行する
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
    
    # --- Supabaseから最新のユーザープロフィールを取得 ---
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
            time.sleep(1.0)
            st.rerun()

    # 先にデータベースから最新の器具リストを裏側で取得
    try:
        eq_res = supabase.table("gym_equipments").select("*").order("category").execute()
        raw_equipments = eq_res.data if eq_res.data else []
    except Exception as e:
        st.error(f"器具データの取得失敗: {e}")
        raw_equipments = []

    # AIプロンプト用の集計
    equip_dict = defaultdict(list)
    for item in raw_equipments:
        part_info = f" ({item['target_part']})" if item.get("target_part") else " (指定なし)"
        equip_dict[item["category"]].append(f"{item['name']}{part_info}")

    # --- ジム器具の管理エリア（アコーディオン） ---
    with st.expander("🏋️‍♂️ ジムの導入器具・設備登録＆編集", expanded=False):
        st.subheader("🆕 新しい器具の登録")
        eq_category = st.selectbox(
            "エリア・カテゴリ",
            ["プレートロード", "マシンエリア", "フリーウエイト", "ファンクショナル", "カーディオエリア", "設備・その他"],
            key="eq_cat_select"
        )
        eq_name = st.text_input("器具・設備名（例: コンバージング・チェストプレス）", key="eq_name_input")
        eq_target_part = st.selectbox(
            "対象部位（Nullにする場合は『指定なし』）",
            ["指定なし", "胸", "背中", "脚", "肩", "腕", "腹筋"],
            key="eq_part_select"
        )
        
        if st.button("ジムの器具を登録する", key="eq_save_btn"):
            if eq_name:
                try:
                    db_part = None if eq_target_part == "指定なし" else eq_target_part
                    supabase.table("gym_equipments").insert({
                        "category": eq_category, 
                        "name": eq_name,
                        "target_part": db_part
                    }).execute()
                    st.success(f"✅ 【{eq_category}】に「{eq_name}（部位: {eq_target_part}）」を追加しました！")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")
            else:
                st.warning("器具・設備名を入力してください。")
        
        st.markdown("---")
        st.subheader("🛠️ 登録済み器具の管理（編集・削除）")
        if raw_equipments:
            for item in raw_equipments:
                edit_col1, edit_col2, edit_col3, edit_col4 = st.columns([2, 2, 2, 1])
                with edit_col1:
                    new_name = st.text_input(
                        "器具名", value=item["name"], label_visibility="collapsed", key=f"name_{item['id']}"
                    )
                with edit_col2:
                    cat_options = ["プレートロード", "マシンエリア", "フリーウエイト", "ファンクショナル", "カーディオエリア", "設備・その他"]
                    c_idx = cat_options.index(item["category"]) if item["category"] in cat_options else 0
                    new_cat = st.selectbox(
                        "カテゴリ", cat_options, index=c_idx, label_visibility="collapsed", key=f"cat_{item['id']}"
                    )
                with edit_col3:
                    part_options = ["指定なし", "胸", "背中", "脚", "肩", "腕", "腹筋"]
                    current_part = item.get("target_part") if item.get("target_part") else "指定なし"
                    p_idx = part_options.index(current_part) if current_part in part_options else 0
                    new_part = st.selectbox(
                        "部位", part_options, index=p_idx, label_visibility="collapsed", key=f"part_{item['id']}"
                    )
                with edit_col4:
                    if st.button("🗑️", key=f"del_{item['id']}", help="この器具を削除します"):
                        supabase.table("gym_equipments").delete().eq("id", item["id"]).execute()
                        st.toast(f"🗑️ 「{item['name']}」を削除しました")
                        time.sleep(0.5)
                        st.rerun()
                
                db_new_part = None if new_part == "指定なし" else new_part
                if new_name != item["name"] or new_cat != item["category"] or db_new_part != item.get("target_part"):
                    if new_name.strip():
                        supabase.table("gym_equipments").update({
                            "name": new_name, 
                            "category": new_cat,
                            "target_part": db_new_part
                        }).eq("id", item["id"]).execute()
                        st.toast(f"✏️ 「{new_name}」の設定を更新しました")
        else:
            st.caption("ℹ️ 登録済みのジム器具はありません。")

    # ✨ NEW: --- AI提案の前提条件 管理エリア（アコーディオン） ---
    try:
        cond_res = supabase.table("ai_conditions").select("*").order("created_at").execute()
        raw_conditions = cond_res.data if cond_res.data else []
    except Exception as e:
        st.error(f"前提条件データの取得失敗: {e}")
        raw_conditions = []

    with st.expander("🔮 AI提案の前提条件（プロンプト設定）", expanded=False):
        st.subheader("🆕 前提条件の追加")
        new_cond_text = st.text_input("メニュー生成時にAIに必ず守らせたい条件（例: 有酸素運動はなし）", key="new_cond_input")
        if st.button("条件を追加する", key="cond_save_btn"):
            if new_cond_text.strip():
                try:
                    supabase.table("ai_conditions").insert({"content": new_cond_text.strip()}).execute()
                    st.success(f"✅ 条件「{new_cond_text}」を追加しました！")
                    time.sleep(1.0)
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")
            else:
                st.warning("条件を入力してください。")
        
        st.markdown("---")
        st.subheader("🛠️ 登録済みの前提条件一覧")
        if raw_conditions:
            for cond in raw_conditions:
                c_col1, c_col2 = st.columns([5, 1])
                with c_col1:
                    edited_cond = st.text_input(
                        "条件内容", value=cond["content"], label_visibility="collapsed", key=f"cond_text_{cond['id']}"
                    )
                with c_col2:
                    if st.button("🗑️", key=f"cond_del_{cond['id']}", help="この条件を削除します"):
                        supabase.table("ai_conditions").delete().eq("id", cond["id"]).execute()
                        st.toast("🗑️ 条件を削除しました")
                        time.sleep(0.5)
                        st.rerun()
                
                if edited_cond != cond["content"] and edited_cond.strip():
                    supabase.table("ai_conditions").update({"content": edited_cond.strip()}).eq("id", cond["id"]).execute()
                    st.toast("✏️ 条件を更新しました")
        else:
            st.caption("ℹ️ 登録されている固定の前提条件はありません。")

    # ユーザープロフィールテキストの構築
    user_profile_text = f"【ユーザー情報】年齢: {age}歳, 身長: {height}cm, 体重: {weight}kg, 筋肉量: {muscle_mass}kg, 体脂肪率: {fat_percentage}%, 目的: {purpose}, 活動量: {activity}"

    # --- セグメントコントロール（ボタン型UI） ---
    current_mode = st.radio(
        "メニューを選択してください",
        ["筋トレ記録", "食事記録", "🔮 次回の提案"],
        horizontal=True,
        key="app_mode_toggle"
    )

    st.markdown("---")

    # --- パターン1：筋トレ記録 ---
    if current_mode == "筋トレ記録":
        st.subheader("今日のトレーニング")
        w_date = st.date_input("日付", datetime.date.today(), key="w_date")
        part = st.selectbox("部位", ["胸", "背中", "脚", "肩", "腕", "腹筋"], key="workout_part")
        
        menu_input_type = st.radio(
            "種目名の入力形式",
            ["登録器具から選択", "自由に入力（自宅トレなど）"],
            horizontal=True,
            key="menu_input_type"
        )
        
        menu = ""
        last_details_value = "" 
        current_placeholder = "例: 80kg 10回 3セット" 
        
        if menu_input_type == "登録器具から選択":
            if raw_equipments:
                filtered_items = [
                    item for item in raw_equipments 
                    if item.get("target_part") == part or item.get("target_part") is None or item.get("target_part") == ""
                ]
                filtered_items.sort(key=lambda x: (x.get("target_part") != part, x["name"]))
                filtered_equipments = [item["name"] for item in filtered_items]
                
                if filtered_equipments:
                    menu = st.selectbox(f"種目名（{part}の対象器具・共通器具）", filtered_equipments, key="workout_menu_select")
                    
                    if menu:
                        try:
                            past_log_res = (
                                supabase.table("workout_logs")
                                .select("volume_details")
                                .eq("menu_name", menu)
                                .order("workout_date", desc=True)
                                .limit(1)
                                .execute()
                            )
                            if past_log_res.data and past_log_res.data[0]["volume_details"]:
                                last_details_value = past_log_res.data[0]["volume_details"]
                                current_placeholder = f"前回値: {last_details_value}"
                            else:
                                last_details_value = ""
                                current_placeholder = "例: 10回 3セット"
                        except Exception:
                            pass
                else:
                    st.info(f"ℹ️ {part}に対応する器具が登録されていません。全器具から選択します。")
                    all_names = [item["name"] for item in raw_equipments]
                    all_names.sort()
                    menu = st.selectbox("種目名（すべての器具）", all_names, key="workout_menu_select_fallback")
            else:
                st.info("ℹ️ 登録されている器具がありません。「自由に入力」するか上のメニューから器具を登録してください。")
        else:
            menu = st.text_input("種目名（例: 自重プッシュアップ）", key="workout_menu_text")
            last_details_value = ""
            current_placeholder = "例: 10回 3セット"

        label_suffix = f" (前回値: {last_details_value})" if last_details_value else " (前回値データなし)"
        
        details = st.text_input(
            f"回数・セット{label_suffix}",
            value=last_details_value,
            placeholder=current_placeholder,
            key="workout_details"
        )
        
        if st.button("筋トレを記録＆送信", key="workout_save_btn"):
            if menu and details:
                data = {"workout_date": str(w_date), "part": part, "menu_name": menu, "volume_details": details}
                try:
                    supabase.table("workout_logs").insert(data).execute()
                    st.success(f"✅ 送信完了！ 【{menu}】の記録を保存しました。")
                    time.sleep(1.5)
                    st.rerun() 
                except Exception as e:
                    st.error(f"❌ 送信失敗（エラー: {e}）")
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
                    st.success(f"🍳 保存完了！ {m_type} の食事内容を記録しました。")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 接続エラー: {str(e)}")
            else:
                st.warning("食事内容を入力してください。")

    # --- パターン3：次回のメニュー提案 ---
    elif current_mode == "🔮 次回の提案":
        st.subheader("🔮 過去のデータからAI提案")
        
        tab_gym, tab_meal = st.tabs(["🏋️‍♂️ 次回のジムメニュー", "🥗 次回の食事メニュー"])
        
        # --- タブ1：ジムメニュー提案 ---
        with tab_gym:
            st.caption("登録されているジム設備、過去の筋トレ履歴、および【管理エリアで設定した前提条件】からメニューを算出します。")
            gym_request = st.text_area(
                "ジムメニューへのその日の個別要望（例: 「今日は寝不足なので軽めで」「時短15分で」など）",
                placeholder="特にない場合は空欄のままでOKです",
                key="ai_gym_request"
            )
            if st.button("AIにジムメニューを提案してもらう", key="ai_gym_suggest_btn"):
                past_workouts = supabase.table("workout_logs").select("*").order("workout_date", desc=True).limit(14).execute()
                if past_workouts.data:
                    history_text = "\n".join([f"・{r['workout_date']} [{r['part']}] {r['menu_name']}: {r['volume_details']}" for r in past_workouts.data])
                else:
                    history_text = "過去の履歴はありません。新規の基本メニューを考えてください。"
                    
                gym_info = ""
                if equip_dict:
                    gym_info = "\n".join([f"・{k}: {', '.join(v)}" for k, v in equip_dict.items()])
                else:
                    gym_info = "一般的なジム器具（特定の指定なし）"
                
                # 💡 登録された固定の前提条件をテキスト化してプロンプトに注入する
                fixed_conditions_text = ""
                if raw_conditions:
                    fixed_conditions_text = "\n".join([f"・{c['content']}" for c in raw_conditions])
                else:
                    fixed_conditions_text = "特になし"
                    
                prompt = f"【ユーザープロフィール】\n{user_profile_text}\n\n【利用可能なジムの器具・設備（カッコ内は対象部位）】\n{gym_info}\n\n【必ず守るべき必須の前提条件】\n{fixed_conditions_text}\n\n【トレーニング履歴】\n{history_text}\n\n【当日の個別要望】\n{gym_request if gym_request else '特になし'}\n\n【指示】\n1. ユーザーのプロフィールと過去の履歴を考慮し、「必ず守るべき必須の前提条件」および「当日の個別要望」を絶対に厳守して、次回鍛えるべき最適なメニューを特定してください。\n2. 「利用可能なジムの器具・設備」に登録されている種目やマシンを最大限優先的に使用し、今回挑戦すべき具体的な種目、セット数、目標重量と回数を提案してください。"
                
                with st.spinner("トレーニング履歴とジム設備・前提条件を分析中..."):
                    ai_res = ai_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(system_instruction="あなたは科学的根拠を重視し、ユーザーの状況に柔軟に寄り添うパーソナルトレーナーです。提供された『利用可能なジムの器具・設備』のリストにあるマシンや設備をベースに、『必ず守るべき必須の前提条件』を満たした具体的で実践しやすいメニューを作成してください。")
                    )
                    st.session_state.gym_advice = ai_res.text

            if "gym_advice" in st.session_state:
                st.markdown("---")
                st.markdown("### 🏋️‍♂️ おすすめの次回のメニュー")
                st.write(st.session_state.gym_advice)

        # --- タブ2：食事メニュー提案 ---
        with tab_meal:
            st.caption("ユーザーの目的や直近の食事内容から、おすすめのPFCバランスや具体的なメニューを提案します。")
            meal_request = st.text_area(
                "食事メニューへの個別要望（例: 「コンビニで買えるもの」「高タンパク・低糖質で」「自炊で簡単に作れるもの」など）",
                placeholder="特にない場合は空欄のままでOKです",
                key="ai_meal_request"
            )
            if st.button("AIに食事メニューを提案してもらう", key="ai_meal_suggest_btn"):
                past_meals = supabase.table("meal_logs").select("*").order("meal_date", desc=True).limit(10).execute()
                if past_meals.data:
                    meal_history_text = "\n".join([f"・{r['meal_date']} [{r['meal_type']}] {r['content']}" for r in past_meals.data])
                else:
                    meal_history_text = "直近の食事履歴はありません。"
                    
                prompt = f"【ユーザープロフィール】\n{user_profile_text}\n\n【直近の食事履歴】\n{meal_history_text}\n\n【個別要望】\n{meal_request if meal_request else '特になし'}\n\n【指示】\n1. ユーザーの年齢・体重・筋肉量・活動量、およびトレーニングの目的（引き締め、バルクアップ等）を元に、次回の食事で意識すべきカロリーやPFC（タンパク質・脂質・炭水化物）バランスの方向性を提示してください。\n2. 直近の食事内容で不足していそうな栄養素（例：タンパク質不足、野菜不足など）があれば優しく指摘し、個別要望に沿った具体的な食事メニュー例（朝・昼・晩・間食のいずれか、または全体）を提案してください。"
                
                with st.spinner("食事履歴とプロフィールから最適な栄養バランスを計算中..."):
                    ai_res = ai_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(system_instruction="あなたは栄養学の知識が豊富で、ユーザーの日々の生活に寄り添う優秀なスポーツ栄養士・管理栄養士です。堅苦しくなく、明日からすぐに真似できる具体的で美味しい食事アドバイスを提供してください。")
                    )
                    st.session_state.meal_advice = ai_res.text

            if "meal_advice" in st.session_state:
                st.markdown("---")
                st.markdown("### 🥗 おすすめの食事メニュー・アドバイス")
                st.write(st.session_state.meal_advice)
