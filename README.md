# 📲 WhatsApp Admissions Bot

A WhatsApp chatbot built with Flask + WhatsApp Cloud API that captures student leads and saves them to Google Sheets (with CSV backup).

---

## 🗂 Project Structure

```
whatsapp-bot/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── Procfile                  # For Render/Heroku deployment
├── .env.example              # Environment variable template
├── .gitignore
├── google_credentials.json   # ← You create this (NOT committed to git)
├── user_states.json          # Auto-created at runtime
└── leads.csv                 # Auto-created CSV backup
```

---

## ✅ Features

- Conversational flow: Program → Eligibility → Course → Name
- Saves leads to **Google Sheets** (live) + **CSV** (backup)
- Input validation with helpful error messages
- Proper logging for debugging
- `/health` endpoint for uptime monitoring
- Production-ready with Gunicorn

---

## 🚀 Step-by-Step Setup

### Step 1 — WhatsApp Cloud API Setup

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a **Meta App** → Add **WhatsApp** product
3. Under WhatsApp → API Setup, note:
   - `Phone Number ID`
   - `Access Token` (temporary, or generate a permanent one via System User)
4. Make up any string for `VERIFY_TOKEN` (e.g. `mybot_verify_123`)

---

### Step 2 — Google Sheets Setup

#### A) Create the Sheet
1. Go to [sheets.google.com](https://sheets.google.com)
2. Create a new spreadsheet named **"Admissions Leads"**
3. Copy the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   ```

#### B) Create a Service Account
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
5. Name it `whatsapp-bot`, click Create
6. Click the service account → **Keys tab → Add Key → JSON**
7. Download the JSON file and rename it to `google_credentials.json`
8. Place it in the project root folder

#### C) Share the Sheet with Service Account
1. Open your Google Sheet
2. Click **Share**
3. Add the service account email (looks like `whatsapp-bot@project-id.iam.gserviceaccount.com`)
4. Give it **Editor** access

---

### Step 3 — Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
ACCESS_TOKEN=EAAxxxxxxxxxxxxx
PHONE_NUMBER_ID=123456789012345
VERIFY_TOKEN=mybot_verify_123
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
GOOGLE_CREDENTIALS_FILE=google_credentials.json
PORT=5000
```

---

### Step 4 — Deploy to Render (Free/Paid)

1. Push your project to GitHub (make sure `.env` and `google_credentials.json` are in `.gitignore`)
2. Go to [render.com](https://render.com) → New → **Web Service**
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
5. Under **Environment Variables**, add all the variables from `.env`
6. For `google_credentials.json` — go to **Environment → Secret Files**:
   - Filename: `google_credentials.json`
   - Content: paste the full JSON content from your downloaded file
7. Deploy → copy the public URL (e.g. `https://your-bot.onrender.com`)

> **Alternative platforms:** Railway, Heroku, Fly.io, or any VPS with Python support.

---

### Step 5 — Register Webhook with Meta

1. Go to Meta Developer Console → Your App → WhatsApp → Configuration
2. Set **Webhook URL**: `https://your-bot.onrender.com/webhook`
3. Set **Verify Token**: same string you put in `VERIFY_TOKEN`
4. Click **Verify and Save**
5. Subscribe to the `messages` webhook field

---

### Step 6 — Test It

Send a WhatsApp message to your test number. You should see:

```
👋 Welcome to Admissions Bot!

Please choose a Program:
1️⃣ UG Program
2️⃣ PG Program
```

---

## 🔁 Conversation Flow

```
User sends any message
    └── Welcome + Program selection (UG / PG)
            ├── UG → Course selection (B.Sc / BCA)
            │       └── Name → Lead saved ✅
            └── PG → UG completed? (Yes / No)
                    ├── Yes → Course selection (MBA)
                    │       └── Name → Lead saved ✅
                    └── No → Ineligible message, flow reset
```

---

## 📊 Google Sheet Output

| Timestamp | Phone | Name | Program | Course | UG Completed |
|-----------|-------|------|---------|--------|--------------|
| 2024-06-18 10:30:00 | 919876543210 | Ravi Kumar | UG | BCA | N/A |
| 2024-06-18 11:00:00 | 918765432109 | Priya Sharma | PG | MBA | Yes |

---

## 🩺 Health Check

```
GET https://your-bot.onrender.com/health
→ {"status": "ok", "service": "whatsapp-admissions-bot"}
```

---

## 🛠 Local Development

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in values
python app.py
```

Use [ngrok](https://ngrok.com) to expose localhost:
```bash
ngrok http 5000
```
Use the ngrok HTTPS URL as your webhook URL in Meta settings.

---

## ⚠️ Common Issues

| Problem | Fix |
|---------|-----|
| Webhook verification fails | Check VERIFY_TOKEN matches exactly in `.env` and Meta settings |
| Google Sheets not updating | Check service account email has Editor access on the sheet |
| Messages not received | Ensure `messages` webhook field is subscribed in Meta Console |
| Bot stuck in a state | Delete the user's entry from `user_states.json` |
| Access token expired | Use a System User permanent token from Meta Business Manager |
