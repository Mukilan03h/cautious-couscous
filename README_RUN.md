# MyPlatform Run Instructions 🚀

This guide explains how to run the Backend and Frontend of MyPlatform locally outside of Docker.

---

## 🐍 Backend (Python/FastAPI)

### Prerequisites
- Python 3.11+
- PostgreSQL (running locally or accessible)
- Redis (running locally or accessible)

### 1. Setup Environment
Navigate to the backend directory:
```powershell
cd backend
```

Create and activate a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:
```powershell
pip install -r requirements/default.txt
```

### 2. Configuration
Create a `.env` file in `backend/` with necessary environment variables. Minimal example:
```env
POSTGRES_HOST=localhost
POSTGRES_User=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=esa
REDIS_HOST=localhost
AUTH_TYPE=basic
```

### 3. Database Migrations
Run Alembic migrations to set up the schema:
```powershell
alembic upgrade head
```

### 4. Run Server
Start the API server (defaults to port 8080 within code usually, or 8000 default uvicorn):
```powershell
uvicorn esa.main:app --reload --port 8080
```
*The backend API will be available at http://localhost:8080*

---

## ⚛️ Frontend (Next.js)

### Prerequisites
- Node.js 18+
- npm

### 1. Setup
Navigate to the web directory:
```powershell
cd web
```

Install dependencies:
```powershell
npm install
```

### 2. Configuration
Create a `.env.local` file `web/` if needed, pointing to the backend:
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
```

### 3. Run Development Server
Start the Next.js dev server:
```powershell
npm run dev
```
*The frontend will be available at http://localhost:3000*

---

## 🛠️ Common Commands

| Component | Action | Command |
|-----------|--------|---------|
| **Backend** | Run Tests | `pytest` |
| **Backend** | New Migration | `alembic revision --autogenerate -m "message"` |
| **Frontend** | Build Prod | `npm run build` |
| **Frontend** | Lint | `npm run lint` |
