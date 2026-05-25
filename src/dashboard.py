"""
dashboard.py — Log Analyzer Dashboard (single-page dark tech)

Usage:
    streamlit run src/dashboard.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    # (keyword, display_name, category, is_dangerous)
    # Moteurs de recherche
    ("googlebot",             "Googlebot",               "Moteur de recherche", False),
    ("google-inspectiontool", "Google Inspection Tool",  "Moteur de recherche", False),
    ("googleother",           "Google Other",            "Moteur de recherche", False),
    ("adsbot-google",         "Google AdsBot",           "Moteur de recherche", False),
    ("mediapartners-google",  "Google Mediapartners",    "Moteur de recherche", False),
    ("bingbot",               "Bingbot",                 "Moteur de recherche", False),
    ("bingpreview",           "Bing Preview",            "Moteur de recherche", False),
    ("msnbot",                "MSNBot",                  "Moteur de recherche", False),
    ("adidxbot",              "Bing AdIdxBot",           "Moteur de recherche", False),
    ("duckduckbot",           "DuckDuckBot",             "Moteur de recherche", False),
    ("yandexbot",             "YandexBot",               "Moteur de recherche", False),
    ("yandex.com/bots",       "YandexBot",               "Moteur de recherche", False),
    ("baiduspider",           "Baidu Spider",            "Moteur de recherche", False),
    ("applebot",              "Applebot",                "Moteur de recherche", False),
    ("sogou",                 "Sogou Spider",            "Moteur de recherche", False),
    ("naverbot",              "NaverBot",                "Moteur de recherche", False),
    # IA
    ("gptbot",                "GPTBot (OpenAI)",             "IA Bot", False),
    ("chatgpt-user",          "ChatGPT-User (OpenAI)",       "IA Bot", False),
    ("oai-searchbot",         "OAI SearchBot (OpenAI)",      "IA Bot", False),
    ("claude-searchbot",      "Claude-SearchBot (Anthropic)","IA Bot", False),
    ("claudebot",             "ClaudeBot (Anthropic)",       "IA Bot", False),
    ("claude-web",            "Claude Web (Anthropic)",      "IA Bot", False),
    ("anthropic",             "Anthropic Bot",               "IA Bot", False),
    ("google-extended",       "Google-Extended (Gemini)",    "IA Bot", False),
    ("perplexitybot",         "PerplexityBot",               "IA Bot", False),
    ("cohere",                "Cohere AI Bot",               "IA Bot", False),
    ("meta-externalagent",    "Meta AI Bot",                 "IA Bot", False),
    ("amazonbot",             "AmazonBot (Alexa AI)",        "IA Bot", False),
    ("bytespider",            "ByteSpider (TikTok AI)",      "IA Bot", False),
    ("diffbot",               "DiffBot",                     "IA Bot", False),
    ("facebookbot",           "FacebookBot (Meta AI)",       "IA Bot", False),
    ("anchor browser",        "Anchor Browser (Anchor)",     "IA Bot", False),
    ("ccbot",                 "CCBot (Common Crawl)",        "IA Bot", False),
    ("ia_archiver",           "Wayback Machine (Archive.org)","Archiveur", False),
    ("archive.org_bot",       "archive.org_bot",             "Archiveur", False),
    ("arquivo",               "Arquivo Web Crawler",         "Archiveur", False),
    # SEO
    ("ahrefsbot",             "AhrefsBot",               "SEO Tool", False),
    ("semrushbot",            "SEMrushBot",              "SEO Tool", False),
    ("mj12bot",               "Majestic MJ12Bot",        "SEO Tool", False),
    ("dotbot",                "OpenLinkProfiler DotBot", "SEO Tool", False),
    ("blexbot",               "BLEXBot",                 "SEO Tool", False),
    ("sitebulb",              "Sitebulb",                "SEO Tool", False),
    ("serpstatbot",           "SerpstatBot",             "SEO Tool", False),
    ("rogerbot",              "Moz Rogerbot",            "SEO Tool", False),
    ("seolyt",                "SeoLyt",                  "SEO Tool", False),
    ("seokicks",              "SEOkicks",                "SEO Tool", False),
    # Social
    ("facebookexternalhit",   "Facebook Crawler",        "Social", False),
    ("facebot",               "Facebot (Facebook)",      "Social", False),
    ("twitterbot",            "TwitterBot",              "Social", False),
    ("linkedinbot",           "LinkedInBot",             "Social", False),
    ("pinterestbot",          "PinterestBot",            "Social", False),
    ("slackbot",              "Slackbot",                "Social", False),
    ("whatsapp",              "WhatsApp Preview",        "Social", False),
    ("telegrambot",           "TelegramBot",             "Social", False),
    ("discordbot",            "DiscordBot",              "Social", False),
    # Scanners dangereux
    ("l9scan",                "LeakIX Scanner",          "Scanner", True),
    ("leakix",                "LeakIX Scanner",          "Scanner", True),
    ("shodan",                "Shodan",                  "Scanner", True),
    ("censys",                "Censys",                  "Scanner", True),
    ("masscan",               "Masscan",                 "Scanner", True),
    ("zgrab",                 "ZGrab",                   "Scanner", True),
    ("nuclei",                "Nuclei",                  "Scanner", True),
    ("nikto",                 "Nikto",                   "Scanner", True),
    ("sqlmap",                "SQLMap",                  "Scanner", True),
    ("nmap",                  "Nmap",                    "Scanner", True),
    ("acunetix",              "Acunetix",                "Scanner", True),
    ("burpsuite",             "Burp Suite",              "Scanner", True),
    ("dirbuster",             "DirBuster",               "Scanner", True),
    ("gobuster",              "GoBuster",                "Scanner", True),
    ("wfuzz",                 "WFuzz",                   "Scanner", True),
    ("nessus",                "Nessus",                  "Scanner", True),
    ("skipfish",              "Skipfish",                "Scanner", True),
    ("w3af",                  "W3AF",                    "Scanner", True),
    # Scripts / HTTP clients
    ("python-requests",       "Python Requests",         "Script", False),
    ("axios",                 "Axios",                   "Script", False),
    ("curl/",                 "cURL",                    "Script", False),
    ("wget/",                 "Wget",                    "Script", False),
    ("go-http-client",        "Go HTTP Client",          "Script", False),
    ("java/",                 "Java HTTP",               "Script", False),
    ("okhttp",                "OkHttp",                  "Script", False),
    ("scrapy",                "Scrapy",                  "Script", False),
    ("libwww-perl",           "Perl LWP",                "Script", False),
    ("headlesschrome",        "Headless Chrome",         "Script", False),
]


def extract_bot_info(ua: str) -> dict:
    u = (ua or "").lower()
    for keyword, name, category, dangerous in _BOTS:
        if keyword in u:
            return {"name": name, "category": category, "dangerous": dangerous}
    if any(k in u for k in ["bot", "crawl", "spider", "slurp", "fetcher"]):
        words = [w for w in (ua or "").split() if len(w) > 3]
        raw = words[0][:40] if words else "Bot inconnu"
        return {"name": raw, "category": "Bot inconnu", "dangerous": False}
    if any(k in u for k in ["iphone", "android", "mobile"]):
        return {"name": "Navigateur mobile", "category": "Humain", "dangerous": False}
    if any(k in u for k in ["mozilla", "chrome", "firefox", "safari", "edge"]):
        return {"name": "Navigateur desktop", "category": "Humain", "dangerous": False}
    return {"name": (ua or "Inconnu")[:50], "category": "Inconnu", "dangerous": False}


BOT_COLORS = {
    "Moteur de recherche": "#4285f4",
    "IA Bot":              "#f59e0b",
    "SEO Tool":            "#a855f7",
    "Social":              "#ec4899",
    "Scanner":             "#ef4444",
    "Script":              "#6b7280",
    "Bot inconnu":         "#475569",
    "Humain":              "#38bdf8",
    "Archiveur":           "#0891b2",
    "Inconnu":             "#334155",
}


def classify_path(path: str) -> str:
    p = (path or "/").lower()
    if p in ("/", "/index.html", "/index.php"):
        return "Home"
    if "boutique" in p:
        return "Boutique"
    if "/producten/" in p or "/produits/" in p or "/product" in p:
        return "Produit"
    if "review" in p:
        return "Review"
    if p.startswith("/blog") or "/gidsen/" in p or "/koopgids/" in p or "/guide" in p:
        return "Blog"
    if "/categories/" in p or "/categorie" in p or "/marques/" in p or "/tag/" in p:
        return "Catégorie"
    if any(x in p for x in [".css", ".js", ".png", ".jpg", ".svg", ".ico", ".woff", ".xml", ".txt"]):
        return "Asset"
    return "Autre"


# ---------------------------------------------------------------------------
# DB connection
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
# Inline filter bar
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
    fc1, fc2, fc3, fc4 = st.columns([2, 1.2, 1.5, 1.5])
    with fc1:
        if min_date:
            date_range = st.date_input("Période", value=(min_date, max_date), min_value=min_date, max_value=max_date, label_visibility="collapsed")
            start_date, end_date = (date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_date, max_date))
        else:
            start_date = end_date = None
    with fc2:
        traffic_filter = st.selectbox("Trafic", ["Tous", "Bots/UA suspects", "Humains probables"], label_visibility="collapsed")
    with fc3:
        url_filter = st.text_input("🔍 URL contient", "", placeholder="ex: /producten/", label_visibility="collapsed")
    with fc4:
        page_type_filter = st.multiselect("Type de page", ["Home", "Boutique", "Produit", "Review", "Blog", "Catégorie", "Asset", "Autre"], placeholder="Type de page", label_visibility="collapsed")

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
RANGE_FILTER = f"date_range_start <= '{end_date}' AND date_range_end >= '{start_date}'"

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
if HAS_HTTP_LOGS:
    df_daily = query(f"""
        SELECT
            date,
            COUNT(*) AS requests,
            SUM(edgeresponsebytes) AS bytes,
            SUM(CASE WHEN LOWER(COALESCE(cachestatus, '')) = 'hit' THEN 1 ELSE 0 END) AS cached_requests,
            SUM(CASE WHEN LOWER(COALESCE(cachestatus, '')) = 'hit' THEN edgeresponsebytes ELSE 0 END) AS cached_bytes,
            0 AS threats,
            COUNT(*) AS page_views,
            COUNT(DISTINCT clientip) AS uniques
        FROM cf_http_requests
        WHERE {DATE_FILTER}
        GROUP BY date
        ORDER BY date
    """)
    df_paths_raw = query(f"""
        SELECT clientrequestpath AS path, COUNT(*) AS total
        FROM cf_http_requests
        WHERE {DATE_FILTER}
        GROUP BY clientrequestpath
        ORDER BY total DESC
    """)
    df_ua = query(f"""
        SELECT clientrequestuseragent AS user_agent, COUNT(*) AS total
        FROM cf_http_requests
        WHERE {DATE_FILTER}
        GROUP BY clientrequestuseragent
        ORDER BY total DESC
    """)
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
    df_status = query(f"""
        SELECT edgeresponsestatus AS status_code, COUNT(*) AS total
        FROM cf_http_requests
        WHERE {DATE_FILTER}
        GROUP BY edgeresponsestatus
        ORDER BY total DESC
    """)
    df_cache = query(f"""
        SELECT cachestatus AS cache_status, COUNT(*) AS total
        FROM cf_http_requests
        WHERE {DATE_FILTER}
        GROUP BY cachestatus
        ORDER BY total DESC
    """)
    df_countries = query(f"""
        SELECT clientcountry AS country, COUNT(*) AS total
        FROM cf_http_requests
        WHERE {DATE_FILTER}
        GROUP BY clientcountry
        ORDER BY total DESC
    """)
    df_timings = query(f"""
        SELECT clientrequestpath AS path, AVG(response_time_ms) AS avg_ms, COUNT(*) AS hits
        FROM cf_http_requests
        WHERE {DATE_FILTER} AND response_time_ms IS NOT NULL
        GROUP BY clientrequestpath
        ORDER BY avg_ms DESC
    """)
else:
    df_daily = query(f"SELECT * FROM cf_requests_daily WHERE {DATE_FILTER} ORDER BY date")
    df_paths_raw = query(f"SELECT path, SUM(count) as total FROM cf_top_paths WHERE {RANGE_FILTER} GROUP BY path ORDER BY total DESC")
    df_ua = query(f"SELECT user_agent, SUM(count) as total FROM cf_user_agents WHERE {RANGE_FILTER} GROUP BY user_agent ORDER BY total DESC")
    df_ua_detail = df_ua.copy()
    df_ua_detail["unique_urls"] = None
    df_ua_detail["first_visit"] = None
    df_ua_detail["last_visit"] = None
    df_status = query(f"SELECT status_code, SUM(count) as total FROM cf_status_codes WHERE {RANGE_FILTER} GROUP BY status_code ORDER BY total DESC")
    df_cache = query(f"SELECT cache_status, SUM(count) as total FROM cf_cache_status WHERE {RANGE_FILTER} GROUP BY cache_status ORDER BY total DESC")
    df_countries = query(f"SELECT country, SUM(count) as total FROM cf_countries WHERE {RANGE_FILTER} GROUP BY country ORDER BY total DESC")
    df_timings = query(f"""
        SELECT path, SUM(avg_response_ms * samples) / SUM(samples) as avg_ms, SUM(samples) as hits
        FROM cf_path_timings WHERE {RANGE_FILTER} GROUP BY path ORDER BY avg_ms DESC
    """)

if df_daily.empty:
    st.info("Aucune donnée pour cette période.")
    st.stop()

# Enrich user agents
if not df_ua.empty:
    _info = df_ua["user_agent"].apply(lambda ua: pd.Series(extract_bot_info(ua)))
    df_ua["bot_name"]     = _info["name"]
    df_ua["bot_category"] = _info["category"]
    df_ua["dangerous"]    = _info["dangerous"]
    if not df_ua_detail.empty:
        _info_detail = df_ua_detail["user_agent"].apply(lambda ua: pd.Series(extract_bot_info(ua)))
        df_ua_detail["bot_name"]     = _info_detail["name"]
        df_ua_detail["bot_category"] = _info_detail["category"]
        df_ua_detail["dangerous"]    = _info_detail["dangerous"]
    if traffic_filter == "Bots/UA suspects":
        df_ua = df_ua[df_ua["bot_category"] != "Humain"]
        if not df_ua_detail.empty:
            df_ua_detail = df_ua_detail[df_ua_detail["bot_category"] != "Humain"]
    elif traffic_filter == "Humains probables":
        df_ua = df_ua[df_ua["bot_category"] == "Humain"]
        if not df_ua_detail.empty:
            df_ua_detail = df_ua_detail[df_ua_detail["bot_category"] == "Humain"]

# Enrich paths
if not df_paths_raw.empty:
    df_paths_raw["page_type"] = df_paths_raw["path"].apply(classify_path)
    df_paths = df_paths_raw.copy()
    if url_filter:
        df_paths = df_paths[df_paths["path"].str.contains(url_filter, case=False, na=False)]
    if page_type_filter:
        df_paths = df_paths[df_paths["page_type"].isin(page_type_filter)]
else:
    df_paths = df_paths_raw

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total_req = int(df_daily["requests"].sum())
total_cached = int(df_daily["cached_requests"].sum())
cache_pct = total_cached / total_req * 100 if total_req else 0
bot_hits = int(df_ua[df_ua["bot_category"] != "Humain"]["total"].sum()) if not df_ua.empty else 0
error_hits = int(df_status[df_status["status_code"] >= 400]["total"].sum()) if not df_status.empty else 0
error_pct = error_hits / total_req * 100 if total_req else 0
avg_ms = round(df_timings["avg_ms"].mean(), 0) if not df_timings.empty else None

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Hits totaux", f"{total_req:,}")
k2.metric("Bots & crawlers", f"{bot_hits:,}")
k3.metric("Erreurs 4xx/5xx", f"{error_pct:.1f}%")
k4.metric("Cache hit", f"{cache_pct:.1f}%")
k5.metric("URLs uniques", f"{len(df_paths):,}")
k6.metric("Temps réponse moy.", f"{int(avg_ms)} ms" if avg_ms else "—")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 1 — Traffic + Pays
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Vue globale trafic</div>', unsafe_allow_html=True)
t_left, t_right = st.columns([3, 1])

with t_left:
    df_daily["date"] = pd.to_datetime(df_daily["date"]).dt.date
    fig = px.area(df_daily, x="date", y="requests", color_discrete_sequence=["#38bdf8"])
    fig.update_traces(fill="tozeroy", line_color="#38bdf8", fillcolor="rgba(56,189,248,0.15)")
    fig.update_layout(**dark_layout(height=240, title=None, xaxis_title=None, yaxis_title="Hits"))
    st.plotly_chart(fig, use_container_width=True)

with t_right:
    st.markdown('<p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:6px;">Top pays</p>', unsafe_allow_html=True)
    if not df_countries.empty:
        st.dataframe(df_countries.head(8), use_container_width=True, hide_index=True, height=240)

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 2 — Bot Intelligence
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Bot Intelligence</div>', unsafe_allow_html=True)
b_left, b_mid, b_right = st.columns([1, 1, 2])

with b_left:
    if not df_ua.empty:
        bot_cat = df_ua.groupby("bot_category")["total"].sum().reset_index().sort_values("total", ascending=False)
        fig = px.pie(bot_cat, values="total", names="bot_category", color="bot_category",
                     color_discrete_map=BOT_COLORS, hole=0.55)
        fig.update_layout(**dark_layout(height=300, showlegend=True, margin=dict(l=0, r=0, t=0, b=0),
                                         legend=dict(orientation="v", font=dict(size=11))))
        fig.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
        st.plotly_chart(fig, use_container_width=True)

with b_mid:
    if not df_ua.empty:
        bot_cat2 = df_ua.groupby("bot_category")["total"].sum().reset_index().sort_values("total")
        fig = px.bar(bot_cat2, x="total", y="bot_category", orientation="h",
                     color="bot_category", color_discrete_map=BOT_COLORS)
        fig.update_layout(**dark_layout(height=300, showlegend=False, yaxis=dict(tickfont=dict(size=11))))
        st.plotly_chart(fig, use_container_width=True)

with b_right:
    if not df_ua_detail.empty:
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
            use_container_width=True, hide_index=True, height=300,
        )

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 2.5 — Crawl Timeline
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Crawl Timeline</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
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
else:
    st.info("Timeline disponible avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 3 — Top pages + Temps de réponse
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Top Pages & Performance</div>', unsafe_allow_html=True)
p_left, p_right = st.columns([2, 1])

with p_left:
    if not df_paths.empty:
        top20 = df_paths.head(20)
        fig = px.bar(top20, x="total", y="path", orientation="h",
                     color="page_type",
                     color_discrete_sequence=["#38bdf8", "#818cf8", "#f59e0b", "#10b981", "#ec4899", "#6b7280", "#f87171", "#a3e635"])
        fig.update_layout(**dark_layout(height=460, showlegend=True,
                                         yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11))))
        st.plotly_chart(fig, use_container_width=True)

with p_right:
    if not df_timings.empty:
        top_slow = df_timings.merge(df_paths[["path", "page_type"]], on="path", how="left").head(15)
        top_slow["avg_ms"] = top_slow["avg_ms"].round(0).astype(int)
        top_slow["path"] = top_slow["path"].str[:50]
        fig = px.bar(top_slow.sort_values("avg_ms"), x="avg_ms", y="path", orientation="h",
                     color="avg_ms", color_continuous_scale=["#10b981", "#f59e0b", "#ef4444"])
        fig.update_layout(**dark_layout(height=460, coloraxis_showscale=False,
                                         yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                                         xaxis_title="ms"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Temps de réponse disponibles après le prochain fetch.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 3.5 — Statistics by page category
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Statistics by Page Category</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
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
        df_category_summary["freq_per_day"] = (df_category_summary["hits"] / (df_daily["date"].nunique() if not df_daily.empty else 1)).round(2)
        st.dataframe(
            df_category_summary[["page_type", "hits", "unique_urls", "freq_per_day", "avg_ms"]]
            .rename(columns={"page_type": "Catégorie", "hits": "Hits", "unique_urls": "URLs uniques", "freq_per_day": "Fréq./jour", "avg_ms": "Temps moy. (ms)"}),
            use_container_width=True, hide_index=True, height=200,
        )
else:
    st.info("Statistiques par catégorie disponibles avec les vrais logs Log Explorer.")

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 4 — Status codes + Cache
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Santé Technique</div>', unsafe_allow_html=True)
h_left, h_right = st.columns(2)

with h_left:
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

with h_right:
    if not df_cache.empty:
        cache_colors = {"hit": "#10b981", "miss": "#ef4444", "dynamic": "#38bdf8", "expired": "#f59e0b", "none": "#6b7280"}
        fig = px.pie(df_cache, values="total", names="cache_status", color="cache_status",
                     color_discrete_map=cache_colors, hole=0.5)
        fig.update_layout(**dark_layout(height=260, title="Cache", showlegend=True,
                                         margin=dict(l=0, r=0, t=40, b=0),
                                         legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)))
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 5 — URL Explorer
# ---------------------------------------------------------------------------
st.markdown('<div class="section-label">Explorateur d\'URLs</div>', unsafe_allow_html=True)
if not df_paths.empty:
    explorer = df_paths.copy()
    explorer["share %"] = (explorer["total"] / explorer["total"].sum() * 100).round(1)
    if not df_timings.empty:
        explorer = explorer.merge(df_timings[["path", "avg_ms"]].rename(columns={"avg_ms": "avg ms"}), on="path", how="left")
        explorer["avg ms"] = explorer["avg ms"].fillna(0).astype(int)
    st.dataframe(explorer, use_container_width=True, hide_index=True, height=340)
    st.download_button("⬇ Exporter CSV", explorer.to_csv(index=False).encode("utf-8"), file_name="urls.csv", mime="text/csv")
