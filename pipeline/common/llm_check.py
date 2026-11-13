"""Diagnose LLM setup: list models, test the key, test JSON mode."""
import os, re, pathlib
from dotenv import load_dotenv
from openai import OpenAI, APIStatusError

ENV = pathlib.Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV, override=True)
c = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
k = os.environ["LLM_API_KEY"]
print("base_url:", os.environ["LLM_BASE_URL"])
print("model in .env:", os.environ["LLM_MODEL"], "| key starts:", k[:4], "| key length:", len(k))

try:
    ids = sorted(m.id for m in c.models.list())
    flash = [i for i in ids if "flash" in i and not any(x in i for x in ("image", "tts", "audio", "live"))]
    print("\nflash models available:", *flash, sep="\n  ")
    prefer = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    pick = next((i for p in prefer for i in flash if i.endswith(p)), flash[0] if flash else None)
    if pick:
        ENV.write_text(re.sub(r"^LLM_MODEL=.*$", f"LLM_MODEL={pick}", ENV.read_text(), flags=re.M))
        os.environ["LLM_MODEL"] = pick
        print("\nSET LLM_MODEL =", pick)
except APIStatusError as e:
    print("\nCANNOT LIST MODELS:", e.status_code, e.message[:300])

m = os.environ["LLM_MODEL"]
tests = {"plain": {}, "json_mode": {"response_format": {"type": "json_object"}},
         "json+max_tokens": {"response_format": {"type": "json_object"}, "max_tokens": 8000}}
print()
for name, extra in tests.items():
    try:
        r = c.chat.completions.create(model=m, messages=[{"role": "user", "content": 'Reply with {"ok": true}'}], **extra)
        print(f"{name:16} OK  -> {r.choices[0].message.content!r}")
    except APIStatusError as e:
        print(f"{name:16} {e.status_code} -> {e.message[:300]}")
