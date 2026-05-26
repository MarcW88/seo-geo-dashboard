"""
dashboard.py — Log Analyzer Dashboard (6 views)

Usage:
    streamlit run src/dashboard.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
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
    border-bottom: 1px solid #334155;
    margin-bottom: 14px;
    margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)


def dark_layout(**kwargs):
    base = dict(
        plot_bgcolor="#1e293b",
        paper_bgcolor="#0f172a",
        font=dict(family="Inter", size=12, color="#94a3b8"),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=False, color="#334155", tickcolor="#334155"),
        yaxis=dict(showgrid=True, gridcolor="#334155", color="#94a3b8"),
    )
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Bot identification — comprehensive list including scanners
# ---------------------------------------------------------------------------
_BOTS = [
    # Search engines
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
    # AI bots
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
    # SEO tools
    ("ahrefsbot", "Ahrefsbot", "SEO tools", False),
    ("semrushbot", "SEMrushbot", "SEO tools", False),
    ("mj12bot", "Majestic MJ12Bot", "SEO tools", False),
    ("dotbot", "DotBot", "SEO tools", False),
    ("blexbot", "BLEXBot", "SEO tools", False),
    ("sitebulb", "Sitebulb", "SEO tools", False),
    ("serpstatbot", "SerpstatBot", "SEO tools", False),
    ("rogerbot", "Moz Rogerbot", "SEO tools", False),
    # Social networks
    ("facebookexternalhit", "Facebook External Hit", "Social networks", False),
    ("facebot", "Facebot (Facebook)", "Social networks", False),
    ("twitterbot", "TwitterBot", "Social networks", False),
    ("linkedinbot", "LinkedInBot", "Social networks", False),
    ("pinterestbot", "Pinterestbot", "Social networks", False),
    ("slackbot", "Slackbot", "Social networks", False),
    # Scanners / Security (dangerous)
    ("tlm-audit-scanner", "TLM Audit Scanner", "Scanners", True),
    ("masscan", "Masscan", "Scanners", True),
    ("zgrab", "ZGrab", "Scanners", True),
    ("nmap", "Nmap", "Scanners", True),
    ("nikto", "Nikto", "Scanners", True),
    ("sqlmap", "SQLMap", "Scanners", True),
    ("nuclei", "Nuclei", "Scanners", True),
    ("dirbuster", "DirBuster", "Scanners", True),
    ("gobuster", "GoBuster", "Scanners", True),
    ("shodan", "Shodan", "Scanners", True),
    ("censys", "Censys", "Scanners", True),
    ("expanse", "Expanse", "Scanners", True),
    ("internetmeasurement", "Internet Measurement", "Scanners", False),
    ("netcraft", "Netcraft", "Scanners", False),
    ("security", "Security Scanner", "Scanners", True),
    ("pentest", "Pentest Tool", "Scanners", True),
    ("vulnerability", "Vulnerability Scanner", "Scanners", True),
    # HTTP clients / scripts
    ("python-requests", "Python Requests", "HTTP clients", False),
    ("python/", "Python", "HTTP clients", False),
    ("aiohttp", "aiohttp", "HTTP clients", False),
    ("axios", "Axios", "HTTP clients", False),
    ("curl/", "cURL", "HTTP clients", False),
    ("wget/", "Wget", "HTTP clients", False),
    ("go-http-client", "Go HTTP Client", "HTTP clients", False),
    ("okhttp", "OkHttp", "HTTP clients", False),
    ("scrapy", "Scrapy", "HTTP clients", False),
    ("headlesschrome", "Headless Chrome", "HTTP clients", False),
    ("java/", "Java HTTP Client", "HTTP clients", False),
    ("libwww-perl", "Perl LWP", "HTTP clients", False),
    ("php/", "PHP HTTP Client", "HTTP clients", False),
]

# Build a flat SQL-compatible keyword list for bot detection
_BOT_SQL_KEYWORDS = [kw for kw, *_ in _BOTS]

def _bot_sql_filter() -> str:
    """Return a SQL fragment to identify bots via LIKE patterns."""
    conditions = " OR ".join([f"LOWER(clientrequestuseragent) LIKE '%{kw}%'" for kw in _BOT_SQL_KEYWORDS])
    return f"({conditions})"


def extract_bot_info(ua: str) -> dict:
    u = (ua or "").lower()
    for keyword, name, category, dangerous in _BOTS:
        if keyword in u:
            return {"name": name, "category": category, "dangerous": dangerous}
    return {"name": "Unknown", "category": "Unknown", "dangerous": False}


def is_bot_ua(ua: str) -> bool:
    u = (ua or "").lower()
    return any(kw in u for kw, *_ in _BOTS)


def classify_path(path: str) -> str:
    p = (path or "").lower()
    if p.endswith((".css", ".js", ".map")):
        return "CSS/JS"
    elif p.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif")):
        return "Images"
    elif p.endswith((".woff", ".woff2", ".ttf", ".eot")):
        return "Fonts"
    elif p.endswith(".xml") or "sitemap" in p:
        return "XML"
    elif "/api/" in p or p.startswith("/api"):
        return "API"
    elif p.endswith((".html", ".htm")):
        return "HTML"
    elif "?" in p or p.startswith(("/fr/", "/en/", "/nl/", "/de/")) or p in ("/", "/fr", "/en", "/nl"):
        return "HTML"
    else:
        return "Other"


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
        st.warning(f"GitHub API: HTTP {meta.status_code}")
        return
    download_url = meta.json().get("download_url", "")
    if not download_url:
        st.warning("No download_url in GitHub API response")
        return
    content = requests.get(download_url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if content.status_code == 200 and len(content.content) > 1000:
        DB_PATH.write_bytes(content.content)
    else:
        st.warning(f"Download failed: HTTP {content.status_code}, {len(content.content)} bytes")


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
    except Exception as e:
        st.error(f"Query error: {e}\n\n`{sql[:300]}`")
        return pd.DataFrame()


def table_exists(name: str) -> bool:
    df = query(f"SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_name = '{name}'")
    return not df.empty and int(df.iloc[0]["n"]) > 0


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
ensure_database()

HAS_HTTP_LOGS = table_exists("cf_http_requests")

# Last fetch timestamp
_last_fetch = ""
if HAS_HTTP_LOGS:
    _df_fetch = query("SELECT MAX(fetched_at) AS last FROM cf_http_requests")
    if not _df_fetch.empty and _df_fetch.iloc[0]["last"] is not None:
        _ts = pd.to_datetime(_df_fetch.iloc[0]["last"]).tz_localize("UTC") if pd.to_datetime(_df_fetch.iloc[0]["last"]).tzinfo is None else pd.to_datetime(_df_fetch.iloc[0]["last"])
        _paris = _ts.astimezone(pytz.timezone("Europe/Paris"))
        _last_fetch = _paris.strftime("%-d %b %Y à %H:%M")

st.markdown(f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:1rem;">
    <div style="display:flex;align-items:baseline;gap:12px;">
        <span style="font-size:1.4rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.5px;">Log Analyzer</span>
        <span style="font-size:12px;color:#64748b;font-family:monospace;">italiaanse-percolator.nl</span>
    </div>
    <div style="font-size:11px;color:#475569;text-align:right;">
        {"Dernière mise à jour : <span style='color:#94a3b8'>" + _last_fetch + "</span> &nbsp;·&nbsp;" if _last_fetch else ""}
        Prochaine maj : <span style='color:#94a3b8'>chaque jour à 05h00 (Paris)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Date range
if HAS_HTTP_LOGS:
    df_dates = query("SELECT MIN(date) as min_d, MAX(date) as max_d FROM cf_http_requests")
else:
    df_dates = pd.DataFrame()

if not df_dates.empty and df_dates.iloc[0]["min_d"] is not None:
    min_date = pd.to_datetime(df_dates.iloc[0]["min_d"]).date()
    max_date = pd.to_datetime(df_dates.iloc[0]["max_d"]).date()
else:
    min_date = max_date = None

# ---------------------------------------------------------------------------
# GlobalFiltersBar
# ---------------------------------------------------------------------------
fc1, fc2, fc3 = st.columns([3, 1, 1])
with fc1:
    if min_date:
        date_range = st.date_input(
            "Période",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date = end_date = None
with fc2:
    traffic_type = st.selectbox("Traffic type", ["All", "Bots only", "Users only"], label_visibility="collapsed")
with fc3:
    status_global = st.selectbox("Status", ["All", "2xx", "3xx", "4xx", "5xx"], label_visibility="collapsed")

if start_date is None:
    st.markdown("## Pas encore de données")
    db_exists = DB_PATH.exists()
    local_exists = LOCAL_PRIVATE_DB_PATH.exists()
    try:
        has_token = bool(st.secrets.get("GITHUB_TOKEN", ""))
    except Exception:
        has_token = False
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Diagnostic")
        st.write(f"{'✅' if db_exists else '❌'} DB : `{DB_PATH}`")
        st.write(f"{'✅' if local_exists else '❌'} DB data-repo : `{LOCAL_PRIVATE_DB_PATH}`")
        st.write(f"{'✅' if has_token else '❌'} GITHUB_TOKEN secret")
    with c2:
        if not has_token:
            st.code('GITHUB_TOKEN = "github_pat_xxx"\nPRIVATE_DB_URL = "https://api.github.com/repos/..."', language="toml")
        elif not db_exists:
            st.warning("Token présent mais DB non téléchargée. Vérifie les permissions.")
    st.stop()

# Build shared SQL filters
DATE_FILTER = f"date >= '{start_date}' AND date <= '{end_date}'"

BOT_SQL = _bot_sql_filter()

traffic_sql = ""
if traffic_type == "Bots only":
    traffic_sql = f"AND {BOT_SQL}"
elif traffic_type == "Users only":
    traffic_sql = f"AND NOT {BOT_SQL}"

status_sql = ""
if status_global == "2xx":
    status_sql = "AND edgeresponsestatus >= 200 AND edgeresponsestatus < 300"
elif status_global == "3xx":
    status_sql = "AND edgeresponsestatus >= 300 AND edgeresponsestatus < 400"
elif status_global == "4xx":
    status_sql = "AND edgeresponsestatus >= 400 AND edgeresponsestatus < 500"
elif status_global == "5xx":
    status_sql = "AND edgeresponsestatus >= 500 AND edgeresponsestatus < 600"

BASE_WHERE = f"WHERE {DATE_FILTER} {traffic_sql} {status_sql}"


# ===========================================================================
# VIEW 1 — Request Distribution
# ===========================================================================
st.markdown('<div class="section-label">Request Distribution</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    df_kpi = query(f"""
        SELECT
            COUNT(*) AS total_hits,
            COUNT(DISTINCT clientrequesturi) AS unique_urls,
            SUM(CASE WHEN {BOT_SQL} THEN 1 ELSE 0 END) AS bot_hits,
            SUM(CASE WHEN NOT {BOT_SQL} THEN 1 ELSE 0 END) AS user_hits
        FROM cf_http_requests
        {BASE_WHERE}
    """)
    df_codes = query(f"""
        SELECT
            CASE
                WHEN edgeresponsestatus >= 200 AND edgeresponsestatus < 300 THEN '2xx'
                WHEN edgeresponsestatus >= 300 AND edgeresponsestatus < 400 THEN '3xx'
                WHEN edgeresponsestatus >= 400 AND edgeresponsestatus < 500 THEN '4xx'
                WHEN edgeresponsestatus >= 500 THEN '5xx'
                ELSE 'other'
            END AS grp,
            edgeresponsestatus AS code,
            COUNT(*) AS hits
        FROM cf_http_requests
        {BASE_WHERE}
        GROUP BY grp, edgeresponsestatus
        ORDER BY grp, code
    """)
    df_bots_count = query(f"""
        SELECT COUNT(DISTINCT clientrequestuseragent) AS bots_detected
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_sql}
        AND {BOT_SQL}
    """)

    row = df_kpi.iloc[0] if not df_kpi.empty else {}
    total = int(row.get("total_hits", 0)) or 1
    bot_hits = int(row.get("bot_hits", 0))
    user_hits = int(row.get("user_hits", 0))
    unique_urls = int(row.get("unique_urls", 0))
    bots_detected = int(df_bots_count.iloc[0]["bots_detected"]) if not df_bots_count.empty else 0

    col_donut, col_kpis = st.columns([1, 2])

    with col_donut:
        fig_donut = go.Figure(go.Pie(
            labels=["Users", "Bots"],
            values=[user_hits, bot_hits],
            hole=0.6,
            marker=dict(colors=["#38bdf8", "#f59e0b"]),
            textinfo="none",
        ))
        fig_donut.update_layout(
            **dark_layout(height=200, margin=dict(l=0, r=0, t=10, b=10)),
            showlegend=True,
            legend=dict(
                orientation="v", x=1, y=0.5,
                font=dict(color="#94a3b8", size=12),
                bgcolor="rgba(0,0,0,0)",
            ),
            annotations=[dict(
                text=f"<b>{total:,}</b>",
                x=0.5, y=0.5,
                font=dict(size=20, color="#f1f5f9"),
                showarrow=False,
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown(
            f'<div style="text-align:center;font-size:12px;color:#94a3b8;">Users <b style="color:#38bdf8">{user_hits:,}</b> &nbsp;|&nbsp; Bots <b style="color:#f59e0b">{bot_hits:,}</b></div>',
            unsafe_allow_html=True,
        )

    with col_kpis:
        k1, k2 = st.columns(2)
        k1.metric("Unique URLs", f"{unique_urls:,}")
        k2.metric("Bots detected", f"{bots_detected:,}")

        if not df_codes.empty:
            st.markdown("**Response codes**")
            STATUS_COLORS = {"2xx": "#22c55e", "3xx": "#38bdf8", "4xx": "#f59e0b", "5xx": "#ef4444", "other": "#64748b"}
            for grp in ["2xx", "3xx", "4xx", "5xx"]:
                grp_df = df_codes[df_codes["grp"] == grp].sort_values("hits", ascending=False)
                if grp_df.empty:
                    continue
                badges = " ".join([
                    f'<span style="background:{STATUS_COLORS.get(grp,"#64748b")}22;border:1px solid {STATUS_COLORS.get(grp,"#64748b")};border-radius:4px;padding:2px 8px;font-size:11px;color:{STATUS_COLORS.get(grp,"#94a3b8")};margin-right:4px;">'
                    f'<b>{int(r["code"])}</b> {int(r["hits"]):,}</span>'
                    for _, r in grp_df.iterrows()
                ])
                st.markdown(badges, unsafe_allow_html=True)

st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)


# ===========================================================================
# VIEW 2 — Bot activity
# ===========================================================================
st.markdown('<div class="section-label">Bot activity</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    df_ua = query(f"""
        SELECT
            clientrequestuseragent AS ua,
            COUNT(*) AS hits,
            COUNT(DISTINCT clientrequesturi) AS unique_urls,
            MIN(edgestarttimestamp) AS first_seen,
            MAX(edgestarttimestamp) AS last_seen
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_sql}
        AND {BOT_SQL}
        GROUP BY clientrequestuseragent
        ORDER BY hits DESC
    """)

    if not df_ua.empty:
        info = df_ua["ua"].apply(lambda u: pd.Series(extract_bot_info(u)))
        df_ua["Bot"] = info["name"]
        df_ua["Category"] = info["category"]
        df_ua["Dangerous"] = info["dangerous"]

        bot_agg = (
            df_ua.groupby(["Bot", "Category", "Dangerous"])
            .agg(Hits=("hits", "sum"), unique_urls=("unique_urls", "sum"), first_seen=("first_seen", "min"), last_seen=("last_seen", "max"))
            .reset_index().sort_values("Hits", ascending=False)
        )
        total_bot_hits = bot_agg["Hits"].sum() or 1
        bot_agg["% of total"] = (bot_agg["Hits"] / total_bot_hits * 100).round(1).astype(str) + "%"
        bot_agg["First seen"] = pd.to_datetime(bot_agg["first_seen"]).dt.strftime("%d/%m/%y %H:%M")
        bot_agg["Last seen"] = pd.to_datetime(bot_agg["last_seen"]).dt.strftime("%d/%m/%y %H:%M")
        bot_agg["⚠"] = bot_agg["Dangerous"].apply(lambda x: "🔴" if x else "")

        st.dataframe(
            bot_agg[["Bot", "Category", "Hits", "% of total", "unique_urls", "First seen", "Last seen", "⚠"]]
            .rename(columns={"unique_urls": "Unique URLs"}),
            use_container_width=True,
            hide_index=True,
            height=350,
        )
    else:
        st.info("No bots detected for the selected period.")

st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)


# ===========================================================================
# VIEW 3 — Crawl timeline
# ===========================================================================
st.markdown('<div class="section-label">Crawl timeline</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    tc1, tc2 = st.columns([1, 1])
    with tc1:
        group_by = st.selectbox("Group by (timeline)", ["day", "week"], label_visibility="collapsed")
    with tc2:
        timeline_view = st.selectbox("View (timeline)", ["Absolute", "Relative (%)"], label_visibility="collapsed")

    trunc = "DATE(edgestarttimestamp)" if group_by == "day" else "DATE_TRUNC('week', edgestarttimestamp)"
    df_tl = query(f"""
        SELECT
            {trunc} AS dt,
            CASE
                WHEN NOT {BOT_SQL} THEN 'Users'
                WHEN LOWER(clientrequestuseragent) LIKE '%googlebot%' OR LOWER(clientrequestuseragent) LIKE '%bingbot%' OR LOWER(clientrequestuseragent) LIKE '%yandex%' OR LOWER(clientrequestuseragent) LIKE '%baidu%' THEN 'Search engines'
                WHEN LOWER(clientrequestuseragent) LIKE '%gptbot%' OR LOWER(clientrequestuseragent) LIKE '%claude%' OR LOWER(clientrequestuseragent) LIKE '%perplexity%' OR LOWER(clientrequestuseragent) LIKE '%anthropic%' THEN 'AI bots'
                WHEN LOWER(clientrequestuseragent) LIKE '%ahrefs%' OR LOWER(clientrequestuseragent) LIKE '%semrush%' OR LOWER(clientrequestuseragent) LIKE '%mj12%' THEN 'SEO tools'
                WHEN LOWER(clientrequestuseragent) LIKE '%facebook%' OR LOWER(clientrequestuseragent) LIKE '%twitter%' OR LOWER(clientrequestuseragent) LIKE '%linkedin%' THEN 'Social'
                ELSE 'Other bots'
            END AS category,
            COUNT(*) AS hits
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_sql}
        GROUP BY {trunc}, category
        ORDER BY dt
    """)

    if not df_tl.empty:
        df_tl["dt"] = pd.to_datetime(df_tl["dt"])
        cat_order = ["Users", "Search engines", "AI bots", "SEO tools", "Social", "Other bots"]
        cat_colors = {
            "Users": "#38bdf8",
            "Search engines": "#22c55e",
            "AI bots": "#a78bfa",
            "SEO tools": "#f59e0b",
            "Social": "#ec4899",
            "Other bots": "#64748b",
        }
        if timeline_view == "Relative (%)":
            pivot = df_tl.pivot_table(index="dt", columns="category", values="hits", aggfunc="sum", fill_value=0)
            pivot = pivot.div(pivot.sum(axis=1), axis=0) * 100
            df_tl_plot = pivot.reset_index().melt(id_vars="dt", var_name="category", value_name="hits")
            yaxis_label = "% of hits"
        else:
            df_tl_plot = df_tl
            yaxis_label = "Hits"

        fig_tl = px.bar(
            df_tl_plot, x="dt", y="hits", color="category",
            color_discrete_map=cat_colors,
            category_orders={"category": cat_order},
            labels={"hits": yaxis_label, "dt": "Date", "category": ""},
        )
        fig_tl.update_layout(**dark_layout(
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
            yaxis_title=yaxis_label,
        ))
        st.plotly_chart(fig_tl, use_container_width=True)
    else:
        st.info("No data for timeline.")

st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)


# ===========================================================================
# VIEW 4 — Statistics by page category
# ===========================================================================
st.markdown('<div class="section-label">Statistics by page category</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        level_filter = st.selectbox("Level (category)", ["1st level", "2nd level"], label_visibility="collapsed")
    with sc2:
        cat_search = st.text_input("Search category...", "", label_visibility="collapsed")

    def get_category(path: str, level: str) -> str:
        parts = (path or "").split("/")
        parts = [p for p in parts if p]
        if level == "1st level":
            return "/" + parts[0] if parts else "/"
        else:
            return "/" + "/".join(parts[:2]) if len(parts) >= 2 else ("/" + parts[0] if parts else "/")

    df_cat_raw = query(f"""
        SELECT
            clientrequestpath AS path,
            COUNT(*) AS hits,
            COUNT(DISTINCT clientrequestpath) AS unique_urls,
            AVG(response_time_ms) AS avg_ms
        FROM cf_http_requests
        {BASE_WHERE}
        GROUP BY clientrequestpath
    """)

    if not df_cat_raw.empty:
        days_range = max((end_date - start_date).days, 1)
        df_cat_raw["category"] = df_cat_raw["path"].apply(lambda p: get_category(p, level_filter))
        if cat_search:
            df_cat_raw = df_cat_raw[df_cat_raw["category"].str.contains(cat_search, case=False, na=False)]

        cat_summary = (
            df_cat_raw.groupby("category")
            .agg(total_hits=("hits", "sum"), unique_urls=("unique_urls", "sum"), avg_ms=("avg_ms", "mean"))
            .reset_index().sort_values("total_hits", ascending=False)
        )
        cat_summary["hits_per_day"] = (cat_summary["total_hits"] / days_range).round(1)
        cat_summary["avg_ms"] = cat_summary["avg_ms"].fillna(0).round(0).astype(int)
        cat_summary["period"] = f"{start_date} - {end_date}"

        col_bars, col_table = st.columns([1, 2])

        with col_bars:
            fig_bar = px.bar(
                cat_summary.head(10).sort_values("total_hits"),
                x="total_hits", y="category", orientation="h",
                color="avg_ms",
                color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
                labels={"total_hits": "Hits", "category": "", "avg_ms": "Avg ms"},
            )
            fig_bar.update_layout(**dark_layout(height=300, margin=dict(l=0, r=0, t=10, b=0)))
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_table:
            st.dataframe(
                cat_summary[["category", "total_hits", "unique_urls", "hits_per_day", "avg_ms", "period"]]
                .rename(columns={
                    "category": "Category", "total_hits": "Total hits",
                    "unique_urls": "Unique URLs", "hits_per_day": "Hits/day",
                    "avg_ms": "Avg duration (ms)", "period": "Period",
                }),
                use_container_width=True,
                hide_index=True,
                height=300,
            )
    else:
        st.info("No data for category stats.")

st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)


# ===========================================================================
# VIEW 5 — Crawled pages
# ===========================================================================
st.markdown('<div class="section-label">Crawled pages</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    cp1, cp2 = st.columns([2, 1])
    with cp1:
        cp_url = st.text_input("Filter by URL...", "", label_visibility="collapsed")
    with cp2:
        cp_bot = st.selectbox("Bot (pages)", ["All"] + sorted(set(b[1] for b in _BOTS)), label_visibility="collapsed")

    cp_url_sql = f"AND clientrequesturi LIKE '%{cp_url}%'" if cp_url else ""
    cp_bot_sql = f"AND LOWER(clientrequestuseragent) LIKE '%{cp_bot.lower()}%'" if cp_bot != "All" else ""

    df_pages = query(f"""
        SELECT
            clientrequesturi AS url,
            COUNT(*) AS total_hits,
            COUNT(DISTINCT clientrequestuseragent) AS unique_bots,
            MAX(edgestarttimestamp) AS last_crawl
        FROM cf_http_requests
        WHERE {DATE_FILTER} {status_sql}
        AND {BOT_SQL}
        {cp_url_sql} {cp_bot_sql}
        GROUP BY clientrequesturi
        ORDER BY last_crawl DESC
        LIMIT 500
    """)

    if not df_pages.empty:
        df_pages["last_crawl"] = pd.to_datetime(df_pages["last_crawl"]).dt.strftime("%d/%m/%y %H:%M")
        st.caption(f"{len(df_pages):,} crawled pages")
        st.dataframe(
            df_pages.rename(columns={"url": "URL", "total_hits": "Total hits", "unique_bots": "Unique bots", "last_crawl": "Last crawl"}),
            use_container_width=True, hide_index=True, height=380,
        )
    else:
        st.info("No crawled pages for the selected period.")

st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)


# ===========================================================================
# VIEW 6 — Request details
# ===========================================================================
st.markdown('<div class="section-label">Request details</div>', unsafe_allow_html=True)

if HAS_HTTP_LOGS:
    rd1, rd2, rd3 = st.columns([2, 1, 1])
    with rd1:
        rd_url = st.text_input("URL contains...", "", label_visibility="collapsed")
    with rd2:
        rd_bot = st.selectbox("Bot (details)", ["All"] + sorted(set(b[1] for b in _BOTS)), label_visibility="collapsed")
    with rd3:
        rd_status = st.selectbox("Status (details)", ["All", "2xx", "3xx", "4xx", "5xx"], label_visibility="collapsed")

    # Resource type toggles
    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    with rc1:
        t_html = st.checkbox("HTML", value=True, key="t_html")
    with rc2:
        t_css = st.checkbox("CSS/JS", value=False, key="t_css")
    with rc3:
        t_img = st.checkbox("Images", value=False, key="t_img")
    with rc4:
        t_xml = st.checkbox("XML", value=False, key="t_xml")
    with rc5:
        t_font = st.checkbox("Fonts", value=False, key="t_font")

    rd_url_sql = f"AND clientrequesturi LIKE '%{rd_url}%'" if rd_url else ""
    rd_bot_sql = f"AND LOWER(clientrequestuseragent) LIKE '%{rd_bot.lower()}%'" if rd_bot != "All" else ""
    if rd_status == "2xx":
        rd_status_sql = "AND edgeresponsestatus >= 200 AND edgeresponsestatus < 300"
    elif rd_status == "3xx":
        rd_status_sql = "AND edgeresponsestatus >= 300 AND edgeresponsestatus < 400"
    elif rd_status == "4xx":
        rd_status_sql = "AND edgeresponsestatus >= 400 AND edgeresponsestatus < 500"
    elif rd_status == "5xx":
        rd_status_sql = "AND edgeresponsestatus >= 500"
    else:
        rd_status_sql = ""

    resource_conds = []
    if t_html:
        resource_conds.append("(clientrequestpath NOT LIKE '%.%' OR clientrequestpath LIKE '%.html' OR clientrequestpath LIKE '%.htm')")
    if t_css:
        resource_conds.append("(clientrequestpath LIKE '%.css' OR clientrequestpath LIKE '%.js')")
    if t_img:
        resource_conds.append("(clientrequestpath LIKE '%.png' OR clientrequestpath LIKE '%.jpg' OR clientrequestpath LIKE '%.jpeg' OR clientrequestpath LIKE '%.gif' OR clientrequestpath LIKE '%.svg' OR clientrequestpath LIKE '%.ico' OR clientrequestpath LIKE '%.webp')")
    if t_xml:
        resource_conds.append("clientrequestpath LIKE '%.xml'")
    if t_font:
        resource_conds.append("(clientrequestpath LIKE '%.woff' OR clientrequestpath LIKE '%.woff2' OR clientrequestpath LIKE '%.ttf' OR clientrequestpath LIKE '%.eot')")
    rd_res_sql = "AND (" + " OR ".join(resource_conds) + ")" if resource_conds else ""

    df_req = query(f"""
        SELECT
            edgestarttimestamp AS dt,
            clientrequesturi AS url,
            clientrequestuseragent AS ua,
            edgeresponsestatus AS status,
            response_time_ms AS duration_ms
        FROM cf_http_requests
        WHERE {DATE_FILTER} {traffic_sql} {rd_status_sql} {rd_url_sql} {rd_bot_sql} {rd_res_sql}
        ORDER BY edgestarttimestamp DESC
        LIMIT 1000
    """)

    if not df_req.empty:
        df_req["Date/Time"] = pd.to_datetime(df_req["dt"]).dt.strftime("%d/%m/%y %H:%M:%S")
        df_req["Bot"] = df_req["ua"].apply(lambda u: extract_bot_info(u)["name"])
        df_req["Category"] = df_req["url"].apply(classify_path)
        df_req["duration_ms"] = df_req["duration_ms"].fillna(0).round(0).astype(int)
        st.caption(f"Showing up to 1,000 results")
        st.dataframe(
            df_req[["Date/Time", "url", "Bot", "Category", "status", "duration_ms"]]
            .rename(columns={"url": "URL", "status": "Status", "duration_ms": "Duration (ms)"}),
            use_container_width=True,
            hide_index=True,
            height=480,
        )
    else:
        st.info("No requests match the current filters.")

