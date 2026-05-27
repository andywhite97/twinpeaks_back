# Cloudinary Integration Setup Guide

## Step 1: Create a Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com)
2. Sign up for a free account
3. Go to your Dashboard
4. Copy these credentials:
   - **Cloud Name**: Found at the top of dashboard
   - **API Key**: In Settings → API Keys
   - **API Secret**: In Settings → API Keys

## Step 2: Update Environment Variables

Add to your `.env` file:

```env
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

**Replace with your actual credentials from Cloudinary dashboard.**

## Step 3: Set Up on Render

In your Render service dashboard:

1. Go to **Environment**
2. Add these environment variables:
   - `CLOUDINARY_CLOUD_NAME` = your cloud name
   - `CLOUDINARY_API_KEY` = your API key  
   - `CLOUDINARY_API_SECRET` = your API secret

3. Click **Save** and the service will redeploy

## Step 4: How It Works

- All media files (images, videos) uploaded to your Django API will automatically be stored on Cloudinary
- Cloudinary provides CDN delivery - your media loads faster globally
- Files are served from Cloudinary URLs instead of your server
- You get free image transformations (resize, crop, optimize, etc.)

## Step 5: Benefits

✅ **Unlimited Storage** - Up to 2GB on free tier
✅ **CDN Delivery** - Fast worldwide content delivery
✅ **Automatic Optimization** - Images automatically optimized
✅ **Image Transformations** - Resize, crop, filter on-the-fly
✅ **No Server Space** - Saves your backend storage
✅ **Scalable** - Handles high traffic automatically

## Step 6: Test Upload

After deploying:

1. Upload a file through your Django admin or API
2. Check the URL - it will be in format: `https://res.cloudinary.com/your-cloud-name/...`
3. If you see local URL like `/media/...`, check that environment variables are set

## Troubleshooting

**Files still uploading to local storage?**
- Make sure `CLOUDINARY_CLOUD_NAME` is set in environment
- Verify no typos in credentials
- Restart the service after adding env vars

**Images not loading?**
- Check Cloudinary dashboard to see if files are there
- Verify API credentials are correct
- Check CORS settings if needed

## Local Development (Optional)

To test Cloudinary locally:

1. Add credentials to your local `.env`
2. Run: `pip install -r requirements.txt`
3. Upload files - they'll go to Cloudinary
4. All media will be served from Cloudinary URLs

## Pricing

- **Free Tier**: 2GB storage, unlimited bandwidth
- **Pay-as-you-go**: $0.10-0.25 per GB for additional storage
- Perfect for production applications!
