# Deploying ServaAI to Vultr + servaai.us

About 20 minutes. If anything fails before 9:00 AM, demo from the laptop instead
(`.venv/Scripts/python -m uvicorn backend.app:app --port 8000`, then open http://localhost:8000).

## 1. Create the server (Vultr)
- Deploy a new **Cloud Compute** instance: **Ubuntu 24.04 x64**, 2 vCPU / 4 GB RAM (the forecast
  model trains once at startup), the region closest to Toronto.
- Add your SSH key, or note the root password Vultr shows.
- Copy the server's **IPv4 address**.

## 2. Point the domain at it
Where servaai.us is managed (currently parked on Articulation), replace the parking records with:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | @ | the Vultr IPv4 | 600 |
| A | www | the Vultr IPv4 | 600 |

Delete any old A / CNAME / URL-forward records for `@` and `www`. DNS usually updates within minutes.

## 3. Copy the data and the key (from the repo folder on your laptop)
```bash
ssh root@SERVER_IP "mkdir -p /opt/servaai/backend /opt/servaai/data"
```
```bash
scp data/*.csv data/README.md root@SERVER_IP:/opt/servaai/data/
```
```bash
scp backend/.env root@SERVER_IP:/opt/servaai/backend/.env
```

## 4. Run the setup script on the server
```bash
ssh root@SERVER_IP
```
```bash
curl -fsSLo setup_vultr.sh https://raw.githubusercontent.com/SqualidRat560/servaai/main/deploy/setup_vultr.sh && sudo bash setup_vultr.sh YOUR_EMAIL
```
It installs Docker, nginx and certbot, builds the app, waits until the engine answers, configures
nginx and gets the HTTPS certificate. If DNS has not reached the server yet it says so and prints
the one certbot command to run later.

## 5. Smoke test (phone too)
- https://servaai.us loads, account 63816, twist card 3 → **Judge 3.1, realistic 1.9**.
- https://servaai.us/#/portfolio shows **32.8%** and the galaxy.
- https://servaai.us/api/health → `{"ok":true,"accounts":4500}`.

## Updating after a code change
```bash
cd /opt/servaai && git pull && docker compose up -d --build
```

## If something goes wrong
- `docker compose logs --tail 100` shows app errors.
- `sudo nginx -t` checks the nginx config; `sudo systemctl reload nginx` applies it.
- Gemini down? The app falls back to the built-in parser automatically.
