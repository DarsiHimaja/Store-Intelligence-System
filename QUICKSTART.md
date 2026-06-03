# 🚀 Quick Deployment Guide

## Option 1: Local Deployment (Fastest - 2 minutes)

### Step 1: Start the API
```bash
cd c:\purplle
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Start the Dashboard (New Terminal)
```bash
cd c:\purplle
streamlit run dashboard/app.py
```

### Step 3: Load Sample Data (New Terminal)
```bash
cd c:\purplle
python load_events.py
```

### 🔗 Access Links:
- **Dashboard**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

---

## Option 2: Docker Deployment (Production Ready)

### Step 1: Build and Start
```bash
cd c:\purplle
docker compose up --build -d
```

### Step 2: Load Data
```bash
docker compose exec api python load_events.py
```

### 🔗 Access Links:
- **Dashboard**: http://localhost:8501
- **API**: http://localhost:8000/docs

---

## Option 3: Cloud Deployment (Free Hosting)

### 🌐 Deploy to Render.com (FREE)

1. **Create account**: https://render.com
2. **New Web Service** → Connect your GitHub repo
3. **Deploy API**:
   - Name: `store-intelligence-api`
   - Environment: `Docker`
   - Dockerfile: `./Dockerfile`
   - Health Check: `/health`
   
4. **Deploy Dashboard**:
   - Name: `store-intelligence-dashboard`
   - Environment: `Docker`
   - Dockerfile: `./Dockerfile.dashboard`
   - Add env var: `API_URL` = `https://store-intelligence-api.onrender.com`

5. **Your Live Links**:
   - Dashboard: `https://store-intelligence-dashboard.onrender.com`
   - API: `https://store-intelligence-api.onrender.com/docs`

---

### 🚂 Deploy to Railway.app (FREE $5 credit)

1. **Create account**: https://railway.app
2. **New Project** → Deploy from GitHub
3. **Add services**:
   - Service 1: API (Port: 8000)
   - Service 2: Dashboard (Port: 8501)
   
4. **Your Live Links**:
   - Dashboard: `https://your-app.up.railway.app`
   - API: `https://your-api.up.railway.app/docs`

---

### ☁️ Deploy to Streamlit Cloud (FREE - Dashboard Only)

1. **Create account**: https://share.streamlit.io
2. **New app** → Point to `dashboard/app.py`
3. Update `API_URL` in settings to your deployed API

4. **Your Live Link**:
   - Dashboard: `https://your-app.streamlit.app`

---

### 🔥 Deploy to Vercel (API as Serverless)

```bash
npm i -g vercel
cd c:\purplle
vercel
```

---

## Current Local Setup

If you've already started the services locally:

### 🔗 Your Current Links:
- **Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics Endpoint**: http://localhost:8000/stores/STORE_001/metrics
- **Funnel Endpoint**: http://localhost:8000/stores/STORE_001/funnel
- **Heatmap Endpoint**: http://localhost:8000/stores/STORE_001/heatmap

---

## 📊 Demo Data

To populate with demo data:
```bash
python load_events.py
```

Or run detection pipeline:
```bash
python pipeline/run.py --videos dataset/videos --store STORE_001 --api http://localhost:8000
```

---

## 🛑 Stop Services

**Local:**
- Press `Ctrl+C` in each terminal

**Docker:**
```bash
docker compose down
```

---

## 🎯 Recommended for Demo

**Fastest**: Option 1 (Local) - Ready in 2 minutes
**Best for Sharing**: Option 3 (Render.com) - Free public URL
**Production**: Option 2 (Docker) - Scalable and isolated
