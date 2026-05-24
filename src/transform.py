"""
transform.py — Transforme les données brutes Cloudflare JSON en tables DuckDB.

Usage:
    python -m src.transform                     # Transforme le fichier du jour
    python -m src.transform --file data/raw/cloudflare/2026-05-24.json
    python -m src.transform --all               # Transforme tous les fichiers raw
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "cloudflare"
DB_PATH = DATA_DIR / "cloudflare.duckdb"


def get_db() -> duckdb.DuckDBPyConnection:
    """Ouvre/crée la base DuckDB et initialise les tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    _create_tables(conn)
    return conn


def _create_tables(conn: duckdb.DuckDBPyConnection):
    """Crée les tables si elles n'existent pas."""

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_requests_daily (
            date        DATE,
            requests    BIGINT,
            bytes       BIGINT,
            cached_requests BIGINT,
            cached_bytes    BIGINT,
            threats     BIGINT,
            page_views  BIGINT,
            uniques     BIGINT,
            fetched_at  TIMESTAMP,
            PRIMARY KEY (date)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_top_paths (
            date_range_start DATE,
            date_range_end   DATE,
            path             VARCHAR,
            count            BIGINT,
            fetched_at       TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_user_agents (
            date_range_start DATE,
            date_range_end   DATE,
            user_agent       VARCHAR,
            count            BIGINT,
            fetched_at       TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_countries (
            date_range_start DATE,
            date_range_end   DATE,
            country          VARCHAR,
            count            BIGINT,
            fetched_at       TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_status_codes (
            date_range_start DATE,
            date_range_end   DATE,
            status_code      INTEGER,
            count            BIGINT,
            fetched_at       TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_cache_status (
            date_range_start DATE,
            date_range_end   DATE,
            cache_status     VARCHAR,
            count            BIGINT,
            fetched_at       TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cf_bots (
            date_range_start DATE,
            date_range_end   DATE,
            user_agent       VARCHAR,
            decision         VARCHAR,
            country          VARCHAR,
            count            BIGINT,
            fetched_at       TIMESTAMP
        )
    """)


def transform_file(filepath: Path, conn: duckdb.DuckDBPyConnection):
    """Transforme un fichier JSON brut en lignes DuckDB."""
    print(f"📄 Transformation: {filepath.name}")

    data = json.loads(filepath.read_text())
    meta = data.get("meta", {})
    since = meta.get("since", "")
    until = meta.get("until", "")
    fetched_at = meta.get("fetched_at", datetime.now(timezone.utc).isoformat())

    # --- cf_requests_daily ---
    for row in data.get("daily", []):
        date = row.get("dimensions", {}).get("date", "")
        s = row.get("sum", {})
        u = row.get("uniq", {})
        conn.execute("""
            INSERT OR REPLACE INTO cf_requests_daily
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            date,
            s.get("requests", 0),
            s.get("bytes", 0),
            s.get("cachedRequests", 0),
            s.get("cachedBytes", 0),
            s.get("threats", 0),
            s.get("pageViews", 0),
            u.get("uniques", 0),
            fetched_at,
        ])

    # --- cf_top_paths ---
    # Supprimer les anciennes données pour cette plage
    conn.execute("DELETE FROM cf_top_paths WHERE date_range_start = ? AND date_range_end = ?", [since, until])
    for row in data.get("top_paths", []):
        path = row.get("dimensions", {}).get("clientRequestPath", "")
        count = row.get("count", 0)
        conn.execute("INSERT INTO cf_top_paths VALUES (?, ?, ?, ?, ?)", [since, until, path, count, fetched_at])

    # --- cf_user_agents ---
    conn.execute("DELETE FROM cf_user_agents WHERE date_range_start = ? AND date_range_end = ?", [since, until])
    for row in data.get("top_user_agents", []):
        ua = row.get("dimensions", {}).get("userAgent", "")
        count = row.get("count", 0)
        conn.execute("INSERT INTO cf_user_agents VALUES (?, ?, ?, ?, ?)", [since, until, ua, count, fetched_at])

    # --- cf_countries ---
    conn.execute("DELETE FROM cf_countries WHERE date_range_start = ? AND date_range_end = ?", [since, until])
    for row in data.get("top_countries", []):
        country = row.get("dimensions", {}).get("clientCountryName", "")
        count = row.get("count", 0)
        conn.execute("INSERT INTO cf_countries VALUES (?, ?, ?, ?, ?)", [since, until, country, count, fetched_at])

    # --- cf_status_codes ---
    conn.execute("DELETE FROM cf_status_codes WHERE date_range_start = ? AND date_range_end = ?", [since, until])
    for row in data.get("status_codes", []):
        status = row.get("dimensions", {}).get("edgeResponseStatus", 0)
        count = row.get("count", 0)
        conn.execute("INSERT INTO cf_status_codes VALUES (?, ?, ?, ?, ?)", [since, until, status, count, fetched_at])

    # --- cf_cache_status ---
    conn.execute("DELETE FROM cf_cache_status WHERE date_range_start = ? AND date_range_end = ?", [since, until])
    for row in data.get("cache_status", []):
        cs = row.get("dimensions", {}).get("cacheStatus", "")
        count = row.get("count", 0)
        conn.execute("INSERT INTO cf_cache_status VALUES (?, ?, ?, ?, ?)", [since, until, cs, count, fetched_at])

    # --- cf_bots ---
    conn.execute("DELETE FROM cf_bots WHERE date_range_start = ? AND date_range_end = ?", [since, until])
    for row in data.get("bots", []):
        dims = row.get("dimensions", {})
        ua = dims.get("userAgent", "")
        decision = dims.get("botManagementDecision", "")
        country = dims.get("clientCountryName", "")
        count = row.get("count", 0)
        conn.execute("INSERT INTO cf_bots VALUES (?, ?, ?, ?, ?, ?, ?)", [since, until, ua, decision, country, count, fetched_at])

    print(f"✓ {filepath.name} transformé")


def print_summary(conn: duckdb.DuckDBPyConnection):
    """Affiche un résumé des tables."""
    tables = [
        "cf_requests_daily", "cf_top_paths", "cf_user_agents",
        "cf_countries", "cf_status_codes", "cf_cache_status", "cf_bots",
    ]
    print(f"\n📊 DuckDB: {DB_PATH}")
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   {table}: {count:,} lignes")


def main():
    parser = argparse.ArgumentParser(description="Transform Cloudflare raw JSON → DuckDB")
    parser.add_argument("--file", type=str, help="Fichier JSON spécifique")
    parser.add_argument("--all", action="store_true", help="Tous les fichiers raw")
    args = parser.parse_args()

    conn = get_db()

    if args.file:
        fp = Path(args.file)
        if not fp.exists():
            print(f"❌ Fichier introuvable: {fp}")
            sys.exit(1)
        transform_file(fp, conn)
    elif args.all:
        files = sorted(RAW_DIR.glob("*.json"))
        if not files:
            print(f"❌ Aucun fichier dans {RAW_DIR}")
            sys.exit(1)
        for fp in files:
            transform_file(fp, conn)
    else:
        # Fichier du jour
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fp = RAW_DIR / f"{today}.json"
        if not fp.exists():
            print(f"❌ Pas de fichier pour aujourd'hui: {fp}")
            print("   Lance d'abord: python -m src.fetch_cloudflare")
            sys.exit(1)
        transform_file(fp, conn)

    print_summary(conn)
    conn.close()


if __name__ == "__main__":
    main()
