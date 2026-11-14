import json
import os
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
out = Path(__file__).resolve().parent / "out"
rows = json.loads((out / "opportunities.json").read_text(encoding="utf-8"))

name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(name, device=device)

texts = [
    "\n".join(filter(None, [
        row["title"],
        row["summary"],
        "Domains: " + ", ".join(row["domains"]),
        row["audience"],
    ]))
    for row in rows
]

vectors = model.encode(
    texts, normalize_embeddings=True, show_progress_bar=True
)
assert vectors.shape == (len(rows), 384), vectors.shape
assert np.isfinite(vectors).all(), "Invalid embedding values"

for row, vector in zip(rows, vectors):
    row["embedding"] = vector.tolist()

target = out / "opportunities_embedded.json"
target.write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Saved {len(rows)} embeddings on {device}.")
print("Model:", name)
print("Output:", target)

for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
    print(key + ":", "SET" if os.getenv(key, "").strip() else "MISSING")
