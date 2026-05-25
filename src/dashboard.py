"""
dashboard.py — Dashboard SEO/GEO Streamlit + DuckDB + Plotly

Usage:
    streamlit run src/dashboard.py
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cloudflare.duckdb"
LOCAL_PRIVATE_DB_PATH = Path(__file__).resolve().parent.parent.parent / "seo-geo-dashboard-data" / "data" / "cloudflare.duckdb"
PRIVATE_DB_URL = "https://api.github.com/repos/MarcW88/seo-geo-dashboard-data/contents/data/cloudflare.duckdb"

st.set_page_config(
    page_title="SEO/GEO Dashboard — italiaanse-percolator.nl",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Minimal CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { padding: 2rem 2rem; max-width: 1200px; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stMetric"] {
        background: #fafafa; padding: 1rem; border-radius: 8px; border: 1px solid #f0f0f0;
    }
    [data-testid="stMetricLabel"] { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; }
    [data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 600; color: #111827; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #e5e7eb; }
    .stTabs [data-baseweb="tab"] {
        height: 42px; font-size: 14px; font-weight: 500; color: #6b7280;
        border: none; border-bottom: 2px solid transparent; border-radius: 0; padding: 0 18px; background: transparent;
    }
    .stTabs [aria-selected="true"] { color: #111827 !important; border-bottom: 2px solid #111827 !important; background: transparent !important; }
    [data-testid="stSidebar"] { background: #fafafa; border-right: 1px solid #f0f0f0; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------
def ensure_database():
    """Rend la DB disponible localement ou via GitHub token."""
    if DB_PATH.exists():
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

    # Step 1 : récupère le download_url via l'API Contents
    meta = requests.get(
        db_url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
    )
    if meta.status_code != 200:
        return
    download_url = meta.json().get("download_url", "")
    if not download_url:
        return

    # Step 2 : télécharge le fichier binaire via le download_url signé
    content = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if content.status_code == 200 and len(content.content) > 1000:
        DB_PATH.write_bytes(content.content)


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
        st.error(f"Erreur SQL: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Init — DB must be ready before any query
# ---------------------------------------------------------------------------
ensure_database()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <div style="font-size: 17px; font-weight: 600; color: #111827;">SEO/GEO Dashboard</div>
        <div style="font-size: 13px; color: #6b7280;">italiaanse-percolator.nl</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Date range filter
    df_dates = query("SELECT MIN(date) as min_d, MAX(date) as max_d FROM cf_requests_daily")
    if not df_dates.empty and df_dates.iloc[0]["min_d"] is not None:
        min_date = pd.to_datetime(df_dates.iloc[0]["min_d"]).date()
        max_date = pd.to_datetime(df_dates.iloc[0]["max_d"]).date()
        date_range = st.date_input("Période", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date, end_date = None, None
        st.warning("Pas de données. Lance le fetch d'abord.")

    st.markdown("---")
    traffic_filter = st.radio("Trafic", ["Tous", "Bots/UA suspects", "Humains probables"])
    url_filter = st.text_input("URL contient", "")
    page_type_filter = st.multiselect(
        "Type de page",
        ["Home", "Boutique", "Produit", "Review", "Blog", "Catégorie", "Autre"],
        default=[],
    )


# ---------------------------------------------------------------------------
# No data guard
# ---------------------------------------------------------------------------
if start_date is None:
    st.markdown("""
    <div style="padding: 3rem; text-align: center;">
        <h2 style="color: #111827; font-weight: 600;">Pas encore de données</h2>
        <p style="color: #6b7280; font-size: 14px; margin-top: 8px;">
            Lance le pipeline pour commencer :
        </p>
        <code style="display: block; margin: 1rem auto; padding: 12px; background: #f9fafb; border-radius: 6px; max-width: 400px;">
            python -m src.fetch_cloudflare<br>
            python -m src.transform
        </code>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

DATE_FILTER = f"date >= '{start_date}' AND date <= '{end_date}'"
RANGE_FILTER = f"date_range_start >= '{start_date}' AND date_range_end <= '{end_date}'"


