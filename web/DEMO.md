# Demo runbook (P4 web app)

Demo runs from **localhost:8080 on the demo laptop**. Vercel is the backup for Profile / Opportunities / Compare only (no Ask there).

## 1. Start three processes (demo laptop)

**Terminal 1: /ask (P3)**, from the repo root, with the root `.env` filled in (Supabase + LLM keys):

    uvicorn api.main:app --reload --port 8000

Check: http://localhost:8000/health answers.

**Terminal 2: watcher (P2)**, Git Bash, repo root:

    source .venv/Scripts/activate
    export PYTHONUTF8=1
    unset LLM_API_KEY
    python -m pipeline.monitor.watch --check
    python -m pipeline.monitor.watch

Start exactly ONE watcher. Leave it running. It prints `Published ocean-harvesting; feed can refresh now.` after a re-rank (about 20 s).

**Terminal 3: web app (P4)**, from `web/`:

    npm install        # first time only
    npm run dev        # http://localhost:8080

## 2. `web/.env.local` on the demo laptop (never committed)

    VITE_SUPABASE_URL=https://mmwxxjnfeafmmhxwcyev.supabase.co
    VITE_SUPABASE_ANON_KEY=<sb_publishable_... from P3, NEVER sb_secret_>
    VITE_ASK_URL=http://localhost:8000
    VITE_USE_MOCK=false

Restart `npm run dev` after any change. Check before going on stage:
- no yellow MOCK banner at the top,
- the Ask page shows no red "not connected" note.

## 3. Logins

`member-oht@demo.com`, `member-addsecure@demo.com`, `staff@demo.com`. Password: from P3 (not stored in the repo).

## 4. The six steps

| # | Click | Say |
|---|---|---|
| 1 | Log in as `member-oht@demo.com` | "A real Blue Science Park member. Nobody typed this profile in." |
| 2 | **Profile**: scroll the facts | "Every fact has a quote and a link to where we found it. Guesses are marked, gaps are shown honestly. 'Old source' means the news article is from before 2024." |
| 3 | **Profile -> Your priorities**: add `Testing and validating our technology with a potential customer is a priority` | "This is the member telling us what matters right now. It's private to them." |
| 4 | **Opportunities**: the blue "Updating your recommendations..." banner shows; after ~20 s the ranks change: *Verification with Customers* gets **"moved up from #4"** arrow to #3 | "The matcher re-ranked using the new priority. Every match says why it fits and what to do next." (Fill the ~20 s with this.) |
| 5 | Log out -> log in as `staff@demo.com` -> **Compare** (OHT vs AddSecure) | "Staff see which opportunities each company should hear about. A member never sees another company's private data." |
| 6 | Log back in as OHT -> **Ask**: click the 4 suggested questions in order | 1 in scope with sources - 2 unrelated (poem) - 3 refused (injection) - 4 no yes/no on eligibility |

Confirm steps 1, 2 and 5 against the team checklist; steps 3, 4 and 6 are fixed.

## 5. Reset between rehearsal and the real run

- **Profile -> Your priorities**: click x on the demo priority (this re-ranks back; wait for the watcher).
- Any "Not correct" clicked: press **Undo**.
- Do not add the same priority twice. Do not run manual reranks while the watcher runs.

## 6. Vercel backup (after the 09:30 merge to main)

    git checkout main
    git pull
    cd web
    npx vercel --prod

Vercel needs `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` and `VITE_USE_MOCK=false` (`npx vercel env ls`). Leave `VITE_ASK_URL` unset there: Ask then says "not connected" instead of answering.