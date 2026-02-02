# ============================================================
# WordPress 404 Intelligence Dashboard
# Author: Soham Aggarwal
# Purpose: Identify bot-driven 404s and actionable redirect candidates
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from urllib.parse import urlparse
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

RAW_FILE = "raw_404_logs.csv"
REPORT_FILE = "404_analysis_report.csv"

BOT_THRESHOLD_URLS = 5
BOT_THRESHOLD_PHP = 3

st.set_page_config(
    page_title="404 Traffic Intelligence",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def safe_read_csv(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        if df.empty:
            raise ValueError("CSV loaded but is empty")
        return df
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return pd.DataFrame()

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.path.rstrip("/")
    except Exception:
        return str(url)

def is_php_attack(url: str) -> bool:
    return bool(re.search(r"\.php|wp-admin|wp-includes|\.env|\.git", str(url), re.I))

def classify_user_agent(ua: str) -> str:
    if pd.isna(ua):
        return "unknown"

    ua = ua.lower()
    if "googlebot" in ua or "google" in ua:
        return "google"
    if "bingbot" in ua or "bing" in ua:
        return "bing"
    if "amazonbot" in ua:
        return "amazon"
    if "chatgpt" in ua or "openai" in ua:
        return "openai"
    if "bot" in ua or "crawler" in ua or "spider" in ua:
        return "other-bot"
    return "human"

def parse_date_safe(date_str: str):
    try:
        return pd.to_datetime(date_str)
    except Exception:
        return pd.NaT

# ============================================================
# DATA LOADING
# ============================================================

raw_df = safe_read_csv(RAW_FILE)

if raw_df.empty:
    st.stop()

# ============================================================
# DATA ENRICHMENT
# ============================================================

raw_df["date_parsed"] = raw_df["date"].apply(parse_date_safe)
raw_df["normalized_url"] = raw_df["source_url"].apply(normalize_url)
raw_df["is_php_attack"] = raw_df["normalized_url"].apply(is_php_attack)
raw_df["ua_class"] = raw_df["user_agent"].apply(classify_user_agent)

# ============================================================
# IP-LEVEL AGGREGATION
# ============================================================

ip_stats = (
    raw_df
    .groupby("ip")
    .agg(
        total_hits=("source_url", "count"),
        unique_urls=("normalized_url", "nunique"),
        php_attempts=("is_php_attack", "sum"),
        first_seen=("date_parsed", "min"),
        last_seen=("date_parsed", "max")
    )
    .reset_index()
)

ip_stats["suspected_bot"] = (
    (ip_stats["unique_urls"] >= BOT_THRESHOLD_URLS) |
    (ip_stats["php_attempts"] >= BOT_THRESHOLD_PHP)
)

# ============================================================
# SIDEBAR CONTROLS
# ============================================================

st.sidebar.title("🛠 Controls")

include_bots = st.sidebar.checkbox("Include suspected bots", value=True)
min_hits = st.sidebar.slider("Minimum hits", 1, 100, 1)
min_unique_urls = st.sidebar.slider("Minimum unique URLs", 1, 50, 1)

search_url = st.sidebar.text_input("Filter URL contains")
search_ip = st.sidebar.text_input("Filter IP contains")
ua_filter = st.sidebar.multiselect(
    "User-Agent Type",
    ["human", "google", "bing", "amazon", "openai", "other-bot"],
    default=["human", "google", "bing", "amazon", "openai", "other-bot"]
)

# ============================================================
# HEADER
# ============================================================

st.title("🚦 WordPress 404 Traffic Intelligence")
st.caption("Raw truth → signal extraction → redirect decisions")

# ============================================================
# KPI ROW
# ============================================================

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total 404s", len(raw_df))
k2.metric("Unique IPs", raw_df["ip"].nunique())
k3.metric("Suspected Bots", int(ip_stats["suspected_bot"].sum()))
k4.metric("Unique URLs", raw_df["normalized_url"].nunique())

st.divider()

# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "🧾 Raw Log",
    "🔗 URL Intelligence",
    "🌐 IP Intelligence",
    "🤖 Bot Analysis",
    "✅ Redirect Candidates",
    "📈 Trends"
])

