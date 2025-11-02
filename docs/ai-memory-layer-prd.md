# AI Memory Layer — Product Requirements Document

## 1. Overview
- **Product Name:** AI Memory Layer (AIML)
- **Owner:** Core Platform / Memory Services squad
- **Purpose:** Provide a deterministic backend memory service for conversational AI systems, decoupled from any frontend or LLM.
- **Vision:** A stateless, horizontally-scalable API that stores, retrieves, and manages conversation memories using transparent policies for importance, decay, retention, and deletion.
- **Primary KPI Targets:** retrieval latency < 100 ms for 10k memories; >95% relevance stability; integration in <1 day for partner teams.

## 2. Problem & Opportunity
| Pain Point | Impact | Opportunity |
| --- | --- | --- |
| Context stuffing inflates prompts | Higher LLM cost, latency | Move memory outside prompt via backend service |
| Ad-hoc “memory” logic per app | Inconsistent, non-repeatable outputs | Provide deterministic policies and APIs |
| Drift and duplication of memories | Unstable behaviors | Centralized retention/forgetting with importance + decay |

## 3. Goals & Non-Goals
**Goals**
1. Deterministic, policy-driven storage and retrieval for conversational memories.
2. Simple REST contract that any chat/agent product can integrate without UI coupling.
3. Automated retention flows (archive/delete) driven by importance, recency, and quotas.
4. Operational readiness: health endpoints, observability, Docker deployment.

**Non-Goals**
- Building UI/agent orchestration layers.
- Training or hosting the LLM itself.
- Providing cross-tenant analytics beyond aggregate metrics.

## 4. Personas & Use Cases
- **Conversational AI engineer:** Wants reliable memory insertion/retrieval calls without prompt bloat.
- **Platform SRE:** Needs observability and deterministic retention for compliance.
- **Product manager:** Needs policies and metrics to reason about memory effectiveness.

Primary Use Cases:
1. Store each user or agent message with metadata and embeddings (`POST /v1/messages`).
2. Retrieve top-K relevant memories given query text (`GET /v1/memory/search`).
3. Periodically archive stale/low-importance memories; delete archived data when policy dictates.
4. Monitor service health and retention job status.

## 5. User Stories
- As an AI engineer, I can ingest messages with metadata so that downstream retrieval uses consistent context.
- As an agent runtime, I can fetch top-K relevant memories under <100 ms so my prompts stay compact.
- As compliance lead, I can define policies to archive/delete certain memories to honor retention rules.
- As SRE, I can check health/metrics to ensure the Memory Layer meets 99.9% uptime.

## 6. Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| FR-1 | Store all messages with embeddings and importance scoring | P1 | API persists message, embedding vector, metadata, timestamps, importance (0–1). |
| FR-2 | Retrieve top-K relevant memories deterministically | P1 | Given same query and config, returns identical ordered set (similarity + decay + importance scoring). |
| FR-3 | Archive low-importance/old messages based on policies | P1 | Scheduler moves qualifying rows to archive tables with audit logs. |
| FR-4 | Delete archived data via admin policy | P2 | Admin job purges archive partitions older than configured retention. |
| FR-5 | REST endpoints for ingest, search, retention, health | P1 | Endpoints documented, versioned (`/v1`), auth-protected, JSON payloads. |
| FR-6 | Importance scorer selectable (rule-based default, ML plug-in) | P2 | Config flag chooses scoring strategy per tenant. |
| FR-7 | Tenancy isolation via org/workspace IDs | P1 | All queries filtered by tenant scope; no cross-tenant leakage. |

## 7. Non-Functional Requirements
- **Performance:** <100 ms p95 retrieval for 10k memories per tenant; ingestion <150 ms.
- **Scalability:** Stateless FastAPI workers; Postgres + pgvector with sharding or partitioning; autoscale to 10x load.
- **Reliability:** 99.9% uptime, zero data loss; RPO < 5 min, RTO < 30 min.
- **Determinism:** Same input + configuration yields identical outputs; documented scoring formula.
- **Security:** mTLS between services; per-tenant API keys or OAuth; encrypted data at rest (Postgres TDE) and in transit.
- **Observability:** Structured logging, distributed tracing (OpenTelemetry), Prometheus metrics for latency, throughput, retention jobs.

## 8. System Architecture
- **API Layer (FastAPI):** Handles REST requests, validates payloads, enforces auth/tenant scoping.
- **Embedding Service:** Async job or sidecar that converts text to vector using configured model (OpenAI, in-house). Supports batched embedding to reduce latency.
- **Importance Scorer:** Rule-based module using recency, role, sentiment, explicit tags; pluggable to ML scorer.
- **Retrieval Engine:** Combines vector similarity (pgvector), exponential decay, and importance weighting to rank memories.
- **Retention Engine:** Scheduler (e.g., Celery/Arq) triggers archive/delete jobs; policies stored in Postgres.
- **Metadata Store:** Postgres with pgvector extension; partitioned tables per tenant or time window; archive schema separated.
- **Infrastructure:** Dockerized app; deploy via ECS/Kubernetes; background workers share codebase with API.

