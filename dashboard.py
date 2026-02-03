
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from urllib.parse import urlparse

st.set_page_config(
    page_title="404 Traffic Intelligence",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# GLOBAL STYLES
# ============================================================

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
h1, h2, h3 {
    font-weight: 600;
}
.stDataFrame {
    border-radius: 12px;
}
.info {
    color: #6c757d;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPERS
# ============================================================

def info(text):
    st.markdown(f"<div class='info'>ℹ️ {text}</div>", unsafe_allow_html=True)

def normalize_url(url):
    try:
        return urlparse(url).path.rstrip("/")
    except:
        return str(url)

def is_attack(url):
    return bool(re.search(r"\.php|wp-admin|wp-includes|\.env|\.git", str(url), re.I))

def classify_ua(ua):
    if pd.isna(ua):
        return "unknown"
    ua = ua.lower()
    if "googlebot" in ua or "google" in ua:
        return "google"
    if "bingbot" in ua:
        return "bing"
    if "bot" in ua or "crawler" in ua or "spider" in ua:
        return "bot"
    if "python" in ua or "httpx" in ua:
        return "script"
    return "human"

# ============================================================
# LOAD DATA
# ============================================================

RAW_FILE = "raw_404_logs.csv"
df = pd.read_csv(RAW_FILE)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["normalized_url"] = df["source_url"].apply(normalize_url)
df["is_attack"] = df["normalized_url"].apply(is_attack)
df["ua_class"] = df["user_agent"].apply(classify_ua)

# ============================================================
# AGGREGATIONS
# ============================================================

ip_stats = (
    df.groupby("ip")
    .agg(
        total_hits=("source_url", "count"),
        unique_urls=("normalized_url", "nunique"),
        attack_hits=("is_attack", "sum")
    )
    .reset_index()
)

ip_stats["suspected_bot"] = (
    (ip_stats["unique_urls"] >= 5) |
    (ip_stats["attack_hits"] >= 3)
)

url_stats = (
    df.groupby("normalized_url")
    .agg(
        hits=("normalized_url", "count"),
        unique_ips=("ip", "nunique"),
        attack_hits=("is_attack", "sum")
    )
    .reset_index()
    .sort_values("hits", ascending=False)
)

# ============================================================
# EXPORT DATASETS (VERIFIED)
# ============================================================

# 1. Full raw dataset
raw_export = df.copy()

# 2. Suspected bots + attacks ONLY
suspected_bot_ips = set(ip_stats[ip_stats["suspected_bot"]]["ip"])

bot_export = df[
    (df["is_attack"]) |
    (df["ip"].isin(suspected_bot_ips))
].copy()

# 3. URL intelligence summary
url_export = url_stats.copy()

# ============================================================
# SIDEBAR — DOWNLOADS ONLY (CLEAN)
# ============================================================

st.sidebar.markdown("## ⬇️ Downloads")
st.sidebar.caption("Clear, purpose-specific CSV exports")

st.sidebar.download_button(
    "📄 Full Raw 404 Data",
    raw_export.to_csv(index=False),
    "404_raw_full.csv",
    "text/csv",
    help="Every logged 404 request with enrichment columns."
)

st.sidebar.download_button(
    "🤖 Suspected Bots & Attacks",
    bot_export.to_csv(index=False),
    "404_suspected_bots.csv",
    "text/csv",
    help="Only traffic flagged as bots, scanners, or exploit attempts."
)

st.sidebar.download_button(
    "🔗 URL Intelligence Summary",
    url_export.to_csv(index=False),
    "404_url_intelligence.csv",
    "text/csv",
    help="One row per missing URL with hit counts and unique IPs."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Interpretation Guide")
st.sidebar.markdown("""
- **Human traffic** → UX / SEO impact  
- **Bot traffic** → Ignore or block  
- **Exploit paths** → Security noise  
""")

# ============================================================
# HEADER
# ============================================================

st.title("🚦 404 Traffic Intelligence Dashboard")
info(
    "I use this dashboard to separate real user errors from bot noise and attack traffic, "
    "and to decide what should be fixed, redirected, ignored, or blocked."
)

# ============================================================
# KPI ROW
# ============================================================

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total 404 Requests", len(df))
k2.metric("Unique Missing URLs", df["normalized_url"].nunique())
k3.metric("Unique IPs", df["ip"].nunique())
k4.metric("Attack Attempts", df["is_attack"].sum())
k5.metric("Suspected Bots", len(suspected_bot_ips))

info("These KPIs summarize scale, impact, and how much traffic is non-human.")

st.divider()

# ============================================================
# TABS
# ============================================================

tab_overview, tab_urls, tab_ips = st.tabs([
    "📊 Overview",
    "🔗 URL Analysis",
    "🌐 IP & Bot Analysis"
])

# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab_overview:
    st.subheader("Traffic Composition")
    info("Breakdown of who is generating 404 traffic based on user-agent classification.")

    ua_breakdown = df["ua_class"].value_counts().reset_index()
    ua_breakdown.columns = ["Type", "Requests"]

    fig = px.bar(ua_breakdown, x="Type", y="Requests", color="Type")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("404 Requests Over Time")
    info("Spikes often align with crawls, deployments, or automated scans.")

    trend = (
        df.dropna(subset=["date"])
        .set_index("date")
        .resample("H")
        .size()
        .reset_index(name="Requests")
    )

    fig = px.line(trend, x="date", y="Requests")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 Full Raw 404 Log"):
        info("Every recorded 404 request, unfiltered.")
        st.dataframe(
            df.sort_values("date", ascending=False),
            use_container_width=True,
            height=500
        )

# ============================================================
# TAB 2 — URL ANALYSIS
# ============================================================

with tab_urls:
    st.subheader("Missing URLs (Ranked)")
    info("URLs repeatedly requested by users are strong redirect or fix candidates.")

    fig = px.bar(
        url_stats.head(25),
        x="normalized_url",
        y="hits"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("All Missing URLs")
    info("Complete URL-level summary.")

    st.dataframe(
        url_stats,
        use_container_width=True,
        height=550
    )

# ============================================================
# TAB 3 — IP & BOT ANALYSIS
# ============================================================

with tab_ips:
    st.subheader("IP Behavior Patterns")
    info("IPs hitting many URLs or exploit paths are likely bots or scanners.")

    fig = px.scatter(
        ip_stats,
        x="unique_urls",
        y="total_hits",
        color="suspected_bot",
        hover_data=["ip", "attack_hits"]
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("All IPs")
    info("Aggregated request behavior per IP address.")

    st.dataframe(
        ip_stats.sort_values("total_hits", ascending=False),
        use_container_width=True,
        height=500
    )

    with st.expander("🚨 Attack & Exploit Attempts"):
        info("Requests targeting common exploit paths. Never redirect these.")
        st.dataframe(
            df[df["is_attack"]]
            .sort_values("date", ascending=False),
            use_container_width=True,
            height=400
        )

# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Rule of thumb: Redirect human-driven URLs. Ignore or block bot and attack traffic."
)
