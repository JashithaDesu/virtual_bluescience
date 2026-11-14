import os
import sys

from sentence_transformers import SentenceTransformer

name = os.environ["EMBED_MODEL"]
print("Preparing embedding model; first startup downloads it.", flush=True)
SentenceTransformer(name, device="cpu")
print("Embedding model cached; starting watcher.", flush=True)
os.execv(sys.executable, [
    sys.executable, "-u", "-m", "pipeline.monitor.watch",
])
