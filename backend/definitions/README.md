# Pipeline & asset definitions

Files in this directory are the source of truth for pipelines + assets.
On backend startup (and again whenever `POST /api/definitions/reload`
is called) every `*.yaml` / `*.yml` file is parsed, validated, and
upserted into the metadata DB.

## Schema

```yaml
pipeline:
  name: <unique pipeline name>
  description: <optional>
  mode: full | incremental | upsert
  schedule: "<cron expression>"   # optional; omit for manual-only
  enabled: true
  source:
    connection: <connection name>   # must exist via the Connections UI
    object: <table / entity set>
    incremental_field: <optional column name>
  destination:
    connection: <connection name>
    object: <table>
  field_mappings:                  # optional; empty = pass-through
    - source: <source column>
      destination: <destination column>
      transform: upper | lower | trim   # optional

assets:                            # 0..N assets produced by this pipeline
  - key: <stable identifier>
    description: <optional>
    depends_on:                    # optional; asset keys this one needs
      - <other asset key>
    metadata:                      # optional free-form
      owner: data-platform
      tier: silver
    freshness:                     # optional; enables auto-materialise
      max_age_minutes: 60          # re-run if older than 1h
      # max_age_hours: 4           # whichever is shorter wins
```

## Auto-materialisation

If an asset declares a `freshness` block, the backend scheduler
(`freshness_tick`, see `app/services/scheduler.py`) inspects it every
minute. When the most recent successful materialisation is older than
the policy allows (or the asset has never been materialised), a DAG run
tagged `triggered_by: auto` is launched. Stale assets discovered in the
same tick are bundled into a single DAG run so shared upstream
pipelines don't run twice. Runs already in flight for an asset are
skipped to avoid storms.

## Rules

- Connection names must already exist (created via the Connections UI).
  Secrets stay in the DB; this directory holds structure only.
- Asset keys are global and must be unique across all files.
- The asset DAG must be acyclic. Cycles abort the entire load.
- An asset listed in `depends_on` must either be declared in another
  YAML file *or* already exist in the DB.
- A YAML pipeline cannot share a name with a UI-created pipeline. Name
  conflicts abort that file's load (others continue).
- Removing a file removes its pipeline and assets on the next reload.
