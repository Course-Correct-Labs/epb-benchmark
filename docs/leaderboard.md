# EPB Leaderboard

The EPB Leaderboard is a public ranking of AI models based on their epistemic integrity, as measured by the Epistemic Pathology Benchmark.

## Legacy/Noncanonical Notice

The ranking below is built entirely from the **legacy** `epb_truth` score
and **legacy** certification tier -- a weighted average of four historical
sub-scores, thresholded into a badge. Per
[`EPB_V1_FINAL_INTEGRATION_FREEZE.md`](../EPB_V1_FINAL_INTEGRATION_FREEZE.md),
both are explicitly **legacy/noncanonical**: no current EPB quantity is
`FROZEN`, so none is eligible for canonical downstream consumption, and
`epb_truth`/certification are retained only for backward compatibility.
**Do not interpret leaderboard rank, "higher score", or certification
badge as a validated, canonical, or Observatory-grade scientific
comparison between models.** The current structured scientific outputs
(`results.json["quantities"]`, one entry per measurable quantity with its
own measurement/validation state) are not yet part of this leaderboard.

## Availability Note

`coursecorrect.org` does not currently resolve (checked at release time).
Everything below documents the leaderboard's intended interface and
protocol -- it is not a confirmation that a production instance is
currently live. `epb submit` will fail with a connection error against
this URL until a real instance is available; see "Running Your Own
Leaderboard" below to self-host one.

## Accessing the Leaderboard

Visit: https://epb.coursecorrect.org (or your deployed instance)

## Submitting Results

### Prerequisites

1. Complete an EPB benchmark run
2. Score your results
3. Obtain a leaderboard API key (contact: hello@coursecorrect.org)

### Submission Process

#### Using the CLI

```bash
# Set environment variables
export EPB_LEADERBOARD_URL="https://epb.coursecorrect.org/api"
export EPB_API_KEY="your-api-key-here"

# Submit results
epb submit --results runs/YYYYMMDD_HHMMSS/results.json
```

#### Using the API Directly

```bash
curl -X POST https://epb.coursecorrect.org/api/submissions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d @results.json
```

### What Gets Submitted

Your submission includes:
- Model name and provider
- Four sub-scores (Phi, Persistence, Contamination, Drift)
- Overall EPB Truth score
- Certification level
- Timestamp

**Note**: Full task details and responses are **not** submitted to protect privacy and API usage.

## Leaderboard Rankings

Models are ranked by their legacy/noncanonical **EPB Truth** score (0-100,
higher is better) -- see the notice above.

### Certification Levels

| Level | Score Range | Badge |
|-------|-------------|-------|
| Platinum | 95-100 | 🏆 |
| Gold | 85-94.99 | 🥇 |
| Silver | 70-84.99 | 🥈 |
| Bronze | 50-69.99 | 🥉 |
| None | 0-49.99 | - |

### Displayed Metrics

For each model, the leaderboard shows:
- **Rank**: Position on leaderboard
- **Model Name**: e.g., "gpt-4", "claude-3-5-sonnet"
- **Provider**: e.g., "openai", "anthropic"
- **EPB Truth**: Overall score
- **Sub-scores**: Phi, Persistence, Contamination, Drift
- **Certification**: Level achieved
- **Submitted**: Date of submission

## Filters

The leaderboard can be filtered by:
- **Provider**: Show only OpenAI, Anthropic, etc.
- **EPB Version**: Currently only "epb_v1"

## Running Your Own Leaderboard

You can host your own EPB leaderboard instance.

### Installation

```bash
# Install leaderboard dependencies
pip install epb-benchmark[leaderboard]
```

### Configuration

Set environment variables:

```bash
# API keys (comma-separated)
export EPB_API_KEYS="key1,key2,key3"

# Database path (optional)
export EPB_DB_PATH="path/to/leaderboard.db"
```

### Running the Backend

```bash
cd leaderboard/backend
python app.py
```

Or with uvicorn:

```bash
uvicorn leaderboard.backend.app:app --host 0.0.0.0 --port 8000
```

The backend will:
- Initialize a SQLite database
- Serve the API at `/api`
- Serve the frontend at `/`

### API Endpoints

#### POST /api/submissions

Submit a new result.

**Headers**:
- `Content-Type: application/json`
- `X-API-Key: your-api-key`

**Body**: Results JSON from `epb score`

**Response**:
```json
{
  "id": 123,
  "status": "accepted",
  "message": "Submission successful"
}
```

#### GET /api/leaderboard

Get ranked submissions.

**Query Parameters**:
- `epb_version` (default: "epb_v1")
- `provider` (optional)
- `limit` (default: 100)

**Response**:
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "model_name": "gpt-4",
      "provider": "openai",
      "scores": {
        "mirror_loop_phi": 85.5,
        "confab_persistence": 72.3,
        "violation_contamination": 95.0,
        "echo_drift": 88.2,
        "epb_truth": 85.25
      },
      "certification": "gold",
      "submitted_at": "2025-01-17T14:30:22Z"
    },
    ...
  ],
  "total": 42
}
```

#### GET /api/submissions/{id}

Get a specific submission by ID.

**Response**: Full submission details including scores.

#### GET /api/stats

Get leaderboard statistics.

**Response**:
```json
{
  "total_submissions": 42,
  "by_provider": {
    "openai": 25,
    "anthropic": 17
  },
  "top_score": 85.25,
  "top_model": "gpt-4"
}
```

## Security

### API Keys

- Required for POST /submissions
- Set via `EPB_API_KEYS` environment variable
- Comma-separated list
- If not set, submissions are open (dev mode)

### Rate Limiting

- Currently: 10 requests/minute per IP (configurable)
- Future: Token bucket algorithm

### Data Validation

All submissions are validated for:
- EPB version compatibility
- Required score fields
- Score ranges (0-100)
- Valid certification levels

## Privacy

- Only aggregated scores are stored
- IP addresses are logged for abuse prevention
- Full task responses are NOT submitted
- Model configurations are optional

## Future Features

Planned enhancements:
- Historical trend graphs
- Filter by certification level
- Model comparison view
- Export leaderboard data
- Verified submissions (with cryptographic proof)

## Support

For leaderboard issues:
- GitHub: [Report Issue](https://github.com/Course-Correct-Labs/epb-benchmark/issues)
- Email: hello@coursecorrect.org

## Terms of Use

By submitting to the leaderboard, you agree that:
- Results are from legitimate EPB runs
- Model name and provider are accurate
- Results may be publicly displayed
- Results may be used for research and analysis

Course Correct Labs reserves the right to remove fraudulent or invalid submissions.
