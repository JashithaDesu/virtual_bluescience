"""Test setup: dummy env vars so pipeline modules import without real keys or network."""
import os, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for k, v in {
    "LLM_BASE_URL": "http://localhost:9/v1",
    "LLM_API_KEY": "test-key",
    "LLM_MODEL": "test-model",
    "SUPABASE_URL": "http://localhost:9",
    "SUPABASE_SERVICE_ROLE_KEY": "test",
}.items():
    os.environ.setdefault(k, v)
