# TCGplayer Postman Setup

This project supports TCGplayer API auth via environment variables used by backend code:
- `TCGPLAYER_PUBLIC_KEY`
- `TCGPLAYER_PRIVATE_KEY`
- `TCGPLAYER_API_BASE` (default: `https://api.tcgplayer.com`)
- `TCGPLAYER_API_VERSION` (default: `v1.39.0`)

TCGplayer's Postman collection uses different variable names:
- `publicId` -> same value as `TCGPLAYER_PUBLIC_KEY`
- `privateId` -> same value as `TCGPLAYER_PRIVATE_KEY`

## Import into Postman

1. Import `TCGPlayer.postman_collection.json`.
2. Import `TCGPlayer.postman_environment`.
3. Set these environment vars in Postman:
   - `publicId`
   - `privateId`

If you need store-scoped endpoints, also complete the store authorization workflow and set `storeAuthorizationCode`.

## Auth Paths

### Non-store workflow

1. Run `Authenticate` request.
2. Use resulting bearer token for catalog endpoints.

### Store workflow

1. Complete store authorization workflow to obtain `storeAuthorizationCode`.
2. Set `storeAuthorizationCode` in Postman environment.
3. Run `Store Authorization` request.
4. Run `Authenticate` request.
5. Verify with a store endpoint (for example, store info).

## Validate Outside Postman

Use this project command to validate credentials + bearer flow from code:

```bash
cd backend
source .venv/bin/activate
python -m app.scraper.tcgplayer_api
```

Expected output shape:

```text
Success=True count=<n>
```

## Troubleshooting

- `invalid_grant`: key pair is wrong, revoked, or does not have API access.
- `401/403`: token expired, wrong auth scope, or restricted endpoint.
- No new API access is granted by TCGplayer (per their note), so existing partner credentials are required.

## Alternative Source When Partner Access Fails

If TCGplayer credentials cannot be issued, this project also supports Open TCG API fallback for price refresh:

- Configure `OPEN_TCG_ENABLED=true` in `.env`.
- Set `OPEN_TCG_BASE`, `OPEN_TCG_API_VERSION`, and `OPEN_TCG_GAME_ID`.
- Use `OPEN_TCG_API_KEY` if required by your endpoint.
