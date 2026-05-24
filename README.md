# SEO/GEO Dashboard — italiaanse-percolator.nl

Dashboard analytics basé sur Cloudflare pour le suivi SEO et GEO du site.

## Architecture

```
Cloudflare API (GraphQL)
    ↓
fetch_cloudflare.py     → data/raw/cloudflare/YYYY-MM-DD.json
    ↓
transform.py            → data/cloudflare.duckdb
    ↓
dashboard.py            → Streamlit + Plotly
    ↓
GitHub Actions          → Automatisation quotidienne
```

## Structure

```
seo-geo-dashboard/
├── src/
│   ├── fetch_cloudflare.py    # Connexion API + GraphQL Analytics
│   ├── transform.py           # Raw JSON → DuckDB
│   └── dashboard.py           # Streamlit dashboard
├── data/
│   ├── raw/cloudflare/        # JSON bruts par jour
│   ├── processed/             # Exports parquet/csv (optionnel)
│   └── cloudflare.duckdb      # Base analytique
├── .github/workflows/
│   └── daily-cloudflare.yml   # GitHub Actions quotidienne
├── .streamlit/config.toml     # Thème Streamlit
├── .env.example
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Installation

```bash
cd seo-geo-dashboard
pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec ton CLOUDFLARE_API_TOKEN et CLOUDFLARE_ZONE_ID
```

### 2. Tester la connexion

```bash
python -m src.fetch_cloudflare --test
```

### 3. Récupérer les données

```bash
python -m src.fetch_cloudflare --days 7
python -m src.transform
```

### 4. Lancer le dashboard

```bash
streamlit run src/dashboard.py
```

## Données récupérées

| Table DuckDB | Contenu |
|---|---|
| `cf_requests_daily` | Requêtes, bytes, cache, page views, uniques par jour |
| `cf_top_paths` | URLs les plus demandées |
| `cf_user_agents` | User-agents (navigateurs, bots) |
| `cf_countries` | Requêtes par pays |
| `cf_status_codes` | Codes HTTP (200, 301, 404, etc.) |
| `cf_cache_status` | Hit, miss, dynamic, expired |
| `cf_bots` | Bots détectés par Cloudflare Bot Management |

## Dashboard

6 onglets :
- **Trafic** — Requêtes/jour, cache vs non-cache
- **Pages** — Top 30 URLs les plus crawlées/visitées
- **Bots & UA** — Bots détectés + user-agents
- **Pays** — Carte choroplèthe + table
- **Status codes** — Répartition 2xx/3xx/4xx/5xx
- **Cache** — Hit/miss/dynamic

## GitHub Actions

Le workflow `daily-cloudflare.yml` tourne tous les jours à 05h00 (heure belge).

### Secrets à configurer

Dans le repo GitHub → Settings → Secrets and variables → Actions :

| Secret | Valeur |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Ton API token Cloudflare |
| `CLOUDFLARE_ZONE_ID` | L'ID de la zone italiaanse-percolator.nl |

### Lancement manuel

Actions → Daily Cloudflare Fetch → Run workflow

## Token Cloudflare

Créer un token API sur https://dash.cloudflare.com/profile/api-tokens :
- Template : **Custom token**
- Permissions : `Zone > Analytics > Read`
- Zone Resources : `Include > Specific zone > italiaanse-percolator.nl`

## Important

- **Repo PRIVÉ** — contient des données analytics
- Le fichier `.env` n'est jamais commité (dans `.gitignore`)
- Les données DuckDB sont commitées pour persistence entre les runs
