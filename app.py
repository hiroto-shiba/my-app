import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from urllib.parse import urlparse, parse_qs

import zaim_client
import categorizer

st.set_page_config(page_title="家計管理アプリ", page_icon="💰", layout="wide")

# ─── OAuth コールバック処理 ────────────────────────────────────────────────
query_params = st.query_params
if "oauth_verifier" in query_params and "oauth_token" in query_params:
    verifier = query_params["oauth_verifier"]
    request_token = zaim_client.load_request_token()
    if request_token:
        try:
            with st.spinner("Zaimと連携中..."):
                zaim_client.fetch_access_token(
                    request_token["oauth_token"],
                    request_token["oauth_token_secret"],
                    verifier,
                )
            st.query_params.clear()
            st.success("Zaimとの連携が完了しました！")
        except Exception as e:
            st.error(f"Zaim連携に失敗しました: {e}")
            st.query_params.clear()
            st.stop()
    else:
        st.error("認証セッションが見つかりません。再度「Zaimで認証する」を押してください。")
        st.query_params.clear()
        st.stop()

# ─── 認証チェック ─────────────────────────────────────────────────────────
is_authenticated = zaim_client.load_tokens() is not None

st.title("💰 家計管理アプリ")

if not is_authenticated:
    st.warning("まずZaimと連携してください。")
    if st.button("Zaimで認証する"):
        with st.spinner("認証URLを準備中..."):
            auth_url = zaim_client.get_authorization_url()
        st.markdown(
            f'<a href="{auth_url}" target="_self" style="font-size:16px; font-weight:bold;">→ こちらをクリックしてZaimで認証する</a>',
            unsafe_allow_html=True,
        )
        st.info("上のリンクをクリックするとZaimの認証ページへ移動します。認証後、自動的にこのページへ戻ります。")
    st.stop()

# ─── サイドバー: 期間選択 ──────────────────────────────────────────────────
st.sidebar.header("期間設定")
today = date.today()
default_start = today.replace(day=1)
start_date = st.sidebar.date_input("開始日", value=default_start)
end_date = st.sidebar.date_input("終了日", value=today)

if st.sidebar.button("データ取得"):
    with st.spinner("Zaimからデータを取得中..."):
        records = zaim_client.fetch_money(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )
    st.session_state["records"] = records
    st.sidebar.success(f"{len(records)}件取得しました")

# ─── データ処理 ────────────────────────────────────────────────────────────
if "records" not in st.session_state or not st.session_state["records"]:
    st.info("サイドバーから期間を選択し「データ取得」を押してください。")
    st.stop()

records = st.session_state["records"]
df = pd.DataFrame(records)

# 型変換
df["date"] = pd.to_datetime(df["date"])
df["amount"] = df["amount"].astype(int)

# 収入・支出に分類 (mode: 1=支出, 2=収入, 3=振替)
df_expense = df[df["mode"] == 1].copy()
df_income = df[df["mode"] == 2].copy()

# カテゴリ分類 (Claude API)
if "category_map" not in st.session_state:
    st.session_state["category_map"] = {}

names_to_classify = [
    r for r in df_expense["name"].unique()
    if r not in st.session_state["category_map"]
]
if names_to_classify:
    with st.spinner(f"カテゴリを推定中 ({len(names_to_classify)}件)..."):
        cats = categorizer.classify_transactions(list(names_to_classify))
        for name, cat in zip(names_to_classify, cats):
            st.session_state["category_map"][name] = cat

df_expense["カテゴリ"] = df_expense["name"].map(st.session_state["category_map"]).fillna("その他")

# ─── タブ ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📅 日次", "📆 月次", "🏷️ カテゴリ", "💹 収入"])

# ── 日次タブ ──
with tab1:
    st.subheader("日次支出")
    daily = df_expense.groupby(df_expense["date"].dt.date)["amount"].sum().reset_index()
    daily.columns = ["日付", "支出合計"]
    fig = px.bar(daily, x="日付", y="支出合計", title="日次支出", labels={"支出合計": "円"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("明細")
    show = df_expense[["date", "name", "amount", "カテゴリ"]].copy()
    show.columns = ["日付", "取引名", "金額", "カテゴリ"]
    show = show.sort_values("日付", ascending=False)
    st.dataframe(show, use_container_width=True)

# ── 月次タブ ──
with tab2:
    st.subheader("月次支出")
    df_expense["月"] = df_expense["date"].dt.to_period("M").astype(str)
    monthly = df_expense.groupby("月")["amount"].sum().reset_index()
    monthly.columns = ["月", "支出合計"]
    fig2 = px.bar(monthly, x="月", y="支出合計", title="月次支出", labels={"支出合計": "円"})
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("期間合計支出", f"¥{df_expense['amount'].sum():,}")
    with col2:
        st.metric("期間合計収入", f"¥{df_income['amount'].sum():,}")

# ── カテゴリタブ ──
with tab3:
    st.subheader("カテゴリ別支出")
    cat_summary = df_expense.groupby("カテゴリ")["amount"].sum().reset_index()
    cat_summary.columns = ["カテゴリ", "合計金額"]
    cat_summary = cat_summary.sort_values("合計金額", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.pie(cat_summary, names="カテゴリ", values="合計金額", title="カテゴリ別支出割合")
        st.plotly_chart(fig3, use_container_width=True)
    with col2:
        fig4 = px.bar(cat_summary, x="合計金額", y="カテゴリ", orientation="h",
                      title="カテゴリ別支出金額", labels={"合計金額": "円"})
        st.plotly_chart(fig4, use_container_width=True)

    st.subheader("カテゴリ別明細")
    selected_cat = st.selectbox("カテゴリを選択", cat_summary["カテゴリ"].tolist())
    detail = df_expense[df_expense["カテゴリ"] == selected_cat][["date", "name", "amount"]]
    detail.columns = ["日付", "取引名", "金額"]
    st.dataframe(detail.sort_values("日付", ascending=False), use_container_width=True)

# ── 収入タブ ──
with tab4:
    st.subheader("収入明細")
    if df_income.empty:
        st.info("期間内に収入データがありません。")
    else:
        show_income = df_income[["date", "name", "amount"]].copy()
        show_income.columns = ["日付", "取引名", "金額"]
        show_income = show_income.sort_values("日付", ascending=False)
        st.metric("期間合計収入", f"¥{df_income['amount'].sum():,}")
        st.dataframe(show_income, use_container_width=True)
