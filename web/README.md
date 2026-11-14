# Virtual Science Park — web app (P4)

Run (Windows cmd, inside this web\ folder):
    npm install
    copy .env.example .env.local
    npm run dev
Open http://localhost:8080

Mock mode is on until VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in .env.local
(and VITE_USE_MOCK=false). Never put the service role key here.
