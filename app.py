import streamlit as st
import datetime
from supabase import create_client, Client

# ==============================================================================
# 1. 初期設定 & データベース接続
# ==============================================================================
st.set_page_config(page_title="Gym Workout Logger", layout="centered")

# Secrets から接続情報を取得（ローカル実行時は .streamlit/secrets.toml を参照）
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==============================================================================
# 2. マスターデータの読み込み（マスタキャッシュ）
# ==============================================================================
# アプリの動作を軽くするため、器具マスターはページ更新ごとに1回だけ取得します
try:
    res = supabase.table("gym_equipments").select("*").order("name").execute()
    raw_equipments = res.data
except Exception as e:
    st.error(f"データベース接続エラー: {e}")
    raw_equipments = []

# ==============================================================================
# 3. アプリケーションヘッダー & モード切り替え
# ==============================================================================
st.title("🏋️‍♂️ Gym Workout Logger")

current_mode = st.radio(
    "メニューを選択",
    ["筋トレ記録", "器具・設備の管理"],
    horizontal=True,
    key="main_mode"
)

st.markdown("---")

# ==============================================================================
# 4. モードA: 筋トレ記録
# ==============================================================================
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
    
    # --- パターン1: 登録器具から選択 ---
    if menu_input_type == "登録器具から選択":
        if raw_equipments:
            # 🔍 フィルタリング条件:
            # 1. 選択した部位と一致する
            # 2. もしくは target_part が Null (None) や 空文字 の器具は「すべて」に含める
            filtered_equipments = [
                item["name"] for item in raw_equipments 
                if item.get("target_part") == part or item.get("target_part") is None or item.get("target_part") == ""
            ]
            
            # 安全対策: 該当器具が1個もない場合は全器具を表示
            if not filtered_equipments:
                filtered_equipments = [item["name"] for item in raw_equipments]
                st.caption("⚠️ 条件に合う器具がないため、すべての器具を表示しています。")
            
            menu = st.selectbox(f"種目名（{part}の登録器具）", filtered_equipments, key="workout_menu_select")
            
            # 選択した器具の「前回の記録」を自動取得するロジック
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
                except Exception:
                    pass
        else:
            st.info("ℹ️ 登録されている器具がありません。「器具・設備の管理」タブから登録してください。")
            
    # --- パターン2: 自由入力 ---
    else:
        menu = st.text_input("種目名を手入力（例: ダンベルベンチプレス）", key="workout_menu_text")

    # ボリューム詳細とメモの入力
    volume_details = st.text_input(
        "内容（重量・回数・セット数）", 
        value=last_details_value, 
        placeholder=current_placeholder,
        key="workout_details"
    )
    memo = st.text_area("メモ・調子など（任意）", key="workout_memo")
    
    # 記録の保存処理
    if st.button("トレーニングを記録する", type="primary"):
        if not menu:
            st.error("❌ 種目名を入力または選択してください。")
        elif not volume_details:
            st.error("❌ 内容（重量や回数など）を入力してください。")
        else:
            try:
                supabase.table("workout_logs").insert({
                    "workout_date": str(w_date),
                    "target_part": part,
                    "menu_name": menu,
                    "volume_details": volume_details,
                    "memo": memo
                }).execute()
                st.success(f"💪 {w_date} の【{part}・{menu}】の記録を保存しました！")
                # 入力後の値のクリアと再描画
                st.rerun()
            except Exception as e:
                st.error(f"❌ 記録の保存に失敗しました: {e}")

# ==============================================================================
# 5. モードB: 器具・設備の管理
# ==============================================================================
else:
    st.subheader("🛠️ ジム器具・マシンの管理")
    
    # タブで「登録」と「一覧確認」を分ける
    manage_tab1, manage_tab2 = st.tabs(["🆕 新しい器具の登録", "📋 登録済み器具の一覧"])
    
    # --- タブ1: 器具の新規追加 ---
    with manage_tab1:
        eq_category = st.selectbox(
            "エリア・カテゴリ", 
            ["プレートロード", "マシンエリア", "フリーウエイト", "ファンクショナル", "カーディオエリア", "設備・その他"],
            key="reg_cat"
        )
        eq_name = st.text_input("器具・設備名（例: コンバージング・チェストプレス）", key="reg_name")
        
        # 部位の選択肢（「その他」を選べばNullの挙動を確認しやすくなります）
        eq_target_part = st.selectbox(
            "対象部位（Nullにしたい場合は『指定なし』を選択）", 
            ["胸", "背中", "脚", "肩", "腕", "腹筋", "指定なし"], 
            key="reg_part"
        )
        
        if st.button("ジムの器具を登録する"):
            if not eq_name:
                st.error("❌ 器具名を入力してください。")
            else:
                try:
                    # 「指定なし」が選ばれた場合は、データベース上は None (Null) として保存する
                    db_part = None if eq_target_part == "指定なし" else eq_target_part
                    
                    supabase.table("gym_equipments").insert({
                        "category": eq_category, 
                        "name": eq_name,
                        "target_part": db_part
                    }).execute()
                    st.success(f"✅ 【{eq_category}】に「{eq_name}（部位: {eq_target_part}）」を追加しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 登録エラー: {e}")
                    
    # --- タブ2: 登録済み器具の表示 ---
    with manage_tab2:
        if raw_equipments:
            # テーブル形式で見やすく加工して表示
            display_data = []
            for item in raw_equipments:
                display_data.append({
                    "器具・設備名": item.get("name"),
                    "カテゴリ": item.get("category"),
                    "鍛えられる部位": item.get("target_part") if item.get("target_part") else "共通 / 未設定 (Null)"
                })
            st.dataframe(display_data, use_container_width=True)
        else:
            st.info("ℹ️ まだ器具が登録されていません。")
