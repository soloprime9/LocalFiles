# Platform Hub

A Flask web app with three pages, wired together:

1. **Search** (`/`, `/search`) — one search bar, results grouped by platform.
2. **Connect Accounts** (`/connect`) — real OAuth "Connect" buttons per platform.
3. **Dashboard** (`/dashboard`) — view-only feed of your connected accounts'
   own content, plus an upload form (reuses the upload code from before).

No download/export features exist anywhere in this app — every result links
to or embeds the platform's own player, the same as visiting the site
directly. That's intentional: re-hosting or downloading other people's posts
is a piracy/ToS problem, and this project stays on the right side of that.

## 1. Install

```bash
cd platform_hub
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Fill in `.env` — what's real vs. limited, per platform

**Search bar coverage** (important — read before you wire anything up):

| Platform  | Public search API? | What this app does |
|-----------|--------------------|---------------------|
| Google    | ✅ Custom Search JSON API | Real web search results |
| YouTube   | ✅ search.list (fully public) | Real video results, embedded player |
| X/Twitter | ⚠️ Only with Elevated/Pro API access | Real results if you have that tier |
| Facebook  | ❌ Removed in 2018 for privacy | Shows an honest "not available" message |
| Instagram | ⚠️ Hashtag-only, connected Business account, ~30 queries/week | Not wired into the search bar; use the dashboard's hashtag lookup once you extend it |
| TikTok    | ❌ No public search API | Honest "not available" message |
| Telegram  | ❌ No official global search | Honest "not available" message |

This is a platform limitation, not something this code works around — any
tool claiming to "search all of Instagram/TikTok/Telegram" for you is either
lying or scraping (which breaks ToS and gets accounts/IPs banned).

### Getting each key

- **Google Custom Search**: console.cloud.google.com → enable "Custom Search
  API" → create an API key. Then go to programmablesearchengine.google.com →
  create a search engine → grab its Search Engine ID (`cx`).
- **YouTube**: same Google API key works — just also enable "YouTube Data
  API v3" in the same Cloud project.
- **X**: developer.x.com → create a Project/App → you need Elevated or Pro
  tier for the recent-search endpoint to return anything.

### Getting OAuth "Connect" credentials

- **Google/YouTube OAuth**: Cloud Console → Credentials → OAuth Client ID →
  type "Web application" → add redirect URI
  `http://localhost:5000/connect/google/callback`.
- **Facebook/Instagram**: developers.facebook.com/apps → create app → add
  redirect URI `http://localhost:5000/connect/facebook/callback`. Instagram
  Business accounts linked to a connected Page become available automatically.
- **X OAuth 2.0**: developer.x.com → App settings → enable OAuth 2.0 → add
  redirect URI `http://localhost:5000/connect/x/callback`.
- **TikTok**: developers.tiktok.com → create app → add redirect URI
  `http://localhost:5000/connect/tiktok/callback`. Note: most TikTok API
  scopes require app review before going live.
- **Telegram**: message @BotFather → `/newbot` → get a bot token → set the
  bot as the domain's login widget via `/setdomain`.

## 3. Run

```bash
python app.py
# open http://localhost:5000
```

## How the pages connect (the "full setup" flow)

```
Search (/) ──user searches──> aggregate_search() hits each platform's
                               real API, or returns an honest "not
                               available" note if the platform doesn't
                               offer one.

Connect (/connect) ──user clicks "Connect X"──> redirected to X's own
                               login page → approves scopes → X redirects
                               back to /connect/x/callback with a code →
                               we exchange it for an access token → stored
                               in session["tokens"]["x"].

Dashboard (/dashboard) ──reads session["tokens"]──> calls
                               content_service.get_*() for each connected
                               platform → renders view-only cards, each
                               linking to/embedding the original post.

Upload form (on /dashboard) ──POST /upload──> upload_service.upload_to_*()
                               using the stored token for whichever
                               platforms you ticked.
```

## Phase 2: MongoDB + storage + full report (this update)

What changed from the session-only version:

- **`db.py`** — all data now lives in MongoDB, in 4 collections:
  - `users` — one doc per person (simple email login for now)
  - `connected_accounts` — one doc per (user, platform), **OAuth tokens
    encrypted** before they're written (see `crypto_utils.py`)
  - `videos` — one doc per uploaded video (storage location, AI fields
    reserved for Phase 3)
  - `posts` — one doc per (video, platform) — this is what powers the
    dashboard's "full report": status, timestamps, the live post URL once
    published, or the exact error if it failed
