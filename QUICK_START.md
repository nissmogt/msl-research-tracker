# 🚀 MSL Research Tracker - Quick Start Guide

## ⚡ 30-Second Development Setup

```bash
# 1. Setup development environment
./dev_env.sh setup

# 2. Start development (both frontend & backend)
./dev_env.sh start

# 3. Open browser to http://localhost:3000
# ✅ You should see "0 articles found" (not 60 from production)
```

## 🎯 One-Liner Commands

| Command | Purpose |
|---------|---------|
| `./dev_env.sh setup` | Create isolated dev environment |
| `./dev_env.sh start` | Start frontend + backend |
| `./dev_env.sh status` | Check what's running |
| `./dev_env.sh test` | Verify everything works |
| `./dev_env.sh stop` | Stop development servers |
| `./dev_env.sh clear-db` | Clear development database |
| `./dev_env.sh teardown` | Switch back to production |

## 🛡️ Safety Features

- ✅ **Isolated Database**: `dev_msl_research.db` (separate from production)
- ✅ **Local API**: `localhost:8000` (not Railway production)
- ✅ **Zero Risk**: Production data completely protected
- ✅ **Easy Switch**: `teardown` returns to production mode

## 🧪 What to Test

1. **Database Isolation**: Should show "0 articles found"
2. **PubMed Search**: Works but doesn't auto-save
3. **Use Case Toggle**: Clinical/Exploratory changes scores
4. **Manual Save**: Save button adds to local database only
5. **Speed UX**: recent-search chips + response caching should make repeat searches feel near-instant
6. **Result Control**: Top-N selector (5/10/15/20) should change returned list size

## 🔄 Quick Workflow

```bash
# Start development
./dev_env.sh setup && ./dev_env.sh start

# Make changes, test features...

# Clear database when needed
./dev_env.sh clear-db

# Switch back to production
./dev_env.sh teardown
```

## 🆘 Emergency Reset

```bash
# Nuclear option - restore production mode
./dev_env.sh destruct
```

## 📋 Verification Checklist

**✅ Frontend (http://localhost:3000):**
- Shows "0 articles found" (not 60)
- Console shows "Frontend connecting to: http://localhost:8000"
- Use case toggle changes rankings

**✅ Backend (http://localhost:8000):**
- Health check responds
- Debug endpoint shows 0 articles
- PubMed search works

**✅ Safety:**
- Development database is isolated
- Production Railway server untouched
- No risk to live data

Read [DEV_README.md](DEV_README.md) for detailed instructions.
