.PHONY: install backend app app-web app-ios app-android clean

install:
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd flutter_app && flutter pub get

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# Generate android/ios/web scaffolding the first time you clone.
app-scaffold:
	cd flutter_app && flutter create --platforms=web,ios,android --project-name=dip --org com.dip .

app: app-web

app-web:
	cd flutter_app && flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api

app-ios:
	cd flutter_app && flutter run -d "iPhone 15" --dart-define=API_BASE_URL=http://localhost:8000/api

app-android:
	cd flutter_app && flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api

clean:
	rm -rf backend/.venv backend/dip.db flutter_app/.dart_tool flutter_app/build
