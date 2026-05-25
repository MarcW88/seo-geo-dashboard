"""
dashboard.py — Log Analyzer Dashboard (Log Explorer only)

Usage:
    streamlit run src/dashboard.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Config paths
# ---------------------------------------------------------------------------
_APP_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_DATA = _APP_ROOT / "data" / "cloudflare.duckdb"
_TMP_DATA = Path("/tmp/cloudflare.duckdb")
DB_PATH = _TMP_DATA if str(_APP_ROOT).startswith("/mount") else _LOCAL_DATA
LOCAL_PRIVATE_DB_PATH = _APP_ROOT.parent / "seo-geo-dashboard-data" / "data" / "cloudflare.duckdb"
PRIVATE_DB_URL = "https://api.github.com/repos/MarcW88/seo-geo-dashboard-data/contents/data/cloudflare.duckdb"

st.set_page_config(
    page_title="Log Analyzer — italiaanse-percolator.nl",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Dark tech CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 1.5rem 2rem; max-width: 100%; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    letter-spacing: 1.5px;
    color: #64748b !important;
    font-weight: 600;
}
[data-testid="stMetricValue"] {
    font-size: 1.7rem !important;
    font-weight: 700;
    color: #f1f5f9 !important;
    font-family: 'Inter', sans-serif;
}
.section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #38bdf8;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Plotly dark layout base
# ---------------------------------------------------------------------------
def dark_layout(**kwargs):
    base = dict(
        plot_bgcolor="#1e293b",
        paper_bgcolor="#0f172a",
        font=dict(family="Inter", size=12, color="#94a3b8"),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=False, color="#334155", tickcolor="#334155"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", color="#334155"),
    )
    base.update(kwargs)
    return base

# ---------------------------------------------------------------------------
# Bot identification
# ---------------------------------------------------------------------------
_BOTS = [
    ("googlebot", "Googlebot", "Search engines", False),
    ("google-inspectiontool", "Google Inspection Tool", "Search engines", False),
    ("googleother", "Google Other", "Search engines", False),
    ("adsbot-google", "Google AdsBot", "Search engines", False),
    ("mediapartners-google", "Google Mediapartners", "Search engines", False),
    ("bingbot", "Bingbot", "Search engines", False),
    ("bingpreview", "Bing Preview", "Search engines", False),
    ("msnbot", "MSNBot", "Search engines", False),
    ("adidxbot", "Bing AdIdxBot", "Search engines", False),
    ("duckduckbot", "DuckDuckBot", "Search engines", False),
    ("yandexbot", "YandexBot", "Search engines", False),
    ("baiduspider", "Baidu Spider", "Search engines", False),
    ("applebot", "Applebot", "Search engines", False),
    ("gptbot", "GPTBot (OpenAI)", "AI bots", False),
    ("chatgpt-user", "ChatGPT-User (OpenAI)", "AI bots", False),
    ("oai-searchbot", "OAI SearchBot (OpenAI)", "AI bots", False),
    ("claude-searchbot", "Claude-SearchBot (Anthropic)", "AI bots", False),
    ("claudebot", "ClaudeBot (Anthropic)", "AI bots", False),
    ("claude-web", "Claude Web (Anthropic)", "AI bots", False),
    ("anthropic", "Anthropic Bot", "AI bots", False),
    ("google-extended", "Google-Extended (Gemini)", "AI bots", False),
    ("perplexitybot", "PerplexityBot", "AI bots", False),
    ("cohere", "Cohere AI Bot", "AI bots", False),
    ("meta-externalagent", "Meta AI Bot", "AI bots", False),
    ("meta-externalads", "Meta AI Bot", "AI bots", False),
    ("amazonbot", "AmazonBot (Alexa AI)", "AI bots", False),
    ("bytespider", "ByteSpider (TikTok AI)", "AI bots", False),
    ("diffbot", "DiffBot", "AI bots", False),
    ("facebookbot", "FacebookBot (Meta AI)", "AI bots", False),
    ("ccbot", "CCBot (Common Crawl)", "AI bots", False),
    ("ia_archiver", "Wayback Machine (Archive.org)", "AI bots", False),
    ("archive.org_bot", "archive.org_bot", "AI bots", False),
    ("ahrefsbot", "Ahrefsbot", "Other bots", False),
    ("semrushbot", "SEMrushbot", "Other bots", False),
    ("mj12bot", "Majestic MJ12Bot", "Other bots", False),
    ("dotbot", "DotBot", "Other bots", False),
    ("blexbot", "BLEXBot", "Other bots", False),
    ("sitebulb", "Sitebulb", "Other bots", False),
    ("serpstatbot", "SerpstatBot", "Other bots", False),
    ("rogerbot", "Moz Rogerbot", "Other bots", False),
    ("facebookexternalhit", "Facebook External Hit", "Social networks", False),
    ("facebot", "Facebot (Facebook)", "Social networks", False),
    ("twitterbot", "TwitterBot", "Social networks", False),
    ("linkedinbot", "LinkedInBot", "Social networks", False),
    ("pinterestbot", "Pinterestbot", "Social networks", False),
    ("slackbot", "Slackbot", "Social networks", False),
    ("python-requests", "Python Requests", "Other bots", False),
    ("axios", "Axios", "Other bots", False),
    ("curl/", "cURL", "Other bots", False),
    ("wget/", "Wget", "Other bots", False),
    ("go-http-client", "Go HTTP Client", "Other bots", False),
    ("okhttp", "OkHttp", "Other bots", False),
    ("scrapy", "Scrapy", "Other bots", False),
    ("headlesschrome", "Headless Chrome", "Other bots", False),
]

def extract_bot_info(ua: str) -> dict:
    u = (ua or "").lower()
    for keyword, name, category, dangerous in _BOTS:
        if keyword in u:
            return {"name": name, "category": category, "dangerous": dangerous}
    return {"name": "Other", "category": "Other bots", "dangerous": False}

def classify_path(path: str) -> str:
    p = (path or "").lower()
    if p.endswith((".css", ".js")):
        return "Asset"
    elif p.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp")):
        return "Asset"
    elif p.endswith((".woff", ".woff2", ".ttf", ".eot")):
        return "Asset"
    elif p.endswith(".xml"):
        return "Sitemap"
    elif "/api/" in p or p.startswith("/api"):
        return "API"
    elif "/admin" in p or "/kentico" in p.lower():
        return "Admin"
    elif p in ("/", "/fr", "/en", "/nl"):
        return "Page"
    elif p.startswith(("/fr/", "/en/", "/nl/")):
        return "Page"
    else:
        return "Autre"

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
def ensure_database():
    if DB_PATH.exists():
        if str(_APP_ROOT).startswith("/mount"):
            if DB_PATH.stat().st_size < 1000:
                if LOCAL_PRIVATE_DB_PATH.exists():
                    import shutil
                    shutil.copy2(LOCAL_PRIVATE_DB_PATH, DB_PATH)
    else:
        if LOCAL_PRIVATE_DB_PATH.exists():
            import shutil
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LOCAL_PRIVATE_DB_PATH, DB_PATH)
        else:
            st.error("Database not found locally.")
            st.stop()

ensure_database()

conn = duckdb.connect(str(DB_PATH), read_only=True)
def query(sql: str) -> pd.DataFrame:
    return conn.execute(sql).df()

# ---------------------------------------------------------------------------
# Check for Log Explorer data
# ---------------------------------------------------------------------------
HAS_HTTP_LOGS = "cf_http_requests" in conn.execute("SHOW TABLES").fetchdf()["name"].values

if not HAS_HTTP_LOGS:
    st.error("Log Explorer data not available. Run the pipeline first.")
    st.stop()

# ---------------------------------------------------------------------------
# Date filter
# ---------------------------------------------------------------------------
min_date = conn.execute("SELECT MIN(DATE(edgestarttimestamp)) FROM cf_http_requests").fetchone()[0]
max_date = conn.execute("SELECT MAX(DATE(edgestarttimestamp)) FROM cf_http_requests").fetchone()[0]

if min_date and max_date:
    date_range = st.date_input("Analysis period", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if len(date_range) == 2:
        start_date, end_date = date_range
        DATE_FILTER = f"DATE(edgestarttimestamp) BETWEEN '{start_date}' AND '{end_date}'"
    else:
        DATE_FILTER = "1=1"
else:
    DATE_FILTER = "1=1"

# ---------------------------------------------------------------------------
# Request Distribution (KPIs)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Request Distribution</div>', unsafe_allow_html=True)

df_kpi = query(f"""
    SELECT
        COUNT(*) AS total_requests,
        COUNT(DISTINCT clientrequesturi) AS unique_urls,
        COUNT(DISTINCT clientrequestuseragent) AS unique_ua
    FROM cf_http_requests
    WHERE {DATE_FILTER}
