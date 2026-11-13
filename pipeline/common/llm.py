"""One LLM entry point for the whole team. LLM_BASE_URL switches hosted <-> local Ollama.
Retries on rate limits (429) and caches results on disk, so re-runs cost no API calls."""
import os, json, re, time, hashlib, pathlib
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError

load_dotenv()
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"], timeout=30, max_retries=0)
MODEL = os.environ["LLM_MODEL"]
CACHE = pathlib.Path(__file__).resolve().parents[2] / ".llm_cache"
CACHE.mkdir(exist_ok=True)

def chat_json(system: str, user: str, temperature: float = 0.0,
              max_tokens: int = 8000, use_cache: bool = True, retries: int = 5) -> dict:
    key = hashlib.sha256(f"{MODEL}\n{system}\n{user}\n{temperature}".encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if use_cache and f.exists():
        return json.loads(f.read_text())
    delay = 5
    for attempt in range(retries):
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=temperature, max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            raw = r.choices[0].message.content or "{}"
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
            out = json.loads(raw)
            if use_cache:
                f.write_text(json.dumps(out, ensure_ascii=False))
            return out
        except (RateLimitError, APIConnectionError) as e:
            print(f"  [llm] {type(e).__name__}, retry in {delay}s ({attempt + 1}/{retries})")
        except APIStatusError as e:
            if e.status_code < 500:
                raise
            print(f"  [llm] server error {e.status_code}, retry in {delay}s")
        except json.JSONDecodeError:
            print(f"  [llm] invalid JSON, retry in {delay}s")
        time.sleep(delay)
        delay = min(delay * 2, 60)
    raise RuntimeError("LLM call failed after retries")

if __name__ == "__main__":
    print(MODEL, "->", chat_json("Reply only with JSON.", 'Return {"ok": true}', use_cache=False))
