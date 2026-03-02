# GitHub OAuth Setup

## 1. Create a GitHub OAuth App

1. Go to **GitHub Settings** → **Developer settings** → **OAuth Apps**
   - Direct link: https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in:
   - **Application name**: Promptdis (or whatever you want)
   - **Homepage URL**: `http://localhost:5173` (for local dev)
   - **Authorization callback URL**: `http://localhost:8000/api/v1/auth/github/callback`
4. Click **"Register application"**

## 2. Get Your Credentials

After registering:
- **Client ID** is shown immediately on the app page
- **Client Secret**: Click **"Generate a new client secret"** — copy it immediately, it won't be shown again

## 3. Set Them in Your Environment

Add to a `.env` file at the project root:

```bash
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
```

Pydantic Settings (used in `server/config.py`) will pick these up automatically.

## Notes

- For **production**, update the callback URL to your actual domain
- Create separate OAuth apps for local dev vs. production
- The **Client Secret** is sensitive — never commit it to git
