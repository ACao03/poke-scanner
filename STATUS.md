# Component Status

| Component | Status | Notes |
| --- | --- | --- |
| DB schema + pgvector | ✅ Production-shaped | Implemented and initialized via `python -m app.init_db`. |
| Card/set ingestion | ✅ Real (via pokemontcg.io) | Implemented in `app/scraper/tcgplayer.py` as the compliant stand-in source. |
| Embedding + pHash | ✅ Works, baseline quality | Implemented in `app/vision/embed.py`. |
| Preprocessing (warp, CLAHE) | ✅ Works | Implemented in `app/vision/preprocess.py`. |
| `/identify` end-to-end | ✅ Works | API route and pipeline wired through `app/api/identify.py`. |
| Price history | ⚠️ Partial | Schema + API done; scraper task is stubbed. Plug in your production price source in `app/scraper/tasks.py`. |
| TCGplayer auth flow | ✅ Implemented scaffold | Client-credentials bearer flow implemented in `app/scraper/tcgplayer_api.py` with env-based key config. |
| Open TCG pricing fallback | ✅ Implemented scaffold | Optional refresh path in `app/scraper/tasks.py` using `app/scraper/open_tcg.py` when `OPEN_TCG_ENABLED=true`. |
| JP card catalog | ⚠️ Partial | Layout classifier not included. Add a small head on the same backbone for JP layout handling. |
| Learned ArcFace embedding | ⚠️ Pending | Swap-in point is `app/vision/embed.py` while preserving interface compatibility. |
| Auth, rate limiting, image storage | ⚠️ Omitted | Not included in this scaffold by design. |

## Next Steps (Priority Order)

1. Get legal data access: TCGplayer partner API, or fall back to a licensed aggregator. This is the single biggest risk.
2. Collect a labeled photo dataset (even 500-1k user photos of ~100 cards) and fine-tune the embedding model with ArcFace. Expect a large accuracy jump over ImageNet-ResNet.
3. Add the JP layout classifier (binary head on the same backbone) and route OCR to a JP model.
4. Set-symbol classifier: a small ~200-class head; this is the decisive disambiguator for reprints.
5. Add `/feedback` to capture "was this your card?" and start the active-learning loop.
6. Frontend polish: camera guidance overlay, live edge detection, price sparkline.

## TCGplayer API Quick Start (Project)

1. Set `TCGPLAYER_PUBLIC_KEY` and `TCGPLAYER_PRIVATE_KEY` in your `.env`.
2. Verify auth + bearer requests work:
	- `cd backend && source .venv/bin/activate`
	- `python -m app.scraper.tcgplayer_api`
3. Expected output:
	- `Success=True count=<n>`

Notes:
- API version is set via `TCGPLAYER_API_VERSION` (default `v1.39.0`).
- Existing catalog ingestion in `app/scraper/tcgplayer.py` still uses pokemontcg.io as the compliant stand-in source until partner access is enabled.
- Postman workflow notes are documented in `TCGPLAYER_POSTMAN.md`.

## Open TCG Fallback (Optional)

Use this when partner API access is unavailable:

1. Set `OPEN_TCG_ENABLED=true` in `.env`.
2. Set `OPEN_TCG_GAME_ID` for your target game namespace.
3. Optionally set `OPEN_TCG_API_KEY` if your endpoint requires bearer auth.
4. Run pricing refresh worker task:
	- `celery -A app.scraper.tasks.celery worker -l info`
	- Trigger `refresh_prices`.

Dry-run smoke test without DB writes:
- `cd backend && source .venv/bin/activate`
- `python -m app.scraper.tasks smoke`
- Returns counts for matched sets, scanned rows, matched rows, variants to create, and rows that would be inserted.
