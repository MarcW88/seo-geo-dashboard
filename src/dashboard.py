"""
dashboard.py — Log Analyzer Dashboard (6 views)

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
.filter-bar {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
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
    ("ahrefsbot", "Ahrefsbot", "SEO tools", False),
    ("semrushbot", "SEMrushbot", "SEO tools", False),
    ("mj12bot", "Majestic MJ12Bot", "SEO tools", False),
    ("dotbot", "DotBot", "SEO tools", False),
    ("blexbot", "BLEXBot", "SEO tools", False),
    ("sitebulb", "Sitebulb", "SEO tools", False),
    ("serpstatbot", "SerpstatBot", "SEO tools", False),
    ("rogerbot", "Moz Rogerbot", "SEO tools", False),
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
        return "CSS/JS"
    elif p.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp")):
        return "Images"
    elif p.endswith((".woff", ".woff2", ".ttf", ".eot")):
        return "Fonts"
    elif p.endswith(".xml"):
        return "XML"
    elif "/api/" in p or p.startswith("/api"):
        return "API"
    elif "/admin" in p or "/kentico" in p.lower():
        return "Admin"
    elif p.endswith((".html", ".htm")) or "?" in p:
        return "HTML"
    elif p in ("/", "/fr", "/en", "/nl"):
        return "HTML"
    elif p.startswith(("/fr/", "/en/", "/nl/")):
        return "HTML"
    else:
        return "Other"

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
# GlobalFiltersBar
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
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        if min_date:
            date_range = st.date_input("Période", value=(min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
            start_date, end_date = (date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_date, max_date))
        else:
            start_date = end_date = None
    with fc2:
        bot_filter = st.selectbox("Bot filter", ["All", "Only bots", "Only users"], label_visibility="collapsed")
    with fc3:
        status_filter = st.selectbox("Status filter", ["All", "2xx", "3xx", "4xx", "5xx"], label_visibility="collapsed")

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

# Build SQL filters
bot_filter_sql = ""
if bot_filter == "Only bots":
    bot_filter_sql = "AND LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%'"
elif bot_filter == "Only users":
    bot_filter_sql = "AND LOWER(clientrequestuseragent) NOT LIKE '%bot%' AND LOWER(clientrequestuseragent) NOT LIKE '%crawler%' AND LOWER(clientrequestuseragent) NOT LIKE '%spider%'"

status_filter_sql = ""
if status_filter != "All":
    if status_filter == "2xx":
        status_filter_sql = "AND edgeresponsestatus >= 200 AND edgeresponsestatus < 300"
    elif status_filter == "3xx":
        status_filter_sql = "AND edgeresponsestatus >= 300 AND edgeresponsestatus < 400"
    elif status_filter == "4xx":
        status_filter_sql = "AND edgeresponsestatus >= 400 AND edgeresponsestatus < 500"
    elif status_filter == "5xx":
        status_filter_sql = "AND edgeresponsestatus >= 500 AND edgeresponsestatus < 600"

# ---------------------------------------------------------------------------
# View 1: Vue globale (Header + KPIs)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Vue globale</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    # Total requests
    df_total = query(f"""
        SELECT
            COUNT(*) AS total_hits,
            COUNT(DISTINCT clientrequesturi) AS unique_urls
        FROM cf_http_requests
        WHERE {DATE_FILTER} {bot_filter_sql} {status_filter_sql}
    """).iloc[0]
    
    # User vs Bot split
    df_split = query(f"""
        SELECT
            CASE 
                WHEN LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%' 
                THEN 'bot' 
                ELSE 'user' 
            END AS type,
            COUNT(*) AS hits
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_filter_sql}
        GROUP BY type
    """)
    
    user_hits = 0
    bot_hits = 0
    if not df_split.empty:
        user_hits = int(df_split[df_split["type"] == "user"]["hits"].sum())
        bot_hits = int(df_split[df_split["type"] == "bot"]["hits"].sum())
    
    # Bots detected
    df_bots_detected = query(f"""
        SELECT COUNT(DISTINCT clientrequestuseragent) AS bots_detected
        FROM cf_http_requests
        WHERE {DATE_FILTER} 
        AND (LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%')
    """).iloc[0]
    
    # Status codes
    df_status = query(f"""
        SELECT
            CASE 
                WHEN edgeresponsestatus >= 200 AND edgeresponsestatus < 300 THEN '2xx'
                WHEN edgeresponsestatus >= 300 AND edgeresponsestatus < 400 THEN '3xx'
                WHEN edgeresponsestatus >= 400 AND edgeresponsestatus < 500 THEN '4xx'
                WHEN edgeresponsestatus >= 500 AND edgeresponsestatus < 600 THEN '5xx'
                ELSE 'other'
            END AS status_group,
            COUNT(*) AS hits
        FROM cf_http_requests
        WHERE {DATE_FILTER} {bot_filter_sql}
        GROUP BY status_group
    """)
    
    k1, k2, k3, k4 = st.columns(4)
    
    total_hits = int(df_total["total_hits"])
    k1.metric("Total requests", f"{total_hits:,}", 
              help=f"Users: {user_hits:,} ({user_hits/total_hits*100:.1f}%), Bots: {bot_hits:,} ({bot_hits/total_hits*100:.1f}%)")
    k2.metric("Unique URLs", f"{int(df_total['unique_urls']):,}")
    k3.metric("Bots detected", f"{int(df_bots_detected['bots_detected']):,}")
    
    # Status codes as clickable badges
    status_text = " | ".join([f"{row['status_group']}: {row['hits']:,}" for _, row in df_status.iterrows()])
    k4.metric("Response codes", status_text if not df_status.empty else "—")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View 2: Bot activity
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Bot activity</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    df_ua_detail = query(f"""
        SELECT
            clientrequestuseragent AS user_agent,
            COUNT(*) AS total,
            COUNT(DISTINCT clientrequesturi) AS unique_urls,
            MIN(edgestarttimestamp) AS first_seen,
            MAX(edgestarttimestamp) AS last_seen
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_filter_sql}
        AND (LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%')
        GROUP BY clientrequestuseragent
        ORDER BY total DESC
    """)

    if not df_ua_detail.empty:
        _info = df_ua_detail["user_agent"].apply(lambda ua: pd.Series(extract_bot_info(ua)))
        df_ua_detail["bot_name"] = _info["name"]
        df_ua_detail["bot_category"] = _info["category"]
        
        # Show raw user agents for debugging
        with st.expander("Debug: Raw user agents"):
            st.dataframe(df_ua_detail[["user_agent", "bot_name", "bot_category", "total"]].head(20), use_container_width=True, hide_index=True)
        
        bot_detail = (
            df_ua_detail.groupby(["bot_name", "bot_category"])
            .agg({"total": "sum", "unique_urls": "sum", "first_seen": "min", "last_seen": "max"})
            .reset_index().sort_values("total", ascending=False)
        )
        if not bot_detail.empty:
            bot_detail["share_of_total"] = (bot_detail["total"] / bot_detail["total"].sum() * 100).round(2)
            bot_detail["first_seen"] = pd.to_datetime(bot_detail["first_seen"]).dt.strftime("%d/%m/%y %H:%M")
            bot_detail["last_seen"] = pd.to_datetime(bot_detail["last_seen"]).dt.strftime("%d/%m/%y %H:%M")
            st.dataframe(
                bot_detail[["bot_name", "bot_category", "total", "share_of_total", "first_seen", "last_seen"]]
                .rename(columns={"bot_name": "Bot", "bot_category": "Category", "total": "Hits", "share_of_total": "% of total", "first_seen": "First seen", "last_seen": "Last seen"}),
                use_container_width=True, hide_index=True, height=400,
            )
        else:
            st.info("No bot data found for the selected period and filters.")
else:
    st.info("Bot activity disponible avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View 3: Crawl timeline
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Crawl timeline</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    group_by = st.selectbox("Group by", ["day", "week"], label_visibility="collapsed")
    
    if group_by == "day":
        df_timeline = query(f"""
            SELECT
                DATE(edgestarttimestamp) AS date,
                CASE 
                    WHEN LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%' 
                    THEN 'Bot' 
                    ELSE 'User' 
                END AS type,
                COUNT(*) AS hits
            FROM cf_http_requests
            WHERE {DATE_FILTER} {status_filter_sql}
            GROUP BY DATE(edgestarttimestamp), type
            ORDER BY date
        """)
    else:
        df_timeline = query(f"""
            SELECT
                DATE_TRUNC('week', edgestarttimestamp) AS date,
                CASE 
                    WHEN LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%' 
                    THEN 'Bot' 
                    ELSE 'User' 
                END AS type,
                COUNT(*) AS hits
            FROM cf_http_requests
            WHERE {DATE_FILTER} {status_filter_sql}
            GROUP BY DATE_TRUNC('week', edgestarttimestamp), type
            ORDER BY date
        """)
    
    if not df_timeline.empty:
        df_timeline["date"] = pd.to_datetime(df_timeline["date"])
        fig = px.bar(df_timeline, x="date", y="hits", color="type",
                     color_discrete_map={"User": "#38bdf8", "Bot": "#f59e0b"},
                     labels={"hits": "Hits", "type": "Type"})
        fig.update_layout(**dark_layout(height=300, title=None, xaxis_title="Date", yaxis_title="Hits",
                                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Crawl timeline disponible avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View 4: Statistics by page category
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Statistics by page category</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    category_search = st.text_input("Search category...", "", placeholder="ex: /fr, /en", label_visibility="collapsed")
    file_type_filter = st.selectbox("File type", ["All", "HTML", "CSS/JS", "Images", "XML", "Fonts", "Other"], label_visibility="collapsed")
    
    file_filter_sql = ""
    if file_type_filter != "All":
        if file_type_filter == "HTML":
            file_filter_sql = "AND (clientrequestpath LIKE '%.html' OR clientrequestpath LIKE '%.htm' OR clientrequestpath LIKE '?' OR clientrequestpath IN ('/', '/fr', '/en', '/nl') OR clientrequestpath LIKE '/fr/%' OR clientrequestpath LIKE '/en/%' OR clientrequestpath LIKE '/nl/%')"
        elif file_type_filter == "CSS/JS":
            file_filter_sql = "AND (clientrequestpath LIKE '%.css' OR clientrequestpath LIKE '%.js')"
        elif file_type_filter == "Images":
            file_filter_sql = "AND (clientrequestpath LIKE '%.png' OR clientrequestpath LIKE '%.jpg' OR clientrequestpath LIKE '%.jpeg' OR clientrequestpath LIKE '%.gif' OR clientrequestpath LIKE '%.svg' OR clientrequestpath LIKE '%.ico' OR clientrequestpath LIKE '%.webp')"
        elif file_type_filter == "XML":
            file_filter_sql = "AND clientrequestpath LIKE '%.xml'"
        elif file_type_filter == "Fonts":
            file_filter_sql = "AND (clientrequestpath LIKE '%.woff' OR clientrequestpath LIKE '%.woff2' OR clientrequestpath LIKE '%.ttf' OR clientrequestpath LIKE '%.eot')"
    
    category_filter_sql = ""
    if category_search:
        category_filter_sql = f"AND clientrequestpath LIKE '%{category_search}%'"
    
    df_category = query(f"""
        SELECT
            clientrequestpath AS path,
            COUNT(*) AS total_hits,
            COUNT(DISTINCT clientrequestpath) AS unique_urls,
            AVG(response_time_ms) AS avg_duration_ms
        FROM cf_http_requests
        WHERE {DATE_FILTER} {bot_filter_sql} {status_filter_sql} {file_filter_sql} {category_filter_sql}
        GROUP BY clientrequestpath
        ORDER BY total_hits DESC
        LIMIT 100
    """)
    
    if not df_category.empty:
        df_category["category"] = df_category["path"].apply(lambda p: "/".join(p.split("/")[:2]) if p.count("/") > 0 else p)
        df_category_summary = df_category.groupby("category").agg(
            total_hits=("total_hits", "sum"),
            unique_urls=("unique_urls", "sum"),
            avg_duration_ms=("avg_duration_ms", "mean")
        ).reset_index().sort_values("total_hits", ascending=False)
        df_category_summary["hits_per_day"] = (df_category_summary["total_hits"] / (df_dates.iloc[0]["max_d"] - df_dates.iloc[0]["min_d"]).days if not df_dates.empty else 1).round(2)
        df_category_summary["avg_duration_ms"] = df_category_summary["avg_duration_ms"].round(0).astype(int)
        st.dataframe(
            df_category_summary[["category", "total_hits", "unique_urls", "hits_per_day", "avg_duration_ms"]]
            .rename(columns={"category": "Category", "total_hits": "Total hits", "unique_urls": "Unique URLs", "hits_per_day": "Hits/day", "avg_duration_ms": "Avg duration (ms)"}),
            use_container_width=True, hide_index=True, height=300,
        )
else:
    st.info("Statistics by page category disponibles avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View 5: Crawled pages
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Crawled pages</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    url_filter = st.text_input("Filter by URL...", "", placeholder="ex: /en/shoes", label_visibility="collapsed")
    bot_specific_filter = st.selectbox("Bot", ["All"] + [b[1] for b in _BOTS], label_visibility="collapsed")
    
    bot_specific_filter_sql = ""
    if bot_specific_filter != "All":
        bot_specific_filter_sql = f"AND LOWER(clientrequestuseragent) LIKE '%{bot_specific_filter.lower()}%'"
    
    url_filter_sql = ""
    if url_filter:
        url_filter_sql = f"AND clientrequesturi LIKE '%{url_filter}%'"
    
    df_crawled = query(f"""
        SELECT
            clientrequesturi AS url,
            COUNT(*) AS total_hits,
            COUNT(DISTINCT clientrequestuseragent) AS unique_bots,
            MAX(edgestarttimestamp) AS last_crawl
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_filter_sql} {bot_specific_filter_sql} {url_filter_sql}
        AND (LOWER(clientrequestuseragent) LIKE '%bot%' OR LOWER(clientrequestuseragent) LIKE '%crawler%' OR LOWER(clientrequestuseragent) LIKE '%spider%')
        GROUP BY clientrequesturi
        ORDER BY last_crawl DESC
        LIMIT 100
    """)
    
    if not df_crawled.empty:
        df_crawled["last_crawl"] = pd.to_datetime(df_crawled["last_crawl"]).dt.strftime("%d/%m/%y %H:%M")
        st.dataframe(
            df_crawled[["url", "total_hits", "unique_bots", "last_crawl"]]
            .rename(columns={"url": "URL", "total_hits": "Total hits", "unique_bots": "Unique bots", "last_crawl": "Last crawl"}),
            use_container_width=True, hide_index=True, height=400,
        )
else:
    st.info("Crawled pages disponibles avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View 6: Request details
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Request details</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    rd_url_filter = st.text_input("URL contains...", "", placeholder="ex: /product", label_visibility="collapsed")
    rd_bot_filter = st.selectbox("Bot (Request details)", ["All"] + [b[1] for b in _BOTS], label_visibility="collapsed")
    rd_status_filter = st.selectbox("Status (Request details)", ["All", "2xx", "3xx", "4xx", "5xx"], label_visibility="collapsed")
    
    # Resource type toggles
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        toggle_html = st.checkbox("HTML", value=True)
    with col2:
        toggle_cssjs = st.checkbox("CSS/JS", value=False)
    with col3:
        toggle_images = st.checkbox("Images", value=False)
    with col4:
        toggle_xml = st.checkbox("XML", value=False)
    with col5:
        toggle_fonts = st.checkbox("Fonts", value=False)
    
    rd_bot_filter_sql = ""
    if rd_bot_filter != "All":
        rd_bot_filter_sql = f"AND LOWER(clientrequestuseragent) LIKE '%{rd_bot_filter.lower()}%'"
    
    rd_status_filter_sql = ""
    if rd_status_filter != "All":
        if rd_status_filter == "2xx":
            rd_status_filter_sql = "AND edgeresponsestatus >= 200 AND edgeresponsestatus < 300"
        elif rd_status_filter == "3xx":
            rd_status_filter_sql = "AND edgeresponsestatus >= 300 AND edgeresponsestatus < 400"
        elif rd_status_filter == "4xx":
            rd_status_filter_sql = "AND edgeresponsestatus >= 400 AND edgeresponsestatus < 500"
        elif rd_status_filter == "5xx":
            rd_status_filter_sql = "AND edgeresponsestatus >= 500 AND edgeresponsestatus < 600"
    
    rd_url_filter_sql = ""
    if rd_url_filter:
        rd_url_filter_sql = f"AND clientrequesturi LIKE '%{rd_url_filter}%'"
    
    # Build resource type filter
    resource_filters = []
    if toggle_html:
        resource_filters.append("(clientrequestpath LIKE '%.html' OR clientrequestpath LIKE '%.htm' OR clientrequestpath LIKE '?' OR clientrequestpath IN ('/', '/fr', '/en', '/nl') OR clientrequestpath LIKE '/fr/%' OR clientrequestpath LIKE '/en/%' OR clientrequestpath LIKE '/nl/%')")
    if toggle_cssjs:
        resource_filters.append("(clientrequestpath LIKE '%.css' OR clientrequestpath LIKE '%.js')")
    if toggle_images:
        resource_filters.append("(clientrequestpath LIKE '%.png' OR clientrequestpath LIKE '%.jpg' OR clientrequestpath LIKE '%.jpeg' OR clientrequestpath LIKE '%.gif' OR clientrequestpath LIKE '%.svg' OR clientrequestpath LIKE '%.ico' OR clientrequestpath LIKE '%.webp')")
    if toggle_xml:
        resource_filters.append("clientrequestpath LIKE '%.xml'")
    if toggle_fonts:
        resource_filters.append("(clientrequestpath LIKE '%.woff' OR clientrequestpath LIKE '%.woff2' OR clientrequestpath LIKE '%.ttf' OR clientrequestpath LIKE '%.eot')")
    
    rd_resource_filter_sql = ""
    if resource_filters:
        rd_resource_filter_sql = "AND (" + " OR ".join(resource_filters) + ")"
    
    df_requests = query(f"""
        SELECT
            edgestarttimestamp AS datetime,
            clientrequesturi AS url,
            clientrequestuseragent AS user_agent,
            edgeresponsestatus AS status_code,
            response_time_ms AS duration_ms
        FROM cf_http_requests
        WHERE {DATE_FILTER} {rd_bot_filter_sql} {rd_status_filter_sql} {rd_url_filter_sql} {rd_resource_filter_sql}
        ORDER BY edgestarttimestamp DESC
        LIMIT 1000
    """)
    
    if not df_requests.empty:
        df_requests["datetime"] = pd.to_datetime(df_requests["datetime"]).dt.strftime("%d/%m/%y %H:%M")
        df_requests["bot"] = df_requests["user_agent"].apply(lambda ua: extract_bot_info(ua)["name"])
        df_requests["category"] = df_requests["url"].apply(classify_path)
        df_requests["duration_ms"] = df_requests["duration_ms"].round(0).astype(int)
        st.dataframe(
            df_requests[["datetime", "url", "bot", "category", "status_code", "duration_ms"]]
            .rename(columns={"datetime": "Date/Time", "url": "URL", "bot": "Bot", "category": "Category", "status_code": "Status", "duration_ms": "Duration (ms)"}),
            use_container_width=True, hide_index=True, height=500,
        )
else:
    st.info("Request details disponibles avec les vrais logs Log Explorer.")
