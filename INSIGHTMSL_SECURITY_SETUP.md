# InsightMSL.com Security Setup Guide

This guide details the secure setup for the new `insightmsl.com` domain with a proxy configuration that protects direct access to the Railway backend.

## Architecture Overview

```
Browser → insightmsl.com/api/* → Vercel Proxy → Railway Backend
                               ↓
                        Injects X-Edge-Auth header
```

- **Frontend**: React app hosted on Vercel at `insightmsl.com`
- **Backend**: FastAPI on Railway (protected by middleware)
- **Security**: Secret header validation prevents direct Railway access

## Environment Variables Setup

### 1. Vercel Environment Variables

In your Vercel project settings, add these environment variables:

```bash
BACKEND_BASE=https://msl-research-tracker-production.up.railway.app
EDGE_SECRET=<generate-a-strong-random-string>
```

**To generate a strong EDGE_SECRET:**
```bash
# Option 1: Using openssl
openssl rand -base64 32

# Option 2: Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"

# Option 3: Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Railway Environment Variables

In your Railway service settings, add:

```bash
EDGE_SECRET=<same-value-as-vercel>
```

⚠️ **Important**: The `EDGE_SECRET` must be identical on both platforms.

## Security Features Implemented

### 1. Vercel Proxy (`/frontend/api/[...path].js`)
- Catches all `/api/*` requests
- Forwards to Railway backend with injected `X-Edge-Auth` header
- Handles all HTTP methods (GET, POST, PUT, DELETE, etc.)
- Includes proper error handling and logging

### 2. Security Headers (`/frontend/vercel.json`)
- **HSTS**: `Strict-Transport-Security` for HTTPS enforcement
- **XFO**: `X-Frame-Options: DENY` prevents clickjacking
- **CSP**: Content Security Policy restricts resource loading
- **CSRF**: `X-Content-Type-Options: nosniff`
- **Permissions**: Restricts camera, microphone, geolocation

### 3. Backend Authentication Middleware (`/backend/middleware/auth_edge.py`)
- Validates `X-Edge-Auth` header on all API requests
- Blocks direct access without the secret header
- Logs unauthorized access attempts
- Excludes health check and docs endpoints

### 4. CORS Configuration
- Restricted to `insightmsl.com` and `www.insightmsl.com`
- Maintains localhost for development
- No wildcard origins

## Testing the Setup

### 1. Test Security Headers
```bash
curl -I https://insightmsl.com/
```

**Expected headers:**
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`

### 2. Test API Proxy (Should Work)
```bash
# Health check through proxy
curl -I https://insightmsl.com/api/health

# Recent articles through proxy
curl https://insightmsl.com/api/articles/recent
```

**Expected**: 200 OK with valid JSON response

### 3. Test Direct Backend Access (Should Fail)
```bash
# Direct access without header (should return 403)
curl -I https://msl-research-tracker-production.up.railway.app/api/health
```

**Expected**: `403 Forbidden`

### 4. Test Direct Backend with Header (Should Work)
```bash
# Direct access with secret header (for verification)
curl -I -H "X-Edge-Auth: YOUR_EDGE_SECRET" https://msl-research-tracker-production.up.railway.app/api/health
```

**Expected**: `200 OK`

## Deployment Steps

### 1. Deploy Frontend to Vercel
```bash
cd frontend
# Ensure environment variables are set in Vercel dashboard
# Deploy will automatically use the new proxy configuration
```

### 2. Deploy Backend to Railway
```bash
# Ensure EDGE_SECRET is set in Railway dashboard
# The middleware will automatically protect all API routes
```

### 3. Update DNS
- Point `insightmsl.com` to Vercel
- Configure any necessary CNAME records

## Security Best Practices

### 1. Secret Rotation
- Rotate `EDGE_SECRET` periodically (monthly recommended)
- Update both Vercel and Railway simultaneously
- Consider implementing secret versioning for zero-downtime rotation

### 2. Monitoring
- Monitor Railway logs for unauthorized access attempts
- Set up alerts for 403 responses
- Track response times through the proxy

### 3. Additional Security Measures
- Enable Vercel's DDoS protection
- Consider adding rate limiting to the proxy
- Implement request logging for audit trails

## Troubleshooting

### Frontend Issues
- **502 Bad Gateway**: Check Railway backend health
- **500 Server Error**: Verify environment variables in Vercel
- **CORS Errors**: Ensure domain is added to backend CORS config

### Backend Issues
- **403 Forbidden**: Check `EDGE_SECRET` matches on both platforms
- **Missing middleware**: Ensure `EdgeAuthMiddleware` is properly imported
- **Health check fails**: Verify excluded paths in middleware

### Environment Variable Issues
```bash
# Verify on Vercel
vercel env ls

# Check Railway logs for startup errors
# Look for "Server misconfiguration: EDGE_SECRET not set"
```

## Files Modified

### Frontend
- `frontend/api/[...path].js` - New proxy function
- `frontend/src/App.js` - Updated axios baseURL
- `frontend/vercel.json` - Added security headers

### Backend
- `backend/middleware/__init__.py` - New middleware package
- `backend/middleware/auth_edge.py` - New authentication middleware
- `backend/main.py` - Added middleware and updated CORS

## Development vs Production

### Development (localhost)
- Proxy still works for consistency
- CORS allows localhost origins
- Edge auth middleware is active but logs attempts

### Production (insightmsl.com)
- All security measures fully active
- Only verified domain in CORS
- Direct Railway access blocked

This setup ensures maximum security while maintaining development flexibility.
