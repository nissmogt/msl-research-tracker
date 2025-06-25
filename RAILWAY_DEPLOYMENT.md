# Railway Deployment Guide

## Environment Variables Required

Set these environment variables in your Railway project dashboard:

### Required Variables:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - A secure random string for JWT signing (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

### Optional Variables:
- `DATABASE_URL` - Railway will provide this automatically if you add a PostgreSQL database
- `FRONTEND_URL` - Your frontend URL (e.g., Vercel deployment URL)

## Deployment Steps

1. **Connect your GitHub repository to Railway**
2. **Add a PostgreSQL database** (recommended for production)
3. **Set environment variables** in Railway dashboard
4. **Deploy** - Railway will automatically detect the Python project and deploy

## Generate Secret Key

Run this command to generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Health Check

The application includes a health check endpoint at `/` that Railway uses to verify the service is running.

## Database Migration

The application will automatically create database tables on first run using SQLAlchemy's `create_all()`.

## CORS Configuration

The API is configured to accept requests from:
- Local development (localhost:3000, localhost:3001)
- Railway domains (*.railway.app)
- Vercel domains (*.vercel.app)
- Netlify domains (*.netlify.app)
- Custom frontend URL (set via FRONTEND_URL env var)

## API Documentation

Once deployed, you can access the API documentation at:
- Swagger UI: `https://your-app.railway.app/docs`
- ReDoc: `https://your-app.railway.app/redoc` 