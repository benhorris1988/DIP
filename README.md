# Data Integration Platform (DIP)

An extensible enterprise data integration platform. Connect heterogeneous source
systems (initially SAP OData, Oracle) to modern destinations (initially
SurrealDB, Microsoft SQL Server) through declaratively configured pipelines, and
monitor every job run from a single console.

## Architecture

```
┌──────────────┐      ┌────────────────────────────────────┐      ┌──────────────────┐
│  Flutter app │      │  FastAPI backend                   │      │                  │
│  Web · iOS · │ <──> │  ┌──────────────────────────────┐  │ <──> │  Source systems  │
│    Android   │      │  │ Connector registry           │  │      │  (SAP, Oracle…)  │
│              │      │  │  • sources/  • destinations/ │  │      │                  │
└──────────────┘      │  └──────────────────────────────┘  │      ├──────────────────┤
                      │  Pipelines • Jobs • Scheduler      │      │  Destinations    │
                      └────────────────────────────────────┘      │  (SurrealDB,     │
                                                                  │   MSSQL, …)      │
                                                                  └──────────────────┘
```

* **Backend** — Python FastAPI with a **SurrealDB metadata store** (the
  platform's own state — connections, pipelines, jobs, assets, DAG runs —
  lives in SurrealDB; tables are defined idempotently at startup), a
  connector plugin registry, and a pipeline runner that streams batches from a
  source connector to a destination connector.
* **Client** — Flutter app (web + iOS + Android) styled as the Bifrost
  operator console: Dashboard, Pipelines, Pipeline Detail, Connections, Job
  Runs, Error Explorer, Settings. See [`flutter_app/README.md`](flutter_app/README.md).
* **Connectors today**
  * Sources: `sap_odata` (OData v2 for SAP ECC 6.0 / S/4HANA), `oracle`
  * Destinations: `surrealdb`, `mssql` (insert + MERGE upsert), `fabric_warehouse`, `databricks_sql`
* **Roadmap connectors** — Snowflake, generic REST/Webhook, S3/Blob.
  Adding one is a single file under
  `backend/app/connectors/{sources,destinations}/`.

## Extending with a new connector

1. Create a new module in `backend/app/connectors/sources/` (or `destinations/`).
2. Subclass `SourceConnector` or `DestinationConnector` from
   `app.connectors.base`.
3. Define `metadata` (a `ConnectorMetadata`) describing config and secret
   fields — these power the dynamic UI form.
4. Decorate the class with `@registry.register` and import it from
   `app/connectors/__init__.py`.

The client automatically picks up the new connector via `GET /api/connectors`
and renders the configuration form from the metadata schema.

## Running locally

### Prerequisites
* Python 3.11+
* Flutter SDK 3.24+
* (Optional) Docker for the backend + SurrealDB
* (Optional) The Microsoft ODBC Driver 18 if you intend to use the MSSQL
  destination from your host

### Backend (Docker)

```bash
docker compose up --build
```

* Backend → http://localhost:8000 (Swagger UI at `/docs`)
* SurrealDB (metadata store) → ws://localhost:8001/rpc (persisted to a
  named volume; switch to your dedicated SurrealDB cluster in production
  by setting `DIP_SURREALDB_URL` / `DIP_SURREALDB_USER` /
  `DIP_SURREALDB_PASSWORD` / `DIP_SURREALDB_NAMESPACE` /
  `DIP_SURREALDB_DATABASE`).

### Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

Repository / API / runner tests need a `surreal` binary on PATH — they
spin up a transient in-memory instance per test. Pure unit tests
(MSSQL MERGE SQL builder, SAP OData mock, scheduler cron logic) run
without it.

### Flutter operator console

```bash
cd flutter_app
flutter create --platforms=web,ios,android --project-name=dip --org com.dip .
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api
```

See [`flutter_app/README.md`](flutter_app/README.md) for iOS / Android
instructions and release builds.

## Project layout

```
DIP/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI routers: connections, pipelines, jobs, connectors
│   │   ├── connectors/        # Pluggable connector framework
│   │   │   ├── base.py        # SourceConnector / DestinationConnector ABCs
│   │   │   ├── registry.py    # Decorator-based registry
│   │   │   ├── sources/       # sap_odata, oracle
│   │   │   └── destinations/  # surrealdb, mssql
│   │   ├── db/                # Async SQLAlchemy session + Base
│   │   ├── models/            # ORM models: Connection, Pipeline, Job
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/runner.py # Pipeline execution engine
│   │   └── main.py            # App entry / lifespan
│   ├── requirements.txt
│   └── Dockerfile
├── flutter_app/
│   ├── lib/
│   │   ├── api/               # Dio client + DTOs
│   │   ├── providers/         # Riverpod providers (data + theme)
│   │   ├── routes/            # go_router config
│   │   ├── theme/             # Bifrost palette + Material 3 theme
│   │   ├── widgets/           # Sidebar, header, status pills, sparkline, …
│   │   └── pages/             # One file per screen
│   ├── web/                   # Web bootstrap
│   ├── pubspec.yaml
│   └── README.md
└── docker-compose.yml
```

## API

All endpoints are mounted at `/api`:

| Method | Path                              | Purpose                          |
| ------ | --------------------------------- | -------------------------------- |
| GET    | `/api/health`                     | Health check                     |
| GET    | `/api/connectors`                 | List installed connector types   |
| GET    | `/api/connections`                | List connections                 |
| POST   | `/api/connections`                | Create connection                |
| POST   | `/api/connections/{id}/test`      | Probe the underlying system      |
| GET    | `/api/connections/{id}/objects`   | List tables / entity sets        |
| GET    | `/api/pipelines`                  | List pipelines                   |
| POST   | `/api/pipelines`                  | Create pipeline                  |
| POST   | `/api/pipelines/{id}/run`         | Trigger a pipeline run           |
| GET    | `/api/jobs`                       | List recent job runs             |
| GET    | `/api/jobs/stats`                 | Aggregate metrics for dashboard  |
| GET    | `/api/jobs/{id}`                  | Job detail with log              |

## Notes

* Mock SAP OData and Oracle source systems are intentionally **not** included —
  they are produced by a separate workstream and will be configured via the
  Connections page when available.
* Secrets are stored in the metadata DB. For production deployments, swap
  `Connection.secrets` for an external secret manager (Vault / Key Vault / AWS
  Secrets Manager) — the registry already separates `config` and `secrets` for
  this reason.
