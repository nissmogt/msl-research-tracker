# 🚀 MSL Research Tracker - Deployment Guide

## ⚡ Fastest Deployment Options (Ranked by Speed)

### 1. **Railway (Recommended - 10 minutes)**

**Why Railway?** Free tier, automatic deployments, handles both frontend/backend, zero config.

#### Quick Deploy:
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Initialize project
railway init

# 4. Deploy
railway up
```

#### Environment Variables (set in Railway dashboard):
```
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-generated-secret-key
DATABASE_URL=sqlite:///./msl_research.db
```

### 2. **Render (15 minutes)**

**Why Render?** Free tier, automatic deployments, good for full-stack apps.

#### Steps:
1. Connect your GitHub repo to Render
2. Create new **Web Service**
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### 3. **Vercel + Railway (20 minutes)**

**Why this combo?** Vercel for frontend (super fast), Railway for backend.

#### Frontend (Vercel):
```bash
cd frontend
npm install -g vercel
vercel
```

#### Backend (Railway):
```bash
cd backend
railway up
```

### 4. **Heroku (30 minutes)**

**Why Heroku?** Traditional, well-established, good documentation.

#### Steps:
```bash
# 1. Install Heroku CLI
# 2. Login
heroku login

# 3. Create app
heroku create your-msl-app

# 4. Set environment variables
heroku config:set OPENAI_API_KEY=your-key
heroku config:set SECRET_KEY=your-secret

# 5. Deploy
git push heroku main
```

## 🔧 Pre-Deployment Setup

### 1. Generate Secret Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Initialize Database
```bash
cd backend
python init_db.py
```

### 3. Test Locally
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm start
```

## 🌍 Environment Variables

Set these in your deployment platform:

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `SECRET_KEY` | JWT signing key | Generated secret |
| `DATABASE_URL` | Database connection | `sqlite:///./msl_research.db` |

## 📊 Deployment Comparison

| Platform | Speed | Cost | Difficulty | Features |
|----------|-------|------|------------|----------|
| **Railway** | ⚡⚡⚡ | Free | Easy | Auto-deploy, DB included |
| **Render** | ⚡⚡ | Free | Easy | Auto-deploy, good docs |
| **Vercel+Railway** | ⚡⚡ | Free | Medium | Best performance |
| **Heroku** | ⚡ | $7/month | Medium | Traditional, reliable |

## 🚨 Common Issues & Solutions

### 1. **CORS Errors**
- Ensure frontend URL is in CORS origins
- Check that backend is running on correct port

### 2. **Database Issues**
- Use PostgreSQL for production (Railway/Render provide this)
- Update DATABASE_URL to use provided database

### 3. **Port Issues**
- Use `$PORT` environment variable
- Don't hardcode port numbers

### 4. **Dependencies**
- Ensure all requirements are in `requirements.txt`
- Check Python version compatibility

## 🎯 Recommended: Railway Deployment

### Step-by-Step:

1. **Prepare your code:**
   ```bash
   # Generate secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Initialize database
   cd backend
   python init_db.py
   ```

2. **Deploy to Railway:**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and deploy
   railway login
   railway init
   railway up
   ```

3. **Set environment variables in Railway dashboard:**
   - `OPENAI_API_KEY`
   - `SECRET_KEY`
   - `DATABASE_URL` (Railway provides this)

4. **Access your app:**
   - Backend API: `https://your-app.railway.app`
   - API Docs: `https://your-app.railway.app/docs`

## 🔄 Post-Deployment

1. **Test the API endpoints** at `/docs`
2. **Initialize the database** with therapeutic areas
3. **Test PubMed integration**
4. **Set up monitoring** (Railway provides this)

## 💡 Pro Tips

- **Use Railway's PostgreSQL** instead of SQLite for production
- **Set up automatic deployments** from GitHub
- **Monitor your app** using Railway's dashboard
- **Use environment-specific configs** for dev/staging/prod

## 🆘 Need Help?

- **Railway Docs:** https://docs.railway.app
- **Render Docs:** https://render.com/docs
- **Vercel Docs:** https://vercel.com/docs
- **Heroku Docs:** https://devcenter.heroku.com

---

**🎉 Your MSL Research Tracker will be live in under 15 minutes!** 