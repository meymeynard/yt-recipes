# 🍳 Pantry Chef: YouTube Recipe Aggregator

A personal, deterministic cooking recipe aggregator that matches what's currently in your kitchen with actual YouTube cooking videos from your favorite creators.

**100% Free & Fast**: No LLM APIs required. Uses regex section extraction, ingredient alias normalization, and set-intersection scoring.

---

## 🔑 Setup & API Key

Set your YouTube Data API v3 key using any of the following methods:

```bash
# Option A: Environment variable
export YOUTUBE_API_KEY="your_api_key_here"

# Option B: Local .env file
echo "YOUTUBE_API_KEY=your_api_key_here" > .env

# Option C: SOPS encrypted environment
# (Automatically reads from ~/.config/sops/secrets.enc.env if present)
```

---

## 🐳 Run with Docker (Recommended)

### One-Click Startup
```bash
./docker-run.sh
```

### Or with Docker Compose:
```bash
# With an environment variable:
export YOUTUBE_API_KEY="your_api_key_here"
docker compose up -d

# Or decrypt on the fly with SOPS:
sops exec-env ~/.config/sops/secrets.enc.env "docker compose up -d"

# View logs:
docker compose logs -f

# Stop container:
docker compose down
```

Open **`http://localhost:8501`** in your browser.  
*(The SQLite database is persisted in `./data/recipes.db`).*

---

## 💻 Run Locally (Without Docker)

### 1. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch
```bash
./run.sh
```
Or directly:
```bash
source .venv/bin/activate
streamlit run app.py
```

---

## 🗂️ Project Structure

```
├── Dockerfile          # Production multi-layer Dockerfile (non-root appuser, healthcheck)
├── docker-compose.yml  # Compose definition with volume mount & env injection
├── docker-run.sh       # One-click startup script with SOPS / env support
├── requirements.txt    # Python dependencies
├── config.py           # Retrieves YOUTUBE_API_KEY from env, .env, or SOPS
├── db.py               # SQLite database (recipes, ingredients, indexes)
├── parser.py           # Heuristic regex extractor & alias normalization engine
├── youtube_client.py   # YouTube Data API client (uploads playlistItems + search)
├── matcher.py          # Pantry intersection scoring & ranking algorithm
├── ingest.py           # CLI tool to crawl & index any YouTube channel
├── app.py              # Streamlit web interface
├── data/               # Persistent storage volume for SQLite (recipes.db)
└── run.sh              # Local virtualenv runner
```

---

## 📥 Indexing Additional Channels

To add videos from other YouTube channels:
```bash
# Inside local venv:
source .venv/bin/activate
python3 ingest.py --channel "Simpol" --limit 30
python3 ingest.py --channel "Kuya Fern's Cooking" --limit 30

# Or inside the running Docker container:
docker exec -it pantry-chef python3 ingest.py --channel "Kuya Fern's Cooking" --limit 30
```
*(You can also sync channels directly from the sidebar in the Streamlit UI!)*