def classify_path(path: str) -> str:
    path = path or "/"
    if path == "/" or path == "/index.html":
        return "Home"
    if "boutique" in path:
        return "Boutique"
    if "/producten/" in path or "/produits/" in path:
        return "Produit"
    if "review" in path:
        return "Review"
    if path.startswith("/blog") or "/gidsen/" in path or "/koopgids/" in path:
        return "Blog"
    if "/categories/" in path or "/marques/" in path:
        return "Catégorie"
    return "Autre"


def is_bot_user_agent(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    bot_terms = ["bot", "crawl", "spider", "slurp", "bingpreview", "facebookexternalhit", "mediapartners", "inspectiontool"]
    return any(term in ua for term in bot_terms)


def apply_path_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "path" not in df.columns:
        return df
    filtered = df.copy()
    filtered["page_type"] = filtered["path"].apply(classify_path)
    if url_filter:
        filtered = filtered[filtered["path"].str.contains(url_filter, case=False, na=False)]
    if page_type_filter:
        filtered = filtered[filtered["page_type"].isin(page_type_filter)]
    return filtered


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
df_daily = query(f"SELECT * FROM cf_requests_daily WHERE {DATE_FILTER} ORDER BY date")

if df_daily.empty:
    st.info("Aucune donnée pour cette période.")
    st.stop()

total_requests = int(df_daily["requests"].sum())
total_cached = int(df_daily["cached_requests"].sum())
total_pageviews = int(df_daily["page_views"].sum())
total_uniques = int(df_daily["uniques"].sum())
cache_ratio = (total_cached / total_requests * 100) if total_requests else 0

df_paths = query(f"""
    SELECT path, SUM(count) as total
    FROM cf_top_paths
    WHERE {RANGE_FILTER}
    GROUP BY path
    ORDER BY total DESC
""")
df_paths = apply_path_filters(df_paths)

df_ua = query(f"""
    SELECT user_agent, SUM(count) as total
    FROM cf_user_agents
    WHERE {RANGE_FILTER}
    GROUP BY user_agent
    ORDER BY total DESC
""")
if not df_ua.empty:
    df_ua["is_bot"] = df_ua["user_agent"].apply(is_bot_user_agent)
    if traffic_filter == "Bots/UA suspects":
        df_ua = df_ua[df_ua["is_bot"]]
    elif traffic_filter == "Humains probables":
        df_ua = df_ua[~df_ua["is_bot"]]

df_status = query(f"""
    SELECT status_code, SUM(count) as total
    FROM cf_status_codes
    WHERE {RANGE_FILTER}
    GROUP BY status_code
    ORDER BY total DESC
""")

df_cache = query(f"""
    SELECT cache_status, SUM(count) as total
    FROM cf_cache_status
    WHERE {RANGE_FILTER}
    GROUP BY cache_status
    ORDER BY total DESC
""")

df_countries = query(f"""
    SELECT country, SUM(count) as total
    FROM cf_countries
    WHERE {RANGE_FILTER}
    GROUP BY country
    ORDER BY total DESC
""")

error_hits = 0
if not df_status.empty:
    error_hits = int(df_status[df_status["status_code"] >= 400]["total"].sum())
error_rate = (error_hits / total_requests * 100) if total_requests else 0
bot_hits = int(df_ua[df_ua["is_bot"]]["total"].sum()) if not df_ua.empty and "is_bot" in df_ua else 0

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <h1 style="font-size: 1.8rem; font-weight: 650; color: #111827; margin: 0;">Log analyzer mini-sites</h1>
    <p style="font-size: 14px; color: #6b7280; margin: 6px 0 0 0;">Crawl SEO, qualité technique et sanity check trafic pour italiaanse-percolator.nl.</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Hits totaux", f"{total_requests:,}")
col2.metric("Hits bots/UA", f"{bot_hits:,}")
col3.metric("Erreurs 4xx/5xx", f"{error_rate:.1f}%")
col4.metric("Cache hit", f"{cache_ratio:.1f}%")
col5.metric("URLs uniques", f"{len(df_paths):,}")
col6.metric("Pays", f"{len(df_countries):,}")

st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

st.subheader("Vue globale trafic")
overview_left, overview_right = st.columns([2, 1])
with overview_left:
    df_daily["date"] = pd.to_datetime(df_daily["date"])
    fig = px.area(
        df_daily,
        x="date",
        y="requests",
        labels={"date": "", "requests": "Requêtes"},
        color_discrete_sequence=["#111827"],
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=0, r=0, t=25, b=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        font=dict(family="Inter", size=12),
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)
with overview_right:
    if not df_countries.empty:
        st.caption("Top pays")
        st.dataframe(df_countries.head(8), use_container_width=True, hide_index=True, height=260)

st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

st.subheader("Crawl SEO / bots")
crawl_left, crawl_right = st.columns([2, 1])
with crawl_left:
    if not df_paths.empty:
        top_paths = df_paths.head(20)
        fig = px.bar(
            top_paths,
            x="total",
            y="path",
            orientation="h",
            labels={"total": "Hits", "path": ""},
            color_discrete_sequence=["#111827"],
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=0, r=0, t=25, b=0),
            yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
            font=dict(family="Inter", size=12),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données URL pour cette période.")
with crawl_right:
    st.caption("Top user-agents")
    if not df_ua.empty:
        df_ua_display = df_ua.copy()
        df_ua_display["type"] = df_ua_display["is_bot"].map({True: "Bot/suspect", False: "Humain probable"})
        df_ua_display["user_agent"] = df_ua_display["user_agent"].str[:70]
        st.dataframe(df_ua_display[["user_agent", "type", "total"]].head(12), use_container_width=True, hide_index=True, height=420)
    else:
        st.info("Pas de données user-agent.")

st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

st.subheader("Erreurs & performance technique")
tech_left, tech_mid, tech_right = st.columns([1, 1, 1])
with tech_left:
    if not df_status.empty:
        df_status_plot = df_status.copy()
        df_status_plot["category"] = df_status_plot["status_code"].apply(
            lambda x: "2xx" if 200 <= x < 300 else "3xx" if 300 <= x < 400 else "4xx" if 400 <= x < 500 else "5xx" if 500 <= x < 600 else "Other"
        )
        fig = px.bar(
            df_status_plot,
            x="status_code",
            y="total",
            color="category",
            labels={"status_code": "Code", "total": "Hits"},
            color_discrete_map={"2xx": "#111827", "3xx": "#6b7280", "4xx": "#ef4444", "5xx": "#dc2626", "Other": "#d1d5db"},
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=25, b=0), height=280, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
with tech_mid:
    if not df_cache.empty:
        colors_cache = {"hit": "#111827", "miss": "#ef4444", "dynamic": "#6b7280", "expired": "#f59e0b", "none": "#d1d5db"}
        fig = px.pie(df_cache, values="total", names="cache_status", color="cache_status", color_discrete_map=colors_cache)
        fig.update_layout(font=dict(family="Inter", size=12), margin=dict(l=0, r=0, t=25, b=0), height=280)
        st.plotly_chart(fig, use_container_width=True)
with tech_right:
    st.caption("Status codes")
    if not df_status.empty:
        st.dataframe(df_status, use_container_width=True, hide_index=True, height=280)

st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

st.subheader("Exploration d'URLs")
if not df_paths.empty:
    explorer = df_paths.copy()
    explorer["share"] = explorer["total"] / explorer["total"].sum() * 100
    explorer = explorer[["path", "page_type", "total", "share"]]
    st.dataframe(explorer, use_container_width=True, hide_index=True, height=320)
    st.download_button(
        "Exporter les URLs filtrées",
        explorer.to_csv(index=False).encode("utf-8"),
        file_name="filtered_urls.csv",
        mime="text/csv",
    )
else:
    st.info("Aucune URL à explorer.")