- **`services/storage_service.py`** — uploads video files to S3-compatible
  storage (AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces all
  work) and returns a public URL, which the DB record stores.
- **`crypto_utils.py`** — encrypts access/refresh tokens with Fernet before
  they touch the database. Anyone reading a DB dump sees ciphertext, not
  a token they could use to post on someone's behalf.
- **Login** (`/login`) — simple email-based login was added so `connect`,
  `dashboard`, and `upload` all know *whose* data they're reading/writing.
  This is intentionally minimal — swap it for real auth (password + hash,
  or "Sign in with Google" reusing the same OAuth flow) before real users
  touch this.

### Setting this up

1. You said you already have MongoDB running — just point `MONGODB_URI` in
   `.env` at it (e.g. `mongodb://localhost:27017` or your Atlas connection
   string). `MONGODB_DB_NAME` can be anything; it'll be created automatically.
2. Generate an encryption key and put it in `.env`:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Store this key somewhere safe outside the repo — losing it makes every
   stored token unreadable (users would need to reconnect their accounts).
3. Set up an S3-compatible bucket (AWS S3 is simplest to start with) and
   fill in the `S3_*` values in `.env`.
4. `pip install -r requirements.txt` (now includes `pymongo`, `cryptography`,
   `boto3`) and run `python app.py`.

### What was actually broken in the previous Phase 2 pass, and what I fixed

I ran this end-to-end (mongomock-backed unit tests + a live Flask test
client hitting every route) instead of just reading the code, and found two
real bugs in `/upload` that would have bitten you the first time you used
it for real:

1. **YouTube upload was broken.** The local video file was deleted
   immediately after the S3 upload, then the code tried to hand that
   now-deleted local path — actually a public `https://` URL — to Google's
   `MediaFileUpload`, which requires an actual local file path, not a URL.
   Every YouTube upload would have thrown. **Fixed**: the local file is now
   kept until every selected platform has finished (success or fail), and
   YouTube gets the local path like it needs.
2. **False "posted successfully" for platforms that weren't implemented.**
   Facebook, X, Instagram, Pinterest, and TikTok all fell into a generic
   `else` branch that returned a stub `{"note": "..."}` with no `id`/`url`
   — and the code called `mark_post_success` on it anyway, flashing
   "posted successfully" even though nothing was posted. **Fixed**: each
   platform now either actually posts (YouTube, Facebook — including
   looking up the right Facebook Page token, TikTok) or raises a clear,
   specific error that gets honestly recorded as `failed` in the dashboard
   report. Nothing is silently faked as a success anymore.

I also filled in files that this changeset didn't include but the app
still imports/renders: `services/__init__.py` (without it, `from services
import ...` in `app.py` fails immediately), and reused
`oauth_service.py`, `search_service.py`, `content_service.py`,
`upload_service.py`, and the `base.html`/`index.html`/`connect.html`
templates + `style.css` from Phase 1 unchanged, since this changeset didn't
touch them.

### What this does NOT do yet (that's Phase 3)

- No AI-generated title/description/hashtags — the upload form still takes
  them as manual input for now.
- No background job queue/scheduler — `/upload` runs each platform's post
  immediately and records the result, rather than queuing it for a chosen
  time.
- Instagram/X/Pinterest/TikTok upload paths are stubbed in `app.py`'s
  `/upload` route (same as before) — YouTube is the one fully wired end-to-end
  through the new DB + storage layer as a working example to copy from.

## Going to production

This demo keeps tokens in the Flask session (a signed cookie) for
simplicity — fine for trying it out locally, not for a real multi-user app.
Before deploying:

- Store tokens in a real database (one row per user per platform), encrypted
  at rest.
- Add a proper login system (Flask-Login or similar) so `/dashboard` and
  `/upload` are tied to an actual account, not just "whoever has this cookie."
- Refresh expired tokens (Google/Facebook/TikTok all issue short-lived
  access tokens with a refresh token — none of that refresh logic is wired
  up yet, it's a straightforward addition to `services/oauth_service.py`).
- Move file uploads off local disk into object storage (S3/GCS) — Instagram
  and Pinterest need a public URL anyway.
- Add CSRF protection (Flask-WTF) on the upload form.
- Serve over HTTPS — several of these OAuth providers require it outside
  of localhost testing.

## Rate limits (check current values before relying on a number)

- YouTube: ~10,000 quota units/day (an upload costs ~1,600).
- Instagram: max 25 API-posted pieces of content per 24h per account.
- X: search and posting caps depend heavily on your API tier.
- TikTok: most endpoints require app review before non-sandbox use.