""").iloc[0]

df_bots = query(f"""
    SELECT COUNT(*) AS bot_count
    FROM cf_http_requests
    WHERE {DATE_FILTER}
    AND LOWER(clientrequestuseragent) NOT LIKE '%bot%'
    AND LOWER(clientrequestuseragent) NOT LIKE '%crawler%'
    AND LOWER(clientrequestuseragent) NOT LIKE '%spider%'
""").iloc[0]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total requests", f"{int(df_kpi['total_requests']):,}")
k2.metric("Unique URLs", f"{int(df_kpi['unique_urls']):,}")
k3.metric("Bots detected", f"{int(df_bots['bot_count']):,}")
k4.metric("Unique user agents", f"{int(df_kpi['unique_ua']):,}")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Response codes
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Response codes</div>', unsafe_allow_html=True)

df_status = query(f"""
    SELECT edgeresponsestatus AS status_code, COUNT(*) AS total
    FROM cf_http_requests
    WHERE {DATE_FILTER}
    GROUP BY edgeresponsestatus
    ORDER BY total DESC
""")

if not df_status.empty:
    df_status_p = df_status.copy()
    df_status_p["cat"] = df_status_p["status_code"].apply(
        lambda x: "2xx" if 200 <= x < 300 else "3xx" if 300 <= x < 400 else "4xx" if 400 <= x < 500 else "5xx" if 500 <= x < 600 else "other"
    )
    cat_colors = {"2xx": "#10b981", "3xx": "#38bdf8", "4xx": "#f59e0b", "5xx": "#ef4444", "other": "#6b7280"}
    fig = px.bar(df_status_p, x="status_code", y="total", color="cat", color_discrete_map=cat_colors)
    fig.update_layout(**dark_layout(height=260, showlegend=True, title="Status codes",
                                     legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)))
    st.plotly_chart(fig, use_container_width=True)

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Bot activity
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Bot activity</div>', unsafe_allow_html=True)

df_ua_detail = query(f"""
    SELECT
        clientrequestuseragent AS user_agent,
        COUNT(*) AS total,
        COUNT(DISTINCT clientrequesturi) AS unique_urls,
        MIN(edgestarttimestamp) AS first_visit,
        MAX(edgestarttimestamp) AS last_visit
    FROM cf_http_requests
    WHERE {DATE_FILTER}
    GROUP BY clientrequestuseragent
    ORDER BY total DESC
