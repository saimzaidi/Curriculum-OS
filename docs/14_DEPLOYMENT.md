# Deployment on Alibaba Cloud

## Hackathon topology

```text
Alibaba ECS
├── reverse proxy
├── Next.js web
├── FastAPI API
├── Prefect server
├── Prefect worker: ingestion
├── Prefect worker: generation
└── Prefect worker: export

Alibaba RDS PostgreSQL
└── relational data + pgvector

Alibaba OSS
├── original documents
├── normalized pages
├── generated assets
└── offline exports

Alibaba Model Studio
├── Qwen reasoning model
├── Qwen fast model
├── Qwen OCR
├── embeddings
└── reranker
```

## Local development

Use Docker Compose with:

- PostgreSQL + pgvector;
- MinIO;
- API;
- web;
- Prefect server;
- worker.

Model calls may target Alibaba Model Studio from local development.

## Environment variables

See `.env.example`.

Never commit:

- API keys;
- database passwords;
- OSS secrets;
- signing secrets.

## Deployment sequence

1. Provision RDS.
2. Enable pgvector.
3. Create OSS bucket.
4. Provision ECS.
5. Configure DNS and TLS.
6. Deploy containers.
7. Run migrations.
8. Create first organization and owner.
9. Verify upload.
10. Verify model calls.
11. Verify schedule solver.
12. Verify export download.
13. Run smoke test.

## Observability

Minimum:

- structured application logs;
- Prefect flow status;
- request trace IDs;
- job IDs;
- error rate;
- model latency and token usage;
- storage usage;
- schedule infeasibility count.

## Backups

- managed RDS backups;
- OSS versioning where available;
- exportable database snapshot before major demos.

## Cost controls

- use fast model for bulk generation;
- cache source embeddings;
- cache generation by input hash;
- pre-generate demo output;
- limit maximum pages and generation scope;
- record token usage per job;
- use batch inference later for full-term generation.

## Production evolution

Later add:

- separate worker autoscaling;
- managed queue;
- CDN;
- multi-region storage;
- SSO;
- tenant billing;
- disaster recovery.
