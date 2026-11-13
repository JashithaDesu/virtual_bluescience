"""Try candidate models (fast ones first) until one answers; write it to .env."""
import os, re, time, pathlib
from dotenv import load_dotenv
from openai import OpenAI

ENV = pathlib.Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV, override=True)
c = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"], timeout=25, max_retries=0)

candidates = ["gemini-2.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash-lite",
              "gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]
for name in candidates:
    t = time.time()
    try:
        r = c.chat.completions.create(
            model=name, response_format={"type": "json_object"}, max_tokens=200,
            messages=[{"role": "user", "content": 'Reply with {"ok": true}'}])
        print(f"OK   {name:26} {time.time() - t:5.1f}s -> {r.choices[0].message.content!r}")
        ENV.write_text(re.sub(r"^LLM_MODEL=.*$", f"LLM_MODEL={name}", ENV.read_text(), flags=re.M))
        print("\nSET LLM_MODEL =", name)
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"FAIL {name:26} {time.time() - t:5.1f}s -> {type(e).__name__}: {str(e)[:100]}")
print("\nNothing worked. Paste this output to Claude.")
