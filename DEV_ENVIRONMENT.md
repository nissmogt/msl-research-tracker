# 🔧 Development Environment Setup

## 🚨 CRITICAL: Separating Development from Production

**The current setup has a SERIOUS ISSUE**: the frontend defaults to connecting to your production Railway server, which means development work could accidentally affect production data!

## 📋 Project Manager Assessment

### 🔴 Current Risks:
- Frontend defaults to production Railway URL
- No isolated development database
- Shared configurations between dev/prod
- Risk of accidentally modifying production data
- No environment separation

### ✅ Required Fixes:
1. **Isolated Development Database**
2. **Environment-Specific Configurations** 
3. **Separate Frontend/Backend URLs**
4. **Development Safety Guards**
5. **Clear Dev/Prod Separation**

## 🛠️ SOLUTION: Proper Development Environment

### Step 1: Run Development Setup

```bash
# Run the automated development setup
python dev_setup.py
```

This creates:
- `backend/.env.development` - Development backend config
- `frontend/.env.development` - Development frontend config  
- `backend/config_dev.py` - Development settings
- Development startup scripts
- Isolated development database

### Step 2: Manual Frontend Environment File

Since `.env` files are blocked, create this manually:

**Create: `frontend/.env.development`**
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
GENERATE_SOURCEMAP=true
```

### Step 3: Backend Development Configuration

**Create: `backend/.env.development`**
```
DATABASE_URL=sqlite:///./dev_msl_research.db
ENVIRONMENT=development
PORT=8000
SECRET_KEY=dev_secret_key_not_for_production
```

## 🔄 Development Workflow

### Safe Development Process:

1. **Start Development Backend:**
   ```bash
   cd backend
   export ENVIRONMENT=development
   python main.py
   ```

2. **Start Development Frontend:**
   ```bash
   cd frontend
   # With .env.development file, this will connect to localhost:8000
   npm start
   ```

3. **Verify Environment:**
   - Check browser console for: `🌐 Frontend connecting to: http://localhost:8000`
   - Backend should show: `📁 Using development database: dev_msl_research.db`

## 🛡️ Safety Features

### Database Isolation:
- **Development**: `dev_msl_research.db` (local only)
- **Production**: Railway PostgreSQL (untouched)

### URL Isolation:
- **Development**: `http://localhost:8000` 
- **Production**: `https://msl-research-tracker-production.up.railway.app`

### Configuration Isolation:
- **Development**: Local `.env.development` files
- **Production**: Railway environment variables

## 🔍 How to Verify You're in Development Mode

### Frontend Verification:
```javascript
// Check browser console for:
🌐 Frontend connecting to: http://localhost:8000
📦 Environment: development
🔧 React App Environment: development
```

### Backend Verification:
```bash
# Terminal should show:
🔧 DEVELOPMENT MODE ACTIVE
📁 Database: sqlite:///./dev_msl_research.db
🌐 API Port: 8000
⚠️  This is DEVELOPMENT mode - isolated from production
```

## 🚀 Production Deployment

When ready for production:

1. **Remove development files:**
   ```bash
   rm frontend/.env.development
   rm backend/.env.development
   ```

2. **Deploy normally:**
   - Frontend automatically connects to Railway production
   - Backend uses Railway environment variables
   - Production database remains untouched

## 🎯 Testing the Fix

### Before Development Setup:
- Frontend shows: "60 articles found" (from production)
- Data comes from Railway production server
- Risk of affecting production data

### After Development Setup:
- Frontend shows: "0 articles found" (from empty dev database)
- Data comes from local `dev_msl_research.db`
- Zero risk to production data

## 📞 Project Manager Recommendations

1. **NEVER work directly against production** 
2. **Always use development environment for testing**
3. **Verify environment before making changes**
4. **Keep development database separate**
5. **Test thoroughly in dev before production deployment**

This setup ensures your production Railway deployment remains completely safe while you develop and test new features locally.
