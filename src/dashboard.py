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
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cloudflare.duckdb"

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
    st.markdown("""
    <div style="font-size: 12px; color: #9ca3af; line-height: 1.8;">
        <div style="font-weight: 600; color: #6b7280; margin-bottom: 4px;">Pipeline</div>
        <div>1. fetch_cloudflare.py</div>
        <div>2. transform.py</div>
        <div>3. dashboard.py</div>
    </div>
    """, unsafe_allow_html=True)


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

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Requêtes", f"{total_requests:,}")
col2.metric("Pages vues", f"{total_pageviews:,}")
col3.metric("Visiteurs uniques", f"{total_uniques:,}")
col4.metric("Cache hit", f"{cache_ratio:.1f}%")
col5.metric("Jours", f"{len(df_daily)}")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_pages, tab_bots, tab_geo, tab_status, tab_cache = st.tabs([
    "Trafic", "Pages", "Bots & UA", "Pays", "Status codes", "Cache"
])

# --- Tab: Trafic ---
with tab_overview:
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1rem 0;">', unsafe_allow_html=True)

    df_daily["date"] = pd.to_datetime(df_daily["date"])

    fig = px.area(
        df_daily, x="date", y="requests",
        labels={"date": "", "requests": "Requêtes"},
        color_discrete_sequence=["#111827"],
    )
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        font=dict(family="Inter", size=12),
        title=dict(text="Requêtes par jour", font=dict(size=14)),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Cached vs non-cached
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df_daily["date"], y=df_daily["cached_requests"], name="Cached", marker_color="#d1d5db"))
    fig2.add_trace(go.Bar(x=df_daily["date"], y=df_daily["requests"] - df_daily["cached_requests"], name="Non-cached", marker_color="#111827"))
    fig2.update_layout(
        barmode="stack",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        font=dict(family="Inter", size=12),
        title=dict(text="Cache vs Non-cache par jour", font=dict(size=14)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig2, use_container_width=True)


# --- Tab: Pages ---
with tab_pages:
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1rem 0;">', unsafe_allow_html=True)

    df_paths = query(f"""
        SELECT path, SUM(count) as total
        FROM cf_top_paths
        WHERE {RANGE_FILTER}
        GROUP BY path
        ORDER BY total DESC
        LIMIT 30
    """)

    if not df_paths.empty:
        fig = px.bar(
            df_paths, x="total", y="path", orientation="h",
            labels={"total": "Requêtes", "path": ""},
            color_discrete_sequence=["#111827"],
        )
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=0, t=30, b=0),
            yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
            font=dict(family="Inter", size=12),
            title=dict(text="Top 30 pages les plus demandées", font=dict(size=14)),
            height=max(400, len(df_paths) * 22),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données de paths.")


# --- Tab: Bots & UA ---
with tab_bots:
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1rem 0;">', unsafe_allow_html=True)

    col_bots, col_ua = st.columns(2)

    with col_bots:
        st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Bots détectés</p>', unsafe_allow_html=True)
        df_bots = query(f"""
            SELECT user_agent, decision, country, SUM(count) as total
            FROM cf_bots
            WHERE {RANGE_FILTER}
            GROUP BY user_agent, decision, country
            ORDER BY total DESC
            LIMIT 20
        """)
        if not df_bots.empty:
            # Truncate long user agents for display
            df_bots["ua_short"] = df_bots["user_agent"].str[:60]
            st.dataframe(df_bots[["ua_short", "decision", "country", "total"]], use_container_width=True, hide_index=True)
        else:
            st.info("Pas de données bots.")

    with col_ua:
        st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Top User-Agents</p>', unsafe_allow_html=True)
        df_ua = query(f"""
            SELECT user_agent, SUM(count) as total
            FROM cf_user_agents
            WHERE {RANGE_FILTER}
            GROUP BY user_agent
            ORDER BY total DESC
            LIMIT 20
        """)
        if not df_ua.empty:
            df_ua["ua_short"] = df_ua["user_agent"].str[:80]
            st.dataframe(df_ua[["ua_short", "total"]], use_container_width=True, hide_index=True)
        else:
            st.info("Pas de données user-agents.")


# --- Tab: Pays ---
with tab_geo:
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1rem 0;">', unsafe_allow_html=True)

    df_countries = query(f"""
        SELECT country, SUM(count) as total
        FROM cf_countries
        WHERE {RANGE_FILTER}
        GROUP BY country
        ORDER BY total DESC
    """)

    if not df_countries.empty:
        col_map, col_table = st.columns([2, 1])

        with col_map:
            fig = px.choropleth(
                df_countries, locations="country", locationmode="country names",
                color="total", color_continuous_scale=["#f9fafb", "#111827"],
                labels={"total": "Requêtes", "country": "Pays"},
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                font=dict(family="Inter", size=12),
                title=dict(text="Requêtes par pays", font=dict(size=14)),
                geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#e5e7eb"),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.dataframe(df_countries, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("Pas de données pays.")


# --- Tab: Status codes ---
with tab_status:
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1rem 0;">', unsafe_allow_html=True)

    df_status = query(f"""
        SELECT status_code, SUM(count) as total
        FROM cf_status_codes
        WHERE {RANGE_FILTER}
        GROUP BY status_code
        ORDER BY total DESC
    """)

    if not df_status.empty:
        # Categorize
        df_status["category"] = df_status["status_code"].apply(
            lambda x: "2xx OK" if 200 <= x < 300 else "3xx Redirect" if 300 <= x < 400 else "4xx Client Error" if 400 <= x < 500 else "5xx Server Error" if 500 <= x < 600 else "Other"
        )

        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            df_cat = df_status.groupby("category")["total"].sum().reset_index()
            colors = {"2xx OK": "#111827", "3xx Redirect": "#6b7280", "4xx Client Error": "#ef4444", "5xx Server Error": "#dc2626", "Other": "#d1d5db"}
            fig = px.pie(
                df_cat, values="total", names="category",
                color="category", color_discrete_map=colors,
            )
            fig.update_layout(
                font=dict(family="Inter", size=12),
                title=dict(text="Répartition status codes", font=dict(size=14)),
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            df_status["status_code"] = df_status["status_code"].astype(str)
            st.dataframe(df_status[["status_code", "total", "category"]], use_container_width=True, hide_index=True)
    else:
        st.info("Pas de données status codes.")


# --- Tab: Cache ---
with tab_cache:
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1rem 0;">', unsafe_allow_html=True)

    df_cache = query(f"""
        SELECT cache_status, SUM(count) as total
        FROM cf_cache_status
        WHERE {RANGE_FILTER}
        GROUP BY cache_status
        ORDER BY total DESC
    """)

    if not df_cache.empty:
        colors_cache = {"hit": "#111827", "miss": "#ef4444", "dynamic": "#6b7280", "expired": "#f59e0b", "none": "#d1d5db"}

        fig = px.bar(
            df_cache, x="cache_status", y="total",
            labels={"cache_status": "Status", "total": "Requêtes"},
            color="cache_status", color_discrete_map=colors_cache,
        )
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=0, t=30, b=0),
            font=dict(family="Inter", size=12),
            title=dict(text="Répartition cache", font=dict(size=14)),
            showlegend=False,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_cache, use_container_width=True, hide_index=True)
    else:
        st.info("Pas de données cache.")
