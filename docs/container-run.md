# CPU deployment with Groq and dense retrieval

This container runs the French web app, BM25, dense, hybrid, hybrid with reranking, and the optional Groq answer path. It does not compile or host a language model. The image contains only application code and locked Python dependencies; the active processed corpus is mounted read-only at runtime.

1. On the host, create or verify `data/processed/manifest.json`, `articles.jsonl`, and `passages.jsonl` with `constitution-evidence ingest` and `constitution-evidence validate-corpus`. The container does not perform OCR.
2. Put `GROQ_API_KEY=...` in the ignored project-root `.env` if Groq answers are wanted. Docker Compose passes only that variable and `GROQ_MODEL` to the container. Extractive answers work without a key. The processed files may be owner-readable only; Compose runs as UID/GID 1000 by default. If your host IDs differ, also set `CONSTITUTION_UID` and `CONSTITUTION_GID` in `.env` to the output of `id -u` and `id -g`.
3. Run `docker compose up -d --build` and open `http://127.0.0.1:8000/`. Run `docker compose ps` to check health; `/health` reports `ok` only when the mounted corpus passes its hash check.
4. Stop with `docker compose down`.

The published port is bound to host loopback. The container runs as an unprivileged user with a read-only root filesystem, a small temporary directory, no Linux capabilities, and a read-only corpus mount. The image excludes `.env`, downloaded PDFs, OCR output, processed data, and saved runs via `.dockerignore`. The dense index and FastEmbed models live in the persistent Docker volume `dense-models`, which is writable by the app. Their first use may download models and take longer; subsequent requests reuse them. `docker compose down` keeps the volume, while `docker compose down -v` deletes it. Generated answers still need human scrutiny for legal completeness and semantic support.

The `Résumé local` option needs a separate Qwen server. This Compose profile does not start one, so the browser disables the option when `/capabilities` cannot reach it. Use `Résumé Groq` or `Extraits` inside this container; to use local Qwen on the host, follow [the local model guide](local-model.md) and run the app directly with `uv run ... serve`.

To verify an image locally, run `docker compose config --quiet`, `docker compose build`, then `docker compose up -d` and query `/health`. If the Docker daemon is unavailable, the Compose syntax check and the project's local offline tests can still run without it.
