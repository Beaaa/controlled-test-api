# Deployment Guide — Controlled Test API

## Deploy to Render (recommended)

### Option A — Blueprint (render.yaml)

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New → Blueprint**
4. Connect your GitHub repo
5. Render reads `render.yaml` and creates the service automatically

### Option B — Manual setup

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python seed.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**

### Environment Variables (optional)

| Variable         | Default                                      | Description          |
|------------------|----------------------------------------------|----------------------|
| `PYTHON_VERSION` | `3.13`                                       | Python runtime       |

---

## URLs (fill in after deploy)

| Resource         | URL                                          |
|------------------|----------------------------------------------|
| **Base URL**     | `https://<your-service>.onrender.com`        |
| **Swagger UI**   | `https://<your-service>.onrender.com/docs`   |
| **ReDoc**        | `https://<your-service>.onrender.com/redoc`  |
| **OpenAPI JSON** | `https://<your-service>.onrender.com/openapi.json` |
| **Health**       | `https://<your-service>.onrender.com/health` |
| **Metrics**      | `https://<your-service>.onrender.com/metrics`|

---

## Auth Credentials (seeded users)

| Username         | Password        | Notes                    |
|------------------|-----------------|--------------------------|
| `alice`          | `password123`   | Normal user              |
| `bob`            | `bobsecure!`    | Normal user              |
| `charlie`        | `charlie99`     | Normal user              |
| `diana`          | `d1@naPass`     | Normal user              |
| `eve`            | `ev3Sec!`       | Normal user              |
| `a`              | `shortname`     | Edge case — 1-char name  |
| `xxxx...` (x50)  | `maxuser!`      | Edge case — max length   |
| `user-with-dashes` | `dashes123`   | Edge case — dashes       |
| `user.dots`      | `dots1234`      | Edge case — dots         |
| `UPPERCASE`      | `upper123`      | Edge case — caps         |

### How to authenticate

```bash
# 1. Login
TOKEN=$(curl -s -X POST https://<your-service>.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}' | jq -r '.access_token')

# 2. Use the token
curl -H "Authorization: Bearer $TOKEN" https://<your-service>.onrender.com/tasks
```

---

## Important Notes

- **Free tier:** Render free instances spin down after 15 min of inactivity.
  First request after spin-down takes ~30 s (cold start + seed).
- **SQLite on Render:** The DB resets on every deploy/restart (ephemeral disk).
  This is intentional — `seed.py` runs on every start to repopulate.
- **HTTPS:** Enabled automatically by Render on all services.
