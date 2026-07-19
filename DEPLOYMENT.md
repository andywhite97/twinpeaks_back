# Twinpeaks Backend Deployment Checklist

## Pre-Deployment Setup ✅

### Configuration Files Created:
- ✅ `.env` - Environment variables
- ✅ `render.yaml` - Render infrastructure configuration
- ✅ `requirements.txt` - Python dependencies
- ✅ `build.sh` - Build script for Render
- ✅ `Procfile` - Web process definition
- ✅ `.gitignore` - Protect sensitive files

### Django Configuration:
- ✅ Settings updated for production
- ✅ Database configured for PostgreSQL
- ✅ CORS configured for frontend (GitHub Pages)
- ✅ Static files configuration ready

## Required Before Deployment 🔧

### 1. Update `.env` with Real Values:
```ini
# Update these with actual values:
EMAIL_HOST_USER=your-actual-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
BIRD_API_KEY=your-messagebird-api-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,twinpeaks-api.render.com
```

### 2. Generate a New DJANGO_SECRET_KEY:
Use Python to generate a secure key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Then update in `render.yaml` and `.env`.

### 3. Commit to GitHub:
```bash
git add .
git commit -m "Configure backend for Render deployment"
git push origin main
```

## Deployment Steps on Render 🚀

### Step 1: Create Render Account
- Go to [render.com](https://render.com)
- Sign up/login with GitHub

### Step 2: Deploy Using Blueprint
- Click **"New +"** → **"Blueprint"**
- Select your GitHub repository
- Confirm `render.yaml` is detected
- Click **"Deploy"**

### Step 3: Set Environment Variables
After deployment, go to your web service and add secret variables:
- `DJANGO_SECRET_KEY` - Copy from `.env`
- `EMAIL_HOST_USER` - Your Gmail
- `EMAIL_HOST_PASSWORD` - Gmail app password
- `BIRD_API_KEY` - Your MessageBird API key

### Step 4: Monitor Build
- Check the build logs in Render dashboard
- Verify migrations run successfully
- Check for any errors

### Step 5: Test the API
Once deployed:
```bash
curl https://twinpeaks-api.render.com/api/auth/login/
```

### Step 6: Start Celery Worker
If your deployment uses Celery for email and background jobs, add a worker service and set the broker URL.
- `CELERY_BROKER_URL=redis://<user>:<password>@<host>:<port>/<db>`
- `CELERY_TASK_ALWAYS_EAGER=False`

Render worker command example:
```bash
celery -A twinpeaks worker --loglevel=info
```

If your broker is Redis, also add it as a Render service or use a managed Redis provider.

## Deployment URLs

- **Backend API:** `https://twinpeaks-api.render.com`
- **Admin Panel:** `https://twinpeaks-api.render.com/admin/`
- **Frontend:** `https://andywhite97.github.io/twinpeaks`

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login/` | POST | Get JWT tokens |
| `/api/auth/refresh/` | POST | Refresh JWT token |
| `/admin/` | GET | Django admin dashboard |

## Post-Deployment Tasks ✓

- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Test login endpoint
- [ ] Verify CORS headers are correct
- [ ] Test email sending (if applicable)
- [ ] Monitor error logs
- [ ] Set up automatic backups

## Troubleshooting

### Build Failures:
- Check `requirements.txt` syntax
- Verify Python version compatibility
- Check for missing dependencies

### Database Connection Issues:
- Verify `DATABASE_URL` format
- Check Render database is running
- Confirm network access rules

### CORS Errors:
- Update `CORS_ALLOWED_ORIGINS` in Render
- Include frontend URL (with protocol)
- Restart the service

### Static Files Not Loading:
- Collectstatic runs automatically in `build.sh`
- Check media folder permissions
- Verify `STATIC_URL` and `MEDIA_URL` settings

## Important Notes

⚠️ **DO NOT** commit `.env` to GitHub (it's in `.gitignore`)
⚠️ Keep DJANGO_SECRET_KEY secret - don't expose in logs
⚠️ Use environment variables for sensitive data in Render dashboard
⚠️ Enable auto-deploy for continuous deployment on git push

## Support

For Render-specific help: https://render.com/docs
For Django deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/
