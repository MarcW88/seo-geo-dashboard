"""
fetch_cloudflare.py — Récupère les données analytics via l'API GraphQL Cloudflare.

Usage:
    python -m src.fetch_cloudflare              # Récupère les 7 derniers jours
    python -m src.fetch_cloudflare --days 30    # Récupère les 30 derniers jours
    python -m src.fetch_cloudflare --test       # Teste la connexion uniquement
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CF_API_URL = "https://api.cloudflare.com/client/v4/graphql"
CF_REST_URL = "https://api.cloudflare.com/client/v4"

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
DOMAIN = os.getenv("DOMAIN", "italiaanse-percolator.nl")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "cloudflare"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_env():
    """Vérifie que les variables d'environnement sont configurées."""
    missing = []
    if not API_TOKEN:
        missing.append("CLOUDFLARE_API_TOKEN")
    if not ZONE_ID:
        missing.append("CLOUDFLARE_ZONE_ID")
    if missing:
        print(f"❌ Variables manquantes dans .env : {', '.join(missing)}")
        sys.exit(1)


def test_connection():
    """Teste le token et l'accès à la zone."""
    _check_env()

    # 1. Vérifier le token
    r = requests.get(f"{CF_REST_URL}/user/tokens/verify", headers=HEADERS)
    token_data = r.json()
    if not token_data.get("success"):
        print("❌ Token invalide.")
        print(json.dumps(token_data, indent=2))
        return False
    print(f"✓ Token valide — statut: {token_data['result']['status']}")

    # 2. Vérifier la zone
    r = requests.get(f"{CF_REST_URL}/zones/{ZONE_ID}", headers=HEADERS)
    zone_data = r.json()
    if not zone_data.get("success"):
        print(f"❌ Zone {ZONE_ID} inaccessible.")
        print(json.dumps(zone_data, indent=2))
        return False
    zone = zone_data["result"]
    print(f"✓ Zone OK — {zone['name']} ({zone['status']})")
    print(f"  Plan: {zone.get('plan', {}).get('name', 'N/A')}")

    return True


# ---------------------------------------------------------------------------
# GraphQL Queries
# ---------------------------------------------------------------------------
QUERY_HTTP_REQUESTS = """
query HttpRequests($zoneTag: String!, $since: Date!, $until: Date!) {
  viewer {
    zones(filter: {zoneTag: $zoneTag}) {

      httpRequests1dGroups(
        limit: 1000
        filter: {date_geq: $since, date_leq: $until}
        orderBy: [date_ASC]
      ) {
        dimensions { date }
        sum {
          requests
          bytes
          cachedRequests
          cachedBytes
          threats
          pageViews
        }
        uniq { uniques }
      }

      topPaths: httpRequestsAdaptiveGroups(
        limit: 100
        filter: {date_geq: $since, date_leq: $until}
        orderBy: [count_DESC]
      ) {
        count
        dimensions {
          clientRequestPath
        }
      }

      topUserAgents: httpRequestsAdaptiveGroups(
        limit: 50
        filter: {date_geq: $since, date_leq: $until}
        orderBy: [count_DESC]
      ) {
        count
        dimensions {
          userAgent
        }
      }

      topCountries: httpRequestsAdaptiveGroups(
        limit: 50
        filter: {date_geq: $since, date_leq: $until}
        orderBy: [count_DESC]
      ) {
        count
        dimensions {
          clientCountryName
        }
      }

      statusCodes: httpRequestsAdaptiveGroups(
        limit: 50
        filter: {date_geq: $since, date_leq: $until}
        orderBy: [count_DESC]
      ) {
        count
        dimensions {
          edgeResponseStatus
        }
      }

      cacheStatus: httpRequestsAdaptiveGroups(
        limit: 20
        filter: {date_geq: $since, date_leq: $until}
        orderBy: [count_DESC]
      ) {
        count
        dimensions {
          cacheStatus
        }
      }

      bots: httpRequestsAdaptiveGroups(
        limit: 50
        filter: {date_geq: $since, date_leq: $until, botManagementDecision_neq: "likely_human"}
        orderBy: [count_DESC]
      ) {
        count
        dimensions {
          userAgent
          botManagementDecision
          clientCountryName
        }
      }

    }
  }
}
"""


def fetch_analytics(days: int = 7) -> dict:
    """Récupère les analytics Cloudflare pour les N derniers jours."""
    _check_env()

    until_date = datetime.now(timezone.utc).date()
    since_date = until_date - timedelta(days=days)

    variables = {
        "zoneTag": ZONE_ID,
        "since": since_date.isoformat(),
        "until": until_date.isoformat(),
    }

    print(f"📡 Requête Cloudflare Analytics: {since_date} → {until_date} ({days}j)")

    r = requests.post(
        CF_API_URL,
        headers=HEADERS,
        json={"query": QUERY_HTTP_REQUESTS, "variables": variables},
    )

    if r.status_code != 200:
        print(f"❌ HTTP {r.status_code}")
        print(r.text[:500])
        sys.exit(1)

    data = r.json()

    if data.get("errors"):
        print("❌ Erreurs GraphQL:")
        for err in data["errors"]:
            print(f"  - {err.get('message', err)}")
        # Continue quand même — certains champs peuvent avoir répondu
        if not data.get("data"):
            sys.exit(1)

    zones = data.get("data", {}).get("viewer", {}).get("zones", [])
    if not zones:
        print("❌ Aucune donnée retournée pour cette zone.")
        sys.exit(1)

    zone_data = zones[0]
    print(f"✓ Données reçues")

    return {
        "meta": {
            "domain": DOMAIN,
            "zone_id": ZONE_ID,
            "since": since_date.isoformat(),
            "until": until_date.isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
        "daily": zone_data.get("httpRequests1dGroups", []),
        "top_paths": zone_data.get("topPaths", []),
        "top_user_agents": zone_data.get("topUserAgents", []),
        "top_countries": zone_data.get("topCountries", []),
        "status_codes": zone_data.get("statusCodes", []),
        "cache_status": zone_data.get("cacheStatus", []),
        "bots": zone_data.get("bots", []),
    }


def save_raw(data: dict) -> Path:
    """Sauvegarde les données brutes en JSON."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = RAW_DIR / f"{today}.json"
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"💾 Sauvegardé → {filepath}")
    return filepath


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Fetch Cloudflare Analytics")
    parser.add_argument("--test", action="store_true", help="Tester la connexion")
    parser.add_argument("--days", type=int, default=7, help="Nombre de jours (défaut: 7)")
    args = parser.parse_args()

    if args.test:
        ok = test_connection()
        sys.exit(0 if ok else 1)

    data = fetch_analytics(days=args.days)
    save_raw(data)

    # Quick summary
    daily = data.get("daily", [])
    total_requests = sum(d.get("sum", {}).get("requests", 0) for d in daily)
    total_cached = sum(d.get("sum", {}).get("cachedRequests", 0) for d in daily)
    cache_pct = (total_cached / total_requests * 100) if total_requests else 0

    print(f"\n📊 Résumé {data['meta']['since']} → {data['meta']['until']}")
    print(f"   Requêtes totales : {total_requests:,}")
    print(f"   Requêtes cachées : {total_cached:,} ({cache_pct:.1f}%)")
    print(f"   Top paths        : {len(data.get('top_paths', []))}")
    print(f"   User-agents      : {len(data.get('top_user_agents', []))}")
    print(f"   Pays             : {len(data.get('top_countries', []))}")
    print(f"   Bots détectés    : {len(data.get('bots', []))}")


if __name__ == "__main__":
    main()
