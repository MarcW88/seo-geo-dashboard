"""
dashboard.py — Log Analyzer Dashboard (Log Explorer only)

Usage:
    streamlit run src/dashboard.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import requests
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
    text-transform: uppercase;
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
_BBOTS = [
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
# DB connection (original logic)
# ---------------------------------------------------------------------------
def ensure_database():
    if DB_PATH.exists() and not str(_APP_ROOT).startswith("/mount"):
        return
    if LOCAL_PRIVATE_DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DB_PATH.write_bytes(LOCAL_PRIVATE_DB_PATH.read_bytes())
        return
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        db_url = st.secrets.get("PRIVATE_DB_URL", PRIVATE_DB_URL)
    except Exception:
        return
    if not token:
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    meta = requests.get(db_url, headers={"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}, timeout=30)
    if meta.status_code != 200:
        st.warning(f"⚠️ GitHub API: HTTP {meta.status_code} — {meta.text[:200]}")
        return
    download_url = meta.json().get("download_url", "")
    if not download_url:
        st.warning(f"⚠️ No download_url in response: {meta.text[:200]}")
        return
    content = requests.get(download_url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if content.status_code == 200 and len(content.content) > 1000:
        DB_PATH.write_bytes(content.content)
    else:
        st.warning(f"⚠️ Download failed: HTTP {content.status_code}, {len(content.content)} bytes")

@st.cache_resource
def get_conn():
    if not DB_PATH.exists():
        return None
    return duckdb.connect(str(DB_PATH), read_only=True)

def query(sql: str) -> pd.DataFrame:
    conn = get_conn()
    if conn is None:
        return pd.DataFrame()
    try:
        return conn.execute(sql).fetchdf()
    except Exception:
        return pd.DataFrame()

def table_exists(table_name: str) -> bool:
    df = query(f"SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_name = '{table_name}'")
    return not df.empty and int(df.iloc[0]["n"]) > 0

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
ensure_database()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:1.5rem;">
    <span style="font-size:1.5rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.5px;">⚡ Log Analyzer</span>
    <span style="font-size:13px;color:#64748b;font-family:monospace;">italiaanse-percolator.nl</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Date filter
# ---------------------------------------------------------------------------
HAS_HTTP_LOGS = table_exists("cf_http_requests")
if HAS_HTTP_LOGS:
    df_dates = query("SELECT MIN(date) as min_d, MAX(date) as max_d FROM cf_http_requests")
else:
    df_dates = query("SELECT MIN(date) as min_d, MAX(date) as max_d FROM cf_requests_daily")
if not df_dates.empty and df_dates.iloc[0]["min_d"] is not None:
    min_date = pd.to_datetime(df_dates.iloc[0]["min_d"]).date()
    max_date = pd.to_datetime(df_dates.iloc[0]["max_d"]).date()
else:
    min_date = max_date = None

with st.container():
    fc1 = st.columns([1])[0]
    with fc1:
        if min_date:
            date_range = st.date_input("Période", value=(min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
            start_date, end_date = (date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_date, max_date))
        else:
            start_date = end_date = None

# ---------------------------------------------------------------------------
# No data guard
# ---------------------------------------------------------------------------
if start_date is None:
    st.markdown("## Pas encore de données")
    db_exists = DB_PATH.exists()
    local_exists = LOCAL_PRIVATE_DB_PATH.exists()
    try:
        has_token = bool(st.secrets.get("GITHUB_TOKEN", ""))
    except Exception:
        has_token = False
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Diagnostic")
        st.write(f"{'✅' if db_exists else '❌'} DB : `{DB_PATH}`")
        st.write(f"{'✅' if local_exists else '❌'} DB data-repo : `{LOCAL_PRIVATE_DB_PATH}`")
        st.write(f"{'✅' if has_token else '❌'} GITHUB_TOKEN dans secrets Streamlit")
    with col_b:
        if not has_token:
            st.code('GITHUB_TOKEN = "github_pat_xxx"\nPRIVATE_DB_URL = "https://api.github.com/repos/MarcW88/seo-geo-dashboard-data/contents/data/cloudflare.duckdb"', language="toml")
        elif not db_exists:
            st.warning("Token présent mais DB non téléchargée. Vérifie les permissions (Contents: Read).")
    st.stop()

DATE_FILTER = f"date >= '{start_date}' AND date <= '{end_date}'"

# ---------------------------------------------------------------------------
# Section 1 — Request Distribution
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Request Distribution</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
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
else:
    st.info("Request distribution disponible avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 2 — Bot activity
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Bot activity</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
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
            .rename(columns={"bot_name": "Bot", "bot_category": "Catégorie", "total": "Requests", "unique_urls": "URLs uniques", "danger": "⚠", "first_visit": "Première visite", "last_visit": "Dernière visite"}),
            use_container_width=True, hide_index=True, height=400,
        )
else:
    st.info("Bot activity disponible avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 3 — Request details
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Request details</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
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
            .rename(columns={"url": "URL", "bot_name": "Bot", "bot_category": "Catégorie", "content_type": "Type", "status": "Status", "response_time_ms": "Temps (ms)", "timestamp": "Timestamp"}),
            use_container_width=True, hide_index=True, height=500,
        )
else:
    st.info("Détails des requêtes disponibles avec les vrais logs Log Explorer.")
