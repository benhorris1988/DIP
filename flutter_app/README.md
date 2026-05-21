# DIP Flutter Operator Console

Flutter client for the Data Integration Platform — same operator console as
the original React app, now targeting **web**, **iOS**, and **Android**.

## Prerequisites

- Flutter SDK ≥ 3.24 (Dart ≥ 3.4) — install with [fvm](https://fvm.app) or
  the official installer.
- A running DIP backend (`uvicorn app.main:app` from `../backend/`). The
  client expects it on `http://localhost:8000` by default.

## First-time setup

Platform scaffolding (`android/`, `ios/`, `web/` runner code) is intentionally
*not* committed — it's generated on demand to keep the repo lean and let
Flutter pick the right templates for your SDK version.

```bash
cd flutter_app

# Generate platform scaffolds (idempotent — safe to re-run)
flutter create --platforms=web,ios,android --project-name=dip --org com.dip .

# Fetch packages
flutter pub get
```

## Run

```bash
# Web (Chrome)
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api

# iOS simulator
flutter run -d "iPhone 15" \
  --dart-define=API_BASE_URL=http://localhost:8000/api

# Android emulator (10.0.2.2 routes to the host machine)
flutter run -d emulator-5554 \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
```

Set `API_BASE_URL` to your deployed backend when shipping builds:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://dip.example.com/api
flutter build ios --release --dart-define=API_BASE_URL=https://dip.example.com/api
flutter build web --release --dart-define=API_BASE_URL=https://dip.example.com/api
```

## Architecture

```
lib/
  main.dart                # ProviderScope + DipApp
  app.dart                 # MaterialApp.router, theme wiring
  theme/                   # Bifrost palette + Material 3 theme
  api/                     # Dio client + plain DTO classes
  providers/               # Riverpod providers (data, theme)
  routes/                  # go_router config
  widgets/
    layout/                # Sidebar, header, responsive scaffold, Bifrost mark
    ui/                    # Status pill, sparkline, connector icon, etc
  pages/                   # One file per screen
  util/                    # Date/duration formatters
```

- **State**: `flutter_riverpod` — `FutureProvider` per backend collection.
  `invalidateAll(ref)` after writes refreshes the dashboard.
- **Routing**: `go_router` with a single `ShellRoute` that hosts the
  responsive scaffold. URLs match the React app (`/dashboard`,
  `/pipelines/:id`, `/jobs/:id`, etc).
- **Layout**: above 900 px the sidebar is persistent; below it collapses
  into a drawer.
- **Theme**: light/dark toggle persisted to `SharedPreferences` under
  `dip.themeMode`.

## Notes

- iOS/Android: app transport security and Android cleartext flags only
  matter when you point at an `http://` backend during development.
  Production should be `https://`.
- Pull to refresh on the dashboard invalidates all data providers.
- `Recent batches` polls the backend every time you land on the page — for
  push-style live updates wire the backend's `GET /jobs/{id}` to SSE or a
  websocket and swap the `Timer.periodic` in `job_detail_page.dart` for a
  stream provider.
