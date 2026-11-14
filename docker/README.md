# Local Docker development stack

Requires Docker Desktop, its Linux engine, Docker Compose, network access,
and the existing seeded Supabase project.

## Setup
Copy .env.example to .env and supply:
SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
LLM_BASE_URL, LLM_API_KEY, LLM_MODEL and EMBED_MODEL.

Never commit .env. No host Python/Node installation or web/.env.local
is required.

Stop any host API on port 8000 and any other matching watcher, then run:

    docker compose up --build

- Web: http://localhost:5180
- API: http://localhost:8000/health
- Watcher: polls private-state edits every five seconds.

The first startup downloads the embedding model. Wait for
"Watcher started" before editing priorities.

## Operations
    docker compose up -d --build
    docker compose ps
    docker compose logs --tail 50 watcher
    docker compose exec -T watcher python -m pipeline.monitor.verify_demo
    docker compose down

Named volumes retain model and runtime caches after shutdown.
Changing .env requires recreating containers with docker compose up -d.

## Credentials
Only the watcher receives the Supabase server secret.
The API receives the public Supabase key and Gemini credentials.
The web receives public Supabase configuration and the API base URL.
Local secret files are excluded from image build contexts.

Validate without printing expanded secrets:

    docker compose config --quiet

Do not share plain docker compose config output.

## Limits
This uses Vite for local development, not production hosting.
Ports bind to loopback; remote access needs explicit API/CORS configuration.
Only one matching watcher should run against the shared database.
The watcher observes future edits and does not rerank on startup.
Existing schema, auth accounts and demo records are prerequisites.

## Verification
All three images built. API and web returned HTTP 200.
The watcher downloaded its model and began polling.
Credential-separation checks and verify_demo passed.
The login page was confirmed visible.
Clean staged-source startup passed with only .env added, no host dependencies, and fresh runtime volumes. All three services started, the watcher downloaded its model and began polling, and verify_demo passed inside the clean watcher container. Docker build layers were reused where available; this was not a cache-free build.
