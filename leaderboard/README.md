# EPB Leaderboard

Public leaderboard for the Epistemic Pathology Benchmark (EPB).

## Quick Start

### Installation

```bash
# Install with leaderboard support
pip install epb-benchmark[leaderboard]
```

### Running Locally

```bash
# Start the backend (from repo root)
cd leaderboard/backend
python app.py
```

Then visit: http://localhost:8000

## Architecture

```
leaderboard/
├── backend/
│   ├── app.py           # FastAPI application
│   ├── models.py        # Database models
│   ├── routes.py        # API endpoints
│   ├── db.py            # Database utilities
│   └── config.py        # Configuration
├── frontend/
│   ├── index.html       # Static HTML page
│   └── main.js          # JavaScript for API calls
└── data/                # SQLite database (created on first run)
```

## Backend (FastAPI + SQLite)

### Features

- REST API for submissions and leaderboard
- SQLite database (no PostgreSQL needed)
- API key authentication
- CORS support
- Serves static frontend

### API Endpoints

- `POST /api/submissions` - Submit results
- `GET /api/leaderboard` - Get rankings
- `GET /api/submissions/{id}` - Get submission details
- `GET /api/stats` - Get statistics
- `GET /health` - Health check

### Configuration

Set via environment variables:

```bash
export EPB_API_KEYS="key1,key2,key3"
export EPB_DB_PATH="leaderboard/data/epb_leaderboard.db"
```

## Frontend (Static HTML/JS)

### Features

- Vanilla JavaScript (no framework)
- Fetches data from backend API
- Filters by provider
- Auto-refresh
- Responsive design

### Files

- `index.html` - Main page with table and styling
- `main.js` - API calls and DOM manipulation

## Development

### Run Backend

```bash
# From leaderboard/backend/
uvicorn app:app --reload --port 8000
```

### Test API

```bash
# Get leaderboard
curl http://localhost:8000/api/leaderboard

# Get stats
curl http://localhost:8000/api/stats
```

### Submit Test Data

```bash
curl -X POST http://localhost:8000/api/submissions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{
    "epb_version": "epb_v1",
    "model_name": "test-model",
    "provider": "test",
    "scores": {
      "mirror_loop_phi": 85.0,
      "confab_persistence": 72.0,
      "violation_contamination": 95.0,
      "echo_drift": 88.0,
      "epb_truth": 85.0
    },
    "certification": "gold"
  }'
```

## Deployment

### Option 1: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .[leaderboard]

EXPOSE 8000
CMD ["uvicorn", "leaderboard.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Option 2: systemd Service

```ini
[Unit]
Description=EPB Leaderboard
After=network.target

[Service]
Type=simple
User=epb
WorkingDirectory=/opt/epb-benchmark
Environment="EPB_API_KEYS=your-keys"
ExecStart=/usr/bin/uvicorn leaderboard.backend.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 3: Cloud Platform

Deploy to platforms like:
- Railway
- Render
- Fly.io
- Heroku

Most support Python/FastAPI out of the box.

## Database

### Schema

**Submission Table**:
- `id` (primary key)
- `epb_version` (index)
- `model_name` (index)
- `provider` (index)
- `mirror_loop_phi`, `confab_persistence`, `violation_contamination`, `echo_drift`
- `epb_truth` (index, used for ranking)
- `certification`
- `submitted_at` (index)
- `scores_json`, `config_json`, `details_json`
- `ip_address`

### Migrations

Currently no migration system. Schema is created on first run via SQLAlchemy.

Future: Add Alembic for migrations.

## Security

### API Keys

Set `EPB_API_KEYS` environment variable:

```bash
export EPB_API_KEYS="$(openssl rand -hex 32),$(openssl rand -hex 32)"
```

### CORS

Configure allowed origins in `config.py`:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://yourdomain.com"
]
```

### Rate Limiting

Future enhancement. Currently not implemented.

## Testing

```bash
# From repo root
pytest leaderboard/backend/tests/
```

## Documentation

See [docs/leaderboard.md](../docs/leaderboard.md) for full documentation.

## License

MIT License - see [../LICENSE](../LICENSE)
