---
description: How to run the fullstack application locally
---

This workflow guides you through running the backend and frontend services on your local machine.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or access to the RDS instance defined in .env)

## 1. Backend Setup

Open a terminal in the `backend` directory.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the backend server:

```powershell
# Ensure you have a .env file in backend/backend/.env or set environment variables
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 2. Frontend Setup

Open a new terminal in the `fullstack-data-platform` directory.

```powershell
cd fullstack-data-platform
npm install
```

Start the frontend server pointing to local backend:

```powershell
# Windows PowerShell
$env:VITE_API_URL="http://localhost:8000"
npm run dev
```

## Automation

You can also use the `start_local.ps1` script in the root directory to launch both services automatically.
