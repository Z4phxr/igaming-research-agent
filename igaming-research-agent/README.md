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

## Railway Deploy

### Backend from repository root
- This repository includes root-level deployment files (`Dockerfile` and `railway.toml`) so Railway can build even when the repo root only contains the `igaming-research-agent/` folder.
- Health endpoint: `/api/health`.

### Recommended monorepo setup (two Railway services)
1. Backend service
	- Root directory: `igaming-research-agent/backend`
	- Builder: Dockerfile (`backend/Dockerfile`) or Python Nixpacks
	- Required env vars: `DATABASE_URL`, `OPENAI_API_KEY`, `SERPER_API_KEY`
2. Frontend service
	- Root directory: `igaming-research-agent/frontend`
	- Builder: Dockerfile (`frontend/Dockerfile`) or Node Nixpacks
	- Set `VITE_API_BASE_URL` to your backend public URL with `/api`

If Railway reports `Railpack could not determine how to build the app`, verify the service root directory is set correctly or deploy using the repository root with the included root `Dockerfile`.

## TODO
- Replace placeholder service implementations in `backend/app/services/*` with real Serper, scraper, and LLM calls.
- Add production `.env` and secret management.
