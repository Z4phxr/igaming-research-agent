# iGaming Research Agent

Daily iGaming research app with a FastAPI backend, scheduled pipeline, and React dashboard.

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite + APScheduler
- Frontend: React 18 + TypeScript + TailwindCSS + Vite + Axios

## Structure
- `backend/` API, DB models, scheduler, scraping/search/analysis services
- `frontend/` React dashboard app

## Local Dev (without Docker)
1. Backend
	- Go to `backend/`
	- Install dependencies from `requirements.txt`
	- Run: `uvicorn app.main:app --reload --port 8001`
2. Frontend
	- Go to `frontend/`
	- Install dependencies with `npm install`
	- Run: `npm run dev`

The frontend expects API on `http://localhost:8001` by default.

## Docker
From project root (`igaming-research-agent/`):

1. Build and start
	- `docker compose up --build`
2. Access apps
	- Frontend: `http://localhost:3000`
	- Backend health: `http://localhost:8001/api/health`
3. Stop
	- `docker compose down`

Notes:
- Frontend container runs behind nginx and proxies `/api` to backend.
- SQLite file is persisted at `backend/data.db` via bind mount.
- You can override frontend API URL at build time with `VITE_API_BASE_URL`.

## TODO
- Replace placeholder service implementations in `backend/app/services/*` with real Serper, scraper, and LLM calls.
- Add production `.env` and secret management.
