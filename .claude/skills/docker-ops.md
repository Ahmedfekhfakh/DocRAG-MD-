# Skill : Docker & Deploiement

Expert Docker Compose et infra GCP.

## Scope
`docker-compose.yml`, `Dockerfile`, `.env`, deploiement.

## Services Docker (5+)
| Service    | Port | Image / Build                           |
|:-----------|:-----|:----------------------------------------|
| qdrant     | 6333 | qdrant/qdrant:latest                    |
| llama-cpp  | 8080 | ghcr.io/ggerganov/llama.cpp:server      |
| api        | 8000 | Build depuis Dockerfile                 |
| frontend   | 3000 | Build multi-stage → nginx               |
| postgres   | 5432 | postgres:15 (Langfuse)                  |
| clickhouse |      | Langfuse analytics                      |
| minio      |      | Langfuse storage                        |

## Regles
- Services communiquent par NOM (pas localhost)
- llama-cpp : `--threads 4 --ctx-size 4096 --cont-batching`
- api depends_on llama-cpp (condition: service_healthy)
- KG charge dans lifespan FastAPI (pas dans Docker)
- Volumes : qdrant_storage, pg_data, hf_cache
- VM GCP : e2-standard-8, 32 Go RAM, Debian 12, europe-west9
- Ports exposes (firewall GCP) : 3000, 8000, 6333

## Commandes
```bash
docker compose up -d
docker compose logs -f api
docker compose up -d --build api
docker compose exec api python -m ingestion.pipeline
```
