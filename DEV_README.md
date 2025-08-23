# 🔧 MSL Research Tracker - Development Environment

## 🚨 IMPORTANT: Development vs Production Safety

This guide helps you set up a **completely isolated** development environment that is **100% safe** from your production Railway deployment.

## 🎯 Quick Start (1-Minute Setup)

```bash
# 1. Run the automated setup script
./dev_env.sh setup

# 2. Start development (opens in separate terminals)
./dev_env.sh start

# 3. Open browser to http://localhost:3000
```

## 📋 Manual Step-by-Step Instructions

### Step 1: Environment Setup

```bash
# Generate development environment files
./dev_env.sh setup
```

This creates:
- `frontend/.env.development` → Forces frontend to localhost:8000
- `backend/.env.development` → Uses isolated dev database
- Development configuration files

### Step 2: Start Backend (Terminal 1)

```bash
cd backend
python main.py
```

You should see:
```
📚 Journal database already contains X journals
INFO: Started server process
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Start Frontend (Terminal 2)

```bash
cd frontend
npm start
```

You should see:
```
Compiled successfully!
Local: http://localhost:3000
```

### Step 4: Verify Development Mode

**Open http://localhost:3000 and check:**

1. **Browser Console** should show:
   ```
   🌐 Frontend connecting to: http://localhost:8000
   📦 Environment: development
   ```

2. **UI should show**:
   - "0 articles found" (not 60 from production)
   - Local Database radio button selected
   - Use case toggles working

3. **Backend verification**:
   ```bash
   curl http://localhost:8000/debug/db-count
   # Should return: {"article_count":0}
   ```

## 🧪 Testing Features

### Test 1: Database Isolation
```bash
# Check development database is empty
curl http://localhost:8000/debug/db-count
# Expected: {"article_count":0}

# Check production is untouched (different URL)
# Your production Railway server still has 60+ articles
```

### Test 2: PubMed Search (No Auto-Save)
1. Switch to "PubMed Search" mode
2. Search for "cardiology"
3. Articles appear but DON'T save to local database
4. Switch back to "Local Database" → still 0 articles

### Test 3: Use Case Toggle
1. Search PubMed for "neurology"
2. Note reliability scores
3. Toggle between "Clinical" and "Exploratory"
4. Scores should change dynamically

### Test 4: Manual Save
1. Search PubMed for articles
2. Click "Save Article" button on specific articles
3. Check local database count increases
4. Switch to "Local Database" to see saved articles

## 🔄 Environment Management

### Quick Commands

```bash
# Setup development environment
./dev_env.sh setup

# Start both frontend and backend
./dev_env.sh start

# Stop all development processes
./dev_env.sh stop

# Clear development database
./dev_env.sh clear-db

# Switch back to production mode
./dev_env.sh teardown

# Show current status
./dev_env.sh status
```

### Manual Environment Control

```bash
# Switch to development mode
echo "REACT_APP_API_URL=http://localhost:8000" > frontend/.env.development
echo "DATABASE_URL=sqlite:///./dev_msl_research.db" > backend/.env.development

# Switch back to production mode
rm frontend/.env.development backend/.env.development
```

## 🛡️ Safety Verification

### Before Starting Development
Always verify you're in development mode:

```bash
# 1. Check environment files exist
ls -la frontend/.env.development backend/.env.development

# 2. Check backend connects to dev database
curl http://localhost:8000/debug/db-count

# 3. Check frontend console shows localhost:8000
# Open browser developer tools and verify connection URL
```

### Production Safety Checklist
- ✅ Development uses `dev_msl_research.db` (local file)
- ✅ Production uses Railway PostgreSQL (cloud)
- ✅ Development connects to `localhost:8000`
- ✅ Production connects to `railway.app`
- ✅ No shared data between environments

## 🔧 Troubleshooting

### Issue: Frontend still shows 60 articles
**Solution:**
```bash
# 1. Verify .env.development exists
cat frontend/.env.development
# Should show: REACT_APP_API_URL=http://localhost:8000

# 2. Restart frontend
cd frontend && npm start

# 3. Hard refresh browser (Cmd+Shift+R)
```

### Issue: Backend not using dev database
**Solution:**
```bash
# 1. Verify backend .env.development
cat backend/.env.development
# Should show: DATABASE_URL=sqlite:///./dev_msl_research.db

# 2. Restart backend
cd backend && python main.py
```

### Issue: Port conflicts
**Solution:**
```bash
# Kill existing processes
pkill -f "python main.py"
pkill -f "react-scripts"

# Restart from scratch
./dev_env.sh stop
./dev_env.sh start
```

## 📊 Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| **Frontend URL** | http://localhost:3000 | https://your-app.vercel.app |
| **Backend URL** | http://localhost:8000 | https://your-app.railway.app |
| **Database** | `dev_msl_research.db` | Railway PostgreSQL |
| **Data** | 0 articles (empty) | 60+ articles (live) |
| **Safety** | 🛡️ Isolated | 🛡️ Protected |

## 🚀 Deployment to Production

When ready to deploy changes:

```bash
# 1. Test thoroughly in development
./dev_env.sh test

# 2. Switch back to production mode
./dev_env.sh teardown

# 3. Commit and push changes
git add .
git commit -m "feature: your changes"
git push

# 4. Production automatically deploys via Railway
```

## 📝 Development Workflow

1. **Start development**: `./dev_env.sh setup && ./dev_env.sh start`
2. **Make changes**: Edit code with live reload
3. **Test features**: Use isolated development environment
4. **Clear data**: `./dev_env.sh clear-db` when needed
5. **Deploy**: `./dev_env.sh teardown` then commit/push

## ⚠️ Important Notes

- **Never commit** `.env.development` files to git
- **Always verify** you're in development mode before testing
- **Use teardown** before deploying to production
- **Production data** is always safe and isolated

## 🆘 Emergency: Restore Production Mode

If something goes wrong:

```bash
# Nuclear option - restore production mode
rm -f frontend/.env.development backend/.env.development
pkill -f "python main.py"
pkill -f "react-scripts"

# Verify production mode
# Frontend should connect to Railway URL again
```