""")

if not df_ua_detail.empty:
    _info = df_ua_detail["user_agent"].apply(lambda ua: pd.Series(extract_bot_info(ua)))
    df_ua_detail["bot_name"] = _info["name"]
    df_ua_detail["bot_category"] = _info["category"]
    df_ua_detail["dangerous"] = _info["dangerous"]
    
    bot_detail = (
        df_ua_detail.groupby(["bot_name", "bot_category", "dangerous"])
        .agg({"total": "sum", "unique_urls": "sum", "first_visit": "min", "last_visit": "max"})
        .reset_index().sort_values("total", ascending=False)
    )
    bot_detail["danger"] = bot_detail["dangerous"].apply(lambda d: "\U0001f534" if d else "")
    bot_detail["share %"] = (bot_detail["total"] / bot_detail["total"].sum() * 100).round(1)
    bot_detail["first_visit"] = pd.to_datetime(bot_detail["first_visit"]).dt.strftime("%d/%m/%y %H:%M")
    bot_detail["last_visit"] = pd.to_datetime(bot_detail["last_visit"]).dt.strftime("%d/%m/%y %H:%M")
    st.dataframe(
        bot_detail[["danger", "bot_name", "bot_category", "total", "unique_urls", "share %", "first_visit", "last_visit"]]
        .rename(columns={"bot_name": "Bot", "bot_category": "Cat\u00e9gorie", "total": "Requests", "unique_urls": "URLs uniques", "danger": "\u26a0", "first_visit": "Premi\u00e8re visite", "last_visit": "Derni\u00e8re visite"}),
        use_container_width=True, hide_index=True, height=400,
    )

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Crawl timeline
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Crawl timeline</div>', unsafe_allow_html=True)

df_timeline_raw = query(f"""
    SELECT
        DATE_TRUNC('hour', edgestarttimestamp) AS hour,
        clientrequestuseragent AS user_agent
    FROM cf_http_requests
    WHERE {DATE_FILTER}
""")
if not df_timeline_raw.empty:
    df_timeline_raw["hour"] = pd.to_datetime(df_timeline_raw["hour"])
    df_timeline_raw["bot_category"] = df_timeline_raw["user_agent"].apply(lambda ua: extract_bot_info(ua)["category"])
    df_bot_timeline = df_timeline_raw.groupby("hour").agg(
        total_hits=("user_agent", "count"),
        bot_hits=("bot_category", lambda x: (x != "Humain").sum())
    ).reset_index()
    fig = px.line(df_bot_timeline, x="hour", y=["total_hits", "bot_hits"],
                 labels={"value": "Hits", "variable": "Type"},
                 color_discrete_sequence=["#38bdf8", "#f59e0b"])
    fig.update_layout(**dark_layout(height=280, title=None, xaxis_title="Heure", yaxis_title="Hits",
                                     legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11))))
    st.plotly_chart(fig, use_container_width=True)

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Statistics by page category
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Statistics by page category</div>', unsafe_allow_html=True)

df_category_stats = query(f"""
    SELECT
        clientrequestpath AS path,
        COUNT(*) AS hits,
        AVG(response_time_ms) AS avg_ms
    FROM cf_http_requests
    WHERE {DATE_FILTER} AND response_time_ms IS NOT NULL
    GROUP BY clientrequestpath
