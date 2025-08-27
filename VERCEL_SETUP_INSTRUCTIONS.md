# Vercel Environment Variables Setup for InsightMSL.com

## 🚨 **Critical Setup Required**

Your Vercel deployment is now live, but the API proxy needs environment variables to work correctly.

## 📋 **Required Environment Variables**

You need to set these in your Vercel project dashboard:

### **1. BACKEND_BASE**
- **Value:** `https://msl-research-tracker-production.up.railway.app`
- **Description:** URL of your Railway backend

### **2. EDGE_SECRET**
- **Value:** Generate a strong secret (32+ characters)
- **Description:** Secret header to authenticate Vercel → Railway requests

## 🔐 **Generate EDGE_SECRET**

Choose one method to generate a strong secret:

```bash
# Option 1: Using openssl (Mac/Linux)
openssl rand -base64 32

# Option 2: Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"

# Option 3: Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example generated secret:** `kJ8n2mP9xR4vL7qE3wT6yU1iO5aS8dF0gH9jK2lN5pQ=`

## 🚀 **Step-by-Step Setup**

### **Step 1: Access Vercel Dashboard**
1. Go to https://vercel.com/dashboard
2. Click on your MSL project
3. Click the "Settings" tab
4. Click "Environment Variables" in the left sidebar

### **Step 2: Add Variables**

**Add BACKEND_BASE:**
1. Click "Add New"
2. Name: `BACKEND_BASE`
3. Value: `https://msl-research-tracker-production.up.railway.app`
4. Environments: Check **Production**, **Preview**, and **Development**
5. Click "Save"

**Add EDGE_SECRET:**
1. Click "Add New"
2. Name: `EDGE_SECRET`
3. Value: Your generated secret (keep this safe!)
4. Environments: Check **Production**, **Preview**, and **Development**
5. Click "Save"

### **Step 3: Add Same Secret to Railway**
1. Go to https://railway.app/dashboard
2. Click on your MSL backend project
3. Click on your service
4. Click "Variables" tab
5. Add `EDGE_SECRET` with the **same value** as Vercel
6. Click "Deploy" if needed

### **Step 4: Redeploy Frontend**
After setting environment variables, trigger a redeploy:
1. In Vercel dashboard → Deployments tab
2. Click "..." on latest deployment → "Redeploy"
3. Wait for deployment to complete

## 🧪 **Test After Setup**

Once environment variables are set and redeployed:

```bash
# Test API proxy (should return JSON, not HTML)
curl https://www.insightmsl.com/api/health

# Test protected endpoint (should work through proxy)
curl https://www.insightmsl.com/api/articles/recent

# Test direct Railway access (should be blocked)
curl https://msl-research-tracker-production.up.railway.app/api/articles/recent
```

## ⚠️ **Current Status**

**✅ Frontend:** Deployed and loading  
**✅ Railway Backend:** Health check fix deployed  
**❌ API Proxy:** Needs environment variables  
**❌ App Functionality:** Will work once proxy is configured  

## 🔧 **Why App Shows Error**

The `TypeError: t.map is not a function` error occurs because:

1. Frontend tries to load articles via `/api/articles/recent`
2. API proxy has no environment variables configured
3. Proxy fails and returns error/HTML instead of JSON array
4. React tries to `.map()` over non-array data
5. Error: "t.map is not a function"

**This will be fixed once environment variables are set!**

## 🎯 **Next Steps**

1. **Set environment variables** (steps above)
2. **Redeploy** Vercel project
3. **Test API endpoints** work correctly
4. **Verify app functionality** returns to normal

Your security improvements are working perfectly - we just need to complete the environment variable setup! 🛡️
