# SEO/GEO Dashboard App

Application Streamlit déployable pour analyser les logs/analytics Cloudflare de `italiaanse-percolator.nl`.

Ce repo contient uniquement l'application : **aucune donnée analytics privée n'est commitée ici**.

## Repos

| Repo | Rôle | Visibilité |
|---|---|---|
| `seo-geo-dashboard` | App Streamlit déployable | Public ou privé |
| `seo-geo-dashboard-data` | DuckDB + raw JSON + pipeline Cloudflare | Privé |

## Architecture

```
seo-geo-dashboard-data
    └── data/cloudflare.duckdb
              ↓ via GitHub token
seo-geo-dashboard
    └── src/dashboard.py → Streamlit Cloud
```

## Structure

```
seo-geo-dashboard/
├── src/
│   └── dashboard.py
├── data/
│   └── .gitkeep
├── .streamlit/config.toml
├── requirements.txt
└── README.md
```

## Déploiement Streamlit

Dans Streamlit Cloud, ajoute ces secrets :

```toml
GITHUB_TOKEN = "ghp_xxx"
PRIVATE_DB_URL = "https://raw.githubusercontent.com/MarcW88/seo-geo-dashboard-data/main/data/cloudflare.duckdb"
```

Le `GITHUB_TOKEN` doit avoir accès au repo privé `seo-geo-dashboard-data`.

## Lancer localement

Si tu as déjà `data/cloudflare.duckdb` localement :

```bash
pip install -r requirements.txt
streamlit run src/dashboard.py
```

Si la DB n'existe pas localement, l'app tentera de la télécharger depuis le repo privé avec `GITHUB_TOKEN`.

## Dashboard

Single-page log analyzer avec :

- KPIs : hits, bots/UA suspects, erreurs, cache hit, URLs, pays
- Vue globale trafic
- Crawl SEO / bots
- Erreurs & performance technique
- Exploration d'URLs + export CSV
- Filtres sidebar : période, trafic, URL contient, type de page

## Important

- Ne jamais commiter `data/cloudflare.duckdb` dans ce repo app
- Les données privées restent dans `seo-geo-dashboard-data`
- Les secrets Cloudflare restent uniquement dans le repo data ou dans GitHub Actions du repo data
