# Technology Stack

## Frontend

- Next.js 16
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- React Hook Form
- Zod
- Dexie.js
- React Flow
- Recharts
- date-fns

## Backend

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- psycopg 3
- httpx
- structlog

## Workflows

- Prefect 3
- PostgreSQL-backed job metadata
- idempotency keys
- retry policies by job type

## Database and storage

- PostgreSQL
- pgvector
- Alibaba RDS for PostgreSQL
- Alibaba OSS
- local MinIO in development

## AI and retrieval

- Qwen3.7 Plus for difficult reasoning and multimodal semantic work
- Qwen3.6 Flash for high-volume generation
- Qwen OCR for difficult document pages
- text-embedding-v4
- qwen3-rerank
- optional local Qwen3-Embedding-0.6B later
- strict Pydantic validation around every model response

## Document parsing

- PyMuPDF for preflight and page operations
- MinerU as primary parser
- PaddleOCR PP-OCRv5 for Urdu/Sindhi/Pashto fallback
- Qwen OCR for formulas, tables, diagrams, exam papers, and difficult scans

## Optimization and graphs

- Google OR-Tools CP-SAT
- NetworkX

## Offline and print

- service worker
- Dexie / IndexedDB
- static HTML export
- MiniSearch or FlexSearch
- Paged.js
- ZIP compilation

## Deployment

- Docker Compose for local development
- Alibaba ECS for web/API/workers
- Alibaba RDS PostgreSQL
- Alibaba OSS
- Alibaba Model Studio

## Testing

- pytest
- pytest-asyncio
- Playwright
- Vitest
- React Testing Library
- golden datasets
- DeepEval or Ragas only for secondary LLM evaluation, not as the sole pass/fail mechanism

## Why these choices

### PostgreSQL instead of a dedicated graph database

The curriculum graph is strongly connected to schedules, sources, assessments, users, and versions. Relational transactions matter more than graph-database convenience.

### Prefect instead of agent frameworks

The workflow is known, typed, retryable, and inspectable. Agent autonomy would add hidden state and unreliable control flow.

### OR-Tools instead of LLM scheduling

Scheduling is a constraint optimization problem. It needs valid, repeatable results and explicit infeasibility reporting.

### Hosted Qwen during the hackathon

Self-hosting a large model adds deployment risk without improving the core product demonstration.
