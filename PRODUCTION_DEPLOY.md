# 🚀 Production Deployment Checklist

## 📋 Pre-Deployment Verification

### ✅ Development Testing Complete
- [x] Development environment isolated from production
- [x] Use case toggle working (clinical/exploratory rankings)
- [x] Database operations working correctly
- [x] PubMed search not auto-saving to local database
- [x] Frontend cache issues resolved
- [x] All features tested in development

### 🧪 Final Development Tests

Run these commands to verify everything works:

```bash
# 1. Run automated tests
./dev_env.sh test

# 2. Manual verification
# - Open http://localhost:3000
# - Verify "0 articles found" (development mode)
# - Test PubMed search
# - Test use case toggle
# - Test manual save functionality
```

## 🔄 Production Preparation Steps

### Step 1: Clean Development Environment

```bash
# Stop development servers
./dev_env.sh stop

# Switch back to production mode
./dev_env.sh teardown
```

### Step 2: Code Quality Check

```bash
# Check for linting errors
cd frontend && npm run build
cd ../backend && python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### Step 3: Remove Development Files

```bash
# Verify development files are removed
ls -la frontend/.env.development backend/.env.development 2>/dev/null || echo "✅ No dev files found"

# Remove any temporary files
rm -f backend/dev_msl_research.db
rm -f backend/msl_research_PRODUCTION_BACKUP.db
```

### Step 4: Git Preparation

```bash
# Check git status
git status

# Add all changes
git add .

# Review changes before commit
git diff --cached
```

## 🎯 Deployment Strategy

### Frontend Deployment (Vercel/Netlify)
The frontend will automatically:
- Connect to Railway production backend
- Use production database
- Remove development configurations

### Backend Deployment (Railway)
The backend will automatically:
- Use Railway PostgreSQL database
- Use production environment variables
- Serve production traffic

## 🔒 Production Safety Checklist

### ✅ Environment Variables (Railway Dashboard)
Verify these are set in Railway:

```
OPENAI_API_KEY=your_production_openai_key
SECRET_KEY=your_production_secret_key
DATABASE_URL=provided_by_railway_postgresql
```

### ✅ Database
- Production PostgreSQL will be used (not SQLite)
- Existing production data is preserved
- No development data will be deployed

### ✅ CORS Configuration
Verify production URLs are allowed in `backend/main.py`:
```python
allow_origins=[
    "https://msl-research-tracker.vercel.app",  # Your production frontend
    "http://localhost:3000",  # Development
    "http://localhost:3001"   # Development
],
```

## 🚀 Deployment Commands

### Option 1: Git Push (Automatic Deployment)
```bash
# Commit changes
git commit -m "feat: improved dashboard functionality and development environment"

# Push to production
git push origin main

# Railway will automatically deploy backend
# Vercel will automatically deploy frontend
```

### Option 2: Manual Railway Deployment
```bash
# If you have Railway CLI
railway up
```

## 📊 Post-Deployment Verification

### 1. Backend Health Check
```bash
curl https://your-app.railway.app/health
```

### 2. Frontend Connection
- Open your production frontend URL
- Verify it shows production data (60+ articles)
- Verify no development configurations are active

### 3. Feature Testing
- Test PubMed search
- Test use case toggle
- Test manual save functionality
- Verify reliability scoring

## 🆘 Rollback Plan

If deployment fails:

```bash
# 1. Revert git commit
git revert HEAD

# 2. Push revert
git push origin main

# 3. Or restore development environment
./dev_env.sh setup && ./dev_env.sh start
```

## 📋 Production Monitoring

After deployment, monitor:
- Application logs in Railway dashboard
- Frontend performance in Vercel dashboard
- Database usage and performance
- API response times

## 🔄 Future Development Workflow

For future changes:

```bash
# 1. Setup development
./dev_env.sh setup && ./dev_env.sh start

# 2. Make changes and test

# 3. Deploy to production
./dev_env.sh teardown
git add . && git commit -m "your changes"
git push origin main
```

## ⚠️ Important Notes

- **Development files** (`.env.development`) are never committed to git
- **Production database** remains untouched during development
- **Automatic deployments** happen on git push
- **Zero downtime** deployment via Railway and Vercel
