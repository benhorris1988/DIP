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

* **Backend** — Python FastAPI with an async SQLAlchemy metadata store, a
  connector plugin registry, and a pipeline runner that streams batches from a
  source connector to a destination connector.
* **Client** — Flutter app (web + iOS + Android) styled as the Bifrost
  operator console: Dashboard, Pipelines, Pipeline Detail, Connections, Job
  Runs, Error Explorer, Settings. See [`flutter_app/README.md`](flutter_app/README.md).
* **Connectors today**
  * Sources: `sap_odata`, `oracle`, `mssql_source` (Microsoft SQL Server)
  * Destinations: `surrealdb`, `mssql` (Microsoft SQL Server), `fabric_warehouse`,
    `databricks_sql`
* **Roadmap connectors** — Snowflake, generic REST/Webhook, S3/Blob. Adding one
  is a single file under `backend/app/connectors/{sources,destinations}/`.

## Transformations

Pipelines can reshape records in-flight between the source and destination. A
pipeline carries an ordered **transform plan** (`Pipeline.transform`) that runs
on every batch after the field mappings and before the write. Build it visually
with the drag-and-drop editor on the pipeline form, or declare it in YAML.

Available step types (see `GET /api/transforms` for the live catalog, config
fields and inline code examples that power the builder UI):

| Category | Steps |
| -------- | ----- |
| Schema   | `rename`, `drop`, `select` |
| Values   | `cast`, `string_op`, `replace`, `fill_null`, `set_constant`, `concat` |
| Python   | `python_column` (expression per cell), `python_row` (statements on the row) |
| Rows     | `filter` (keep rows where a Python expression is true) |

The `python_*` / `filter` steps run small snippets of Python in a restricted
namespace (limited builtins, a few safe modules, no `import`). This is **not** a
security sandbox — only operators trusted to define pipelines can author them.

### Error handling

Each plan has an `on_error` policy:

* `skip` (default) — a row that fails a transform or that the destination
  rejects is dropped, counted in the job's `rows_failed`, and logged as an
  `error` entry. The run still completes.
* `fail` — the first bad row aborts the whole run.

Batch writes that raise are automatically retried row-by-row so a single bad
record doesn't sink the batch. Failed runs and partial (row-level) failures are
both surfaced in the **Error Explorer**, and every job's log stream shows the
captured error samples.

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
* SurrealDB → ws://localhost:8001/rpc

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
| GET    | `/api/transforms`                 | Catalog of transformation steps  |
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