**Data Flow (happy path):**
1. Client sends message to `/v1/messages`.
2. API persists raw message, queues embedding/scoring task.
3. Worker computes embedding + importance, updates record.
4. Search requests query pgvector index, apply scoring formula.
5. Retention scheduler runs archive/delete jobs per policy.

## 9. Data Model (Draft)
| Table | Key Fields |
| --- | --- |
| `messages` | `id (uuid)`, `tenant_id`, `conversation_id`, `role`, `content`, `metadata JSONB`, `created_at`, `importance_score`, `embedding vector`, `status` |
| `archived_messages` | Same columns + `archived_at`, `archive_reason` |
| `retention_policies` | `tenant_id`, `max_age_days`, `importance_threshold`, `max_items`, `created_by`, `updated_at` |
| `embedding_jobs` | `job_id`, `message_id`, `status`, `attempts`, `last_error` |

Indexes: pgvector index on `embedding`; BTREE on `(tenant_id, conversation_id, created_at)`; partial index for `importance_score`.

## 10. API Contracts
### POST `/v1/messages`
- **Purpose:** Ingest a message and trigger embedding + scoring.
- **Request Body:**
```json
{
  "tenant_id": "org_123",
  "conversation_id": "conv_456",
  "role": "user|assistant|system",
  "content": "string",
  "metadata": {"channel": "web", "tags": ["billing"]},
  "importance_override": 0.92
}
```
- **Response:** `202 Accepted` with `message_id`, status.
- **Notes:** Importance override optional; otherwise scorer runs asynchronously.

### GET `/v1/memory/search`
- **Query Params:** `tenant_id`, `conversation_id` (optional), `query`, `top_k`, `time_horizon`, `importance_min`.
- **Response:** Ordered list of memories with scores, timestamps, metadata.
- **Determinism:** Response order = similarity_score * similarity_weight + importance * importance_weight + decay_factor.

### POST `/v1/admin/retention/run`
- **Purpose:** Trigger archive/delete per tenant or global.
- **Request Body:** `tenant_id`, `actions: ["archive","delete"]`, optional dry-run flag.
- **Response:** Summary of records affected, duration, errors.

### GET `/v1/admin/health`
- **Checks:** DB connectivity, pgvector status, worker queue backlog, last retention run.
- **Response:** `status=ok|degraded`, component-level metrics.

## 11. Retention & Forgetting Policies
- **Policies per tenant:** configurable via admin console or API (future).
- **Archive Rules:** archive when `(importance < threshold) OR (age > max_age_days) OR (quota > max_items)`.
- **Deletion Rules:** delete archived rows older than `delete_after_days`; support legal holds.
- **Deduplication:** optional hash on normalized content to avoid duplicates before storage.
- **Audit:** All archival/deletion logged with reason codes.

## 12. Operational Considerations
- **Deployment:** Docker image; env-configured Postgres/Redis URIs; migrations via Alembic.
- **Scaling:** Separate worker deployment for embeddings/retention; autoscale on queue depth.
- **Monitoring:** Prometheus exporters, Grafana dashboards for ingest/search latency, retention throughput, error rates.
- **Alerting:** On-call alerts for p95 latency > target, queue backlog, failed retention runs, DB replication lag.
- **Disaster Recovery:** Daily base backups; WAL archiving; runbooks for failover.

## 13. Success Metrics
1. Retrieval p95 < 100 ms at 10k memories per tenant.
2. >95% deterministic relevance stability (measured via golden queries).
3. Integration partners onboard in <1 day (time to first successful search).
4. Retention jobs complete within SLA (<10 min per 1M rows) and zero policy violations.

## 14. Timeline (8 Weeks)
| Weeks | Milestone | Deliverables |
| --- | --- | --- |
| 1–2 | Core API & schema | Message ingest endpoint, base Postgres schema, pgvector enabled, Dockerfile draft |
| 3–4 | Retrieval & retention | Search endpoint with scoring stack, scheduler + archive flow, importance scorer |
| 5–6 | Packaging & deployment | Production-ready Docker image, IaC templates, CI/CD pipeline |
| 7–8 | Observability & docs | Health endpoint, metrics/dashboards, runbooks, public integration guide |

## 15. Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Embedding latency spikes | Slower ingest | Batch embedding, async workers, caching vectors for repeated text |
| Determinism drift due to floating math | Inconsistent results | Versioned scoring formula, tolerance tests |
| Storage bloat | Higher cost | Partitioning, compression, retention policies |
| Multi-tenant data leakage | Compliance | Strict tenant filters, automated tests, security review |

## 16. Assumptions & Open Questions
- Assumes access to embedding model (first-party or OpenAI) with SLA.
- Assumes Postgres with pgvector available; optional read replicas.
- **Open Questions:**
  1. Do we require per-tenant encryption keys (KMS)?
  2. Should importance scoring be synchronous for VIP tenants?
  3. Minimum viable admin UI vs. API-only management?

## 17. Acceptance Criteria
- Deterministic storage/retrieval verified via regression tests.
- Policy-based retention + deletion run successfully in staging with sample data.
- Docker image deploys with migrations + background workers.
- API reference + integration playbook delivered; partner team validates end-to-end flow.