""")
if not df_category_stats.empty:
    df_category_stats["page_type"] = df_category_stats["path"].apply(classify_path)
    df_category_summary = df_category_stats.groupby("page_type").agg(
        hits=("hits", "sum"),
        unique_urls=("path", "nunique"),
        avg_ms=("avg_ms", "mean")
    ).reset_index().sort_values("hits", ascending=False)
    df_category_summary["avg_ms"] = df_category_summary["avg_ms"].round(0).astype(int)
    df_category_summary["freq_per_day"] = (df_category_summary["hits"] / (max_date - min_date).days if max_date and min_date else 1).round(2)
    st.dataframe(
        df_category_summary[["page_type", "hits", "unique_urls", "freq_per_day", "avg_ms"]]
        .rename(columns={"page_type": "Cat\u00e9gorie", "hits": "Hits", "unique_urls": "URLs uniques", "freq_per_day": "Fr\u00e9q./jour", "avg_ms": "Temps moy. (ms)"}),
        use_container_width=True, hide_index=True, height=200,
    )

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Crawled pages
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Crawled pages</div>', unsafe_allow_html=True)

df_crawled = query(f"""
    SELECT
        clientrequesturi AS url,
        clientrequestuseragent AS user_agent,
        edgeresponsestatus AS status,
        response_time_ms,
        edgestarttimestamp AS timestamp
    FROM cf_http_requests
    WHERE {DATE_FILTER}
    ORDER BY edgestarttimestamp DESC
    LIMIT 500
""")
if not df_crawled.empty:
    df_crawled["bot_name"] = df_crawled["user_agent"].apply(lambda ua: extract_bot_info(ua)["name"])
    df_crawled["bot_category"] = df_crawled["user_agent"].apply(lambda ua: extract_bot_info(ua)["category"])
    df_crawled["timestamp"] = pd.to_datetime(df_crawled["timestamp"]).dt.strftime("%d/%m/%y %H:%M")
    df_crawled["response_time_ms"] = df_crawled["response_time_ms"].round(0).astype(int)
    st.dataframe(
        df_crawled[["url", "bot_name", "bot_category", "status", "response_time_ms", "timestamp"]]
        .rename(columns={"url": "URL", "bot_name": "Bot", "bot_category": "Cat\u00e9gorie", "status": "Status", "response_time_ms": "Temps (ms)", "timestamp": "Timestamp"}),
        use_container_width=True, hide_index=True, height=400,
    )

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Request details
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Request details</div>', unsafe_allow_html=True)

content_type_filter = st.selectbox(
    "Filtrer par type de contenu",
    ["Tous", "Page", "Asset", "API", "Admin", "Sitemap", "Autre"],
    index=0
)

df_requests = query(f"""
    SELECT
        clientrequesturi AS url,
        clientrequestuseragent AS user_agent,
        edgeresponsestatus AS status,
        response_time_ms,
        edgestarttimestamp AS timestamp
    FROM cf_http_requests
    WHERE {DATE_FILTER}
    ORDER BY edgestarttimestamp DESC
    LIMIT 1000
""")
if not df_requests.empty:
    df_requests["bot_name"] = df_requests["user_agent"].apply(lambda ua: extract_bot_info(ua)["name"])
    df_requests["bot_category"] = df_requests["user_agent"].apply(lambda ua: extract_bot_info(ua)["category"])
    df_requests["content_type"] = df_requests["url"].apply(classify_path)
    df_requests["timestamp"] = pd.to_datetime(df_requests["timestamp"]).dt.strftime("%d/%m/%y %H:%M")
    df_requests["response_time_ms"] = df_requests["response_time_ms"].round(0).astype(int)

    if content_type_filter != "Tous":
        df_requests = df_requests[df_requests["content_type"] == content_type_filter]

    st.dataframe(
        df_requests[["url", "bot_name", "bot_category", "content_type", "status", "response_time_ms", "timestamp"]]
        .rename(columns={"url": "URL", "bot_name": "Bot", "bot_category": "Cat\u00e9gorie", "content_type": "Type", "status": "Status", "response_time_ms": "Temps (ms)", "timestamp": "Timestamp"}),
        use_container_width=True, hide_index=True, height=500,
    )

conn.close()
