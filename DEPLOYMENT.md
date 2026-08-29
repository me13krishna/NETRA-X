# NETRA-X Render Deployment Guide

This guide provides step-by-step instructions to deploy the entire NETRA-X platform (FastAPI Backend API, PostgreSQL Database, and Next.js Web Frontend) onto **[Render](https://render.com)**.

---

## Architecture Overview on Render

```
                                +-----------------------------+
                                |      Next.js Frontend       |
                                |         (netra-web)         |
                                +--------------+--------------+
                                               |
                                               v  (HTTPS / REST)
                                +--------------+--------------+
                                |       FastAPI API           |
                                |         (netra-api)         |
                                +--------------+--------------+
                                               |
                                               v  (PostgreSQL)
                                +--------------+--------------+
                                |  Managed PostgreSQL Ledger  |
                                |          (netra-db)         |
                                +-----------------------------+
```

---

## Method 1: Automatic Blueprint Deployment (Recommended)

NETRA-X includes a pre-configured `render.yaml` Blueprint specification.

### Steps:
1. Push your NETRA-X repository to **GitHub** or **GitLab**.
2. Log into [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** -> **Blueprint**.
4. Connect your NETRA-X repository.
5. Render will automatically detect `render.yaml` and prompt to create:
   - `netra-db` (PostgreSQL Instance)
   - `netra-api` (Python Web Service)
   - `netra-web` (Node.js Web Service)
6. Click **Apply**.
7. Render will automatically build, link environment variables, run migrations, and seed the initial synthetic dataset (`admin@netra-x.local` and `analyst@netra-x.local`).

---

## Method 2: Manual Service Creation

If deploying services individually on Render:

### 1. PostgreSQL Database (`netra-db`)
- Create a **New PostgreSQL Database**.
- Database Name: `netrax_db`
- User: `netra`
- Copy the **Internal Database URL**.

### 2. FastAPI Backend Service (`netra-api`)
- Create a **New Web Service** pointing to your repository root.
- **Environment**: Python 3
- **Build Command**: `pip install --upgrade pip && pip install -e .`
- **Start Command**: `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `DATABASE_URL`: *(Paste Internal Database URL from Step 1)*
  - `PYTHONPATH`: `.`
  - `NETRAX_ALLOW_EPHEMERAL_SECRET`: `1` *(or set a custom `SECRET_KEY` string)*
  - `CORS_ORIGINS`: `https://netra-web.onrender.com,http://localhost:3000`

### 3. Next.js Frontend Service (`netra-web`)
- Create a **New Web Service** pointing to your repository.
- **Root Directory**: `apps/web`
- **Environment**: Node
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: `https://netra-api.onrender.com` *(Replace with your deployed netra-api URL)*

---

## Default Access Credentials

Upon initial launch, the system auto-seeds the authoritative synthetic Hero dataset:

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@netra-x.local` | `AdminPass2026!` |
| **Analyst** | `analyst@netra-x.local` | `AnalystPass2026!` |

---

## Verification & Health Check

Once deployed, verify your services:
- **API Health Check**: `https://netra-api.onrender.com/health` (should return `{"status": "healthy"}`)
- **API Documentation**: `https://netra-api.onrender.com/docs` (Swagger UI)
- **Web Portal**: `https://netra-web.onrender.com`
