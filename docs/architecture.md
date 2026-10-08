# Renzai architecture

These diagrams describe the frozen V1 implementation. Optional AI stays outside authoritative
enforcement, and arrows do not imply capabilities such as streaming, tools, or autonomous action.

## 1. System architecture

```mermaid
flowchart LR
  SDK[Python / TypeScript SDKs] --> N[Nginx]
  B[Browser] --> N
  N --> W[Next.js]
  N --> API[FastAPI]
  API --> SEC[Security Engine]
  SEC --> RISK[Risk Engine]
  RISK --> POLICY[Policy Engine]
  API --> PROVIDER[Provider Layer]
  API --> PG[(PostgreSQL)]
  API --> REDIS[(Redis)]
  REDIS --> CELERY[Celery Worker]
  CELERY --> AI[Optional AI Intelligence]
  API --> OTEL[OpenTelemetry Collector]
  API --> PROM[Prometheus]
  CELERY --> PROM
  PROM --> GRAFANA[Grafana]
```

## 2. Analyze security pipeline

```mermaid
flowchart LR
  V[Bounded validation] --> N[Normalization]
  N --> D[11 deterministic detector classes]
  D --> A[Finding aggregation]
  A --> R[Versioned risk scoring]
  R --> P[Declarative policy]
  P --> X[allow / flag / redact / review / block]
  X --> DB[(Durable metadata and privacy-filtered evidence)]
  AI[Optional AI advisory] -. never changes .-> X
```

## 3. Gateway request flow

```mermaid
sequenceDiagram
  participant C as Application
  participant G as Renzai Gateway
  participant S as Security/Risk/Policy
  participant P as Configured Provider
  C->>G: bounded text chat request
  G->>S: input inspection
  S-->>G: durable input decision
  alt block, review, or inspection failure
    G-->>C: fail closed; no provider call
  else allowed or safely redacted
    G->>P: provider request
    P-->>G: bounded text response
    G->>S: output inspection
    S-->>G: durable output decision
    alt safe enforcement result
      G-->>C: allowed or redacted content
    else block, review, or redaction failure
      G-->>C: provider content withheld
    end
  end
```

## 4. Incident lifecycle

```mermaid
stateDiagram-v2
  [*] --> Open
  Open --> Investigating
  Open --> Resolved
  Open --> Ignored
  Open --> FalsePositive
  Investigating --> Resolved
  Investigating --> Ignored
  Investigating --> FalsePositive
  Resolved --> Investigating
  Ignored --> Investigating
  FalsePositive --> Investigating
  note right of Investigating
    Evidence relations, comments, assignments,
    and timeline entries remain tenant-scoped.
  end note
```

## 5. AI Intelligence flow

```mermaid
flowchart LR
  I[Incident + deterministic evidence] --> Q[ID-only Celery task]
  Q --> W[Worker revalidates tenant, consent, and configuration]
  W --> P[Optional configured AI provider]
  P --> V[Strict structured-output validation]
  V --> A[Advisory result with provenance]
  A -. cannot mutate .-> E[Deterministic findings / risk / policy]
```

## 6. Multi-tenant isolation model

```mermaid
flowchart TD
  U[User] --> M[Membership + role]
  M --> O[Organization]
  O --> APP[Applications]
  APP --> ENV[Environments]
  ENV --> KEY[Application keys]
  ENV --> ANA[Analyses]
  ENV --> POL[Policies]
  ENV --> PROV[Providers]
  ANA --> INC[Incidents]
  O --> AI[AI configurations/results]
  O --> ANALYTICS[Bounded analytics]
```

Composite database foreign keys bind environment-, provider-, incident-, and AI-linked records to
the same organization. Service-layer authorization hides foreign-tenant resources rather than
turning identifiers into an oracle.

## 7. Self-hosted deployment

```mermaid
flowchart TB
  HOST[Loopback/public ingress] --> N[Nginx :8080]
  HOST -->|optional loopback :3001| G[Grafana]
  subgraph edge[edge network]
    N --> WEB[Web]
  end
  subgraph app[application network]
    N --> API[API]
    WEB --> API
    API --> WORKER[Worker]
  end
  subgraph data[internal data network]
    API --> PG[(PostgreSQL)]
    API --> R[(Redis)]
    WORKER --> PG
    WORKER --> R
  end
  subgraph obs[internal observability network]
    API --> O[OTel Collector]
    API --> P[Prometheus]
    WORKER --> P
    PE[PostgreSQL exporter] --> P
    RE[Redis exporter] --> P
    P --> G
  end
```

Only Nginx and optional Grafana publish host ports. Production TLS, secret injection, backup,
capacity, and public-ingress policy remain operator responsibilities.

## 8. Observability architecture

```mermaid
flowchart LR
  API[API safe structured logs] --> LOG[Operator log pipeline]
  W[Worker safe structured logs] --> LOG
  API -->|bounded metrics| P[Prometheus]
  W -->|bounded metrics| P
  PGX[PostgreSQL exporter] --> P
  RX[Redis exporter] --> P
  P --> G[Grafana overview]
  API -->|sampled OTLP spans| O[OTel Collector]
  W -->|sampled OTLP spans| O
  O -->|allowlisted export| BACKEND[Operator-selected trace backend]
```

Metric labels exclude prompts, request IDs, user IDs, organization IDs, emails, and secrets. Trace
attributes and logs follow the same privacy boundary; observability outages never authorize bypassing
deterministic enforcement.
