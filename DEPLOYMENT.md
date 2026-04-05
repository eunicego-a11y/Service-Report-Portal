# Deployment Guide

## Project Overview

- **Stack**: Python Flask + Vite (Node.js frontend build)
- **Entry Point**: `run.py` (development), `gunicorn "run:application"` (production)
- **Server**: Gunicorn WSGI application server
- **Frontend Build**: Vite (bundles to `static/dist/`)
- **Dependencies**: See `requirements.txt`

---

## 1. Version Control (Git)

Your repo is already initialized with a good `.gitignore`. To commit your work:

```bash
cd c:\Users\MCBTSI\Documents\MONDAY.COM\Web\service_report_app
git add .
git commit -m "Add Service Status options, Machine System search, and fix TSP WORKWITH personsAndTeams format"
git log  # See your commits
```

**Key files tracked:**

- `app/` — your Python app code
- `frontend/src/` — your Vite source (JavaScript)
- `requirements.txt` — Python dependencies
- `package.json` & `frontend/vite.config.js` — Node.js build config
- `run.py`, `.github/` — entry point and CI/CD configs
- `.env.example` (recommend creating) — template for secrets

**Never commit:**

- `.env` (secrets) ✓ Already in .gitignore
- `.venv/` (virtual environment) ✓ Already in .gitignore
- `signatures/`, `static/uploads/` (user data) ✓ Already in .gitignore

---

## 2. Deployment Options

### **Option A: Heroku (Easiest — Free tier limited)**

Great for quick hosting, OAuth-friendly.

**Steps:**

1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli
2. Create a `Procfile` in project root:
   ```
   web: gunicorn "run:application"
   ```
3. Create a `runtime.txt`:
   ```
   python-3.11.9
   ```
4. Push to Heroku:
   ```bash
   heroku login
   heroku create your-app-name
   heroku config:set $(cat .env | tr '\n' ' ')  # Set environment variables
   git push heroku main
   ```

**Pros:** Easy OAuth setup, auto HTTPS, simple scaling  
**Cons:** Free tier is limited, dyno hours restricted

---

### **Option B: AWS (Scalable, Pay-as-you-go)**

**Using Elastic Beanstalk (simplest AWS option):**

1. Install AWS CLI + EB CLI
2. Create `.ebextensions/python.config`:
   ```yaml
   option_settings:
     aws:elasticbeanstalk:container:python:
       WSGIPath: run:application
   ```
3. Deploy:
   ```bash
   eb init -p python-3.11
   eb create service-report-env
   eb setenv $(cat .env | tr ' ' '\n' | sed 's/^/--/')
   eb deploy
   ```

**Pros:** Enterprise-grade, auto-scaling, RDS database option  
**Cons:** More complex setup, requires AWS account

---

### **Option C: Azure App Service (Microsoft integration friendly)**

1. Create Azure account
2. Install Azure CLI
3. Create app:
   ```bash
   az webapp up --name myapp --resource-group mygroup --runtime "PYTHON:3.11"
   ```
4. Set environment variables in Azure Portal → Configuration

**Pros:** Integrates with Microsoft ecosystem  
**Cons:** Learning curve

---

### **Option D: Docker + Any Cloud (Most Control)**

1. Create `Dockerfile`:

   ```dockerfile
   FROM python:3.11
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements.txt
   RUN npm ci --prefix frontend && npm run build --prefix frontend
   EXPOSE 5000
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:application"]
   ```

2. Create `.dockerignore` (same as `.gitignore`)

3. Build & push:

   ```bash
   docker build -t myapp .
   docker run -p 5000:8000 -e MONDAY_API_KEY=xxx myapp
   ```

4. Deploy to:
   - **Vercel** (Node-focused, but for App Service wrapper)
   - **Railway** (simple, pay-per-use)
   - **Render** (easy GitHub integration)
   - **DigitalOcean** (affordable VPS)

**Pros:** Works everywhere, reproducible  
**Cons:** Requires Docker knowledge

---

## 3. Pre-Deployment Checklist

### Configuration

- [ ] Create `.env.example` with empty secrets (for team reference)
- [ ] Set `FLASK_DEBUG=False` for production
- [ ] Set `DEBUG=False` in production code
- [ ] Use strong `SECRET_KEY` (already 64-char, good)
- [ ] Configure `REMEMBER_COOKIE_DURATION` appropriately (30 days currently)

### Build

- [ ] Run `npm run build` in `frontend/` (creates `static/dist/`)
- [ ] Test with `gunicorn "run:application"` locally
- [ ] Verify all OAuth URLs point to production domain

### Database

- [ ] Users stored in `users.json` — consider PostgreSQL for scale
- [ ] Move to external database if expect 100+ users

### Static Files

- [ ] `static/dist/` is committed (good for serving)
- [ ] `static/uploads/` should be on persistent storage (S3, Azure Blob, etc.)
- [ ] Signatures auto-upload to Monday.com (handled)

---

## 4. Recommended: Railway.app (Easiest for you)

Given your OAuth setup and simple Python app:

```bash
1. Create Railway account: https://railway.app
2. Connect to your GitHub repo (push your code there first)
3. Railway auto-detects `requirements.txt` → installs Python
4. Set environment variables: MONDAY_API_KEY, MONDAY_OAUTH_CLIENT_ID, SECRET_KEY, etc.
5. Click Deploy
6. Get public URL → update OAuth Redirect URls:
   - Monday.com Apps: https://yourapp.railway.app/auth/monday/callback
   - Google OAuth: https://yourapp.railway.app/auth/google/callback
```

**Billing:** Free tier = 5GB bandwidth/month + $5 credit. Production ~$7-15/month.

---

## 5. Local Production Test

Before deploying, test locally with production settings:

```bash
# Set production env
$env:FLASK_DEBUG=$false
$env:FLASK_ENV='production'

# Run with gunicorn
.\.venv\Scripts\gunicorn.exe --bind 127.0.0.1:8000 --workers 4 "run:application"

# Test at http://127.0.0.1:8000
```

---

## 6. After Deployment

- Set up logs monitoring (Heroku: `heroku logs --tail`)
- Automate secret rotation
- Set up uptime monitoring (Pingdom, Better Uptime)
- Back up `users.json` or migrate to database
- Monitor signature upload bandwidth