# ============================================================
# TAB 1 — RAW LOG
# ============================================================

with tabs[0]:
    st.subheader("Full Raw 404 Log")

    raw_view = raw_df.copy()

    if not include_bots:
        raw_view = raw_view[~raw_view["ip"].isin(
            ip_stats[ip_stats["suspected_bot"]]["ip"]
        )]

    raw_view = raw_view[raw_view["ua_class"].isin(ua_filter)]

    if search_url:
        raw_view = raw_view[raw_view["source_url"].str.contains(search_url, case=False)]

    if search_ip:
        raw_view = raw_view[raw_view["ip"].str.contains(search_ip)]

    st.dataframe(
        raw_view.sort_values("date_parsed", ascending=False),
        use_container_width=True,
        height=550
    )

# ============================================================
# TAB 2 — URL INTELLIGENCE
# ============================================================

with tabs[1]:
    st.subheader("Broken URLs — Impact View")

    url_stats = (
        raw_df
        .groupby("normalized_url")
        .agg(
            hits=("normalized_url", "count"),
            unique_ips=("ip", "nunique"),
            bot_hits=("is_php_attack", "sum")
        )
        .reset_index()
        .sort_values("hits", ascending=False)
    )

    url_stats = url_stats[url_stats["hits"] >= min_hits]

    fig = px.bar(
        url_stats.head(30),
        x="normalized_url",
        y="hits",
        title="Top Broken URLs by Volume"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(url_stats, use_container_width=True)

# ============================================================
# TAB 3 — IP INTELLIGENCE
# ============================================================

with tabs[2]:
    st.subheader("IP Behavior Analysis")

    ip_view = ip_stats.copy()

    ip_view = ip_view[ip_view["unique_urls"] >= min_unique_urls]

    fig = px.scatter(
        ip_view,
        x="unique_urls",
        y="total_hits",
        color="suspected_bot",
        hover_data=["ip", "php_attempts"],
        title="IP Behavior: Spread vs Volume"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ip_view, use_container_width=True)

# ============================================================
# TAB 4 — BOT ANALYSIS
# ============================================================

with tabs[3]:
    st.subheader("Bot & Attack Traffic")

    bot_df = raw_df[raw_df["is_php_attack"] | raw_df["ua_class"].str.contains("bot")]

    ua_counts = bot_df["ua_class"].value_counts().reset_index()
    ua_counts.columns = ["ua_class", "count"]

    fig = px.pie(
        ua_counts,
        names="ua_class",
        values="count",
        hole=0.45,
        title="Bot Traffic Breakdown"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(bot_df.sort_values("date_parsed", ascending=False),
                 use_container_width=True)

# ============================================================
# TAB 5 — REDIRECT CANDIDATES
# ============================================================

with tabs[4]:
    st.subheader("Likely Human Redirect Candidates")

    human_ips = ip_stats[~ip_stats["suspected_bot"]]["ip"]
    human_hits = raw_df[raw_df["ip"].isin(human_ips)]

    candidates = (
        human_hits
        .groupby("normalized_url")
        .agg(
            hits=("normalized_url", "count"),
            unique_ips=("ip", "nunique")
        )
        .reset_index()
        .sort_values("hits", ascending=False)
    )

    st.success("These URLs are most likely worth redirecting.")

    st.dataframe(candidates.head(100), use_container_width=True)

# ============================================================
# TAB 6 — TIME TRENDS
# ============================================================

with tabs[5]:
    st.subheader("404 Trends Over Time")

    trend = (
        raw_df
        .dropna(subset=["date_parsed"])
        .set_index("date_parsed")
        .resample("H")
        .size()
        .reset_index(name="count")
    )

    fig = px.line(
        trend,
        x="date_parsed",
        y="count",
        title="404 Requests Over Time"
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Guidance: Do not redirect URLs driven by bots or attack traffic. "
    "Redirect only high-frequency, human-driven URLs."
)
