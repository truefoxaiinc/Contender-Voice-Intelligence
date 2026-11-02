# OpenRouter migration (draft)

This branch routes **both** structured call analysis and SOP/RAG embeddings through OpenRouter's OpenAI-compatible API. Local Faster Whisper transcription is unchanged.

## Required environment (never commit actual keys)

```dotenv
OPENROUTER_API_KEY=replace-with-secret
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_NAME=openai/gpt-4o-mini
EMBEDDING_MODEL_NAME=openai/text-embedding-3-small
```

`OPENAI_API_KEY` is no longer used by these two integrations. The chosen chat model must support structured output. Keep the existing embedding model **unchanged** for compatibility with existing FAISS vectors; changing the embedding model requires an index rebuild and validation.

## Verification before merge/deployment

1. `python -m pytest -q tests/test_openrouter_wiring.py` (offline wiring checks).
2. `python -m pytest -q` (full regression suite).
3. With a non-production OpenRouter key, test one embedding query, one SOP retrieval, and one structured analysis against a safe sample transcript. Verify cost, model availability, error handling, and schema.
4. Confirm the existing FAISS index is trusted and generated with the same embedding model. Existing index loading enables pickle deserialization; do not load untrusted files.
5. Confirm container configuration passes `OPENROUTER_API_KEY`; build and smoke-test separately before updating the running deployment.
6. Verify secrets are never committed or printed. Review HTTPS/private access before processing customer audio.

## Rollback

Do not change the running server as part of this PR. If post-deployment checks fail, restore the previous application image and previous environment configuration. Preserve persistent SQLite/audio volumes and the existing FAISS index.

## Known limits

Offline tests mock SDK clients and do not prove provider connectivity or billing. Existing background task durability, HTTP exposure, and auth issues are out of scope for this migration.
