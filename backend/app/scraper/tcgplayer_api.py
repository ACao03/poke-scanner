from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings


@dataclass
class TCGToken:
    access_token: str
    token_type: str
    expires_at: datetime

    def authorization_header(self) -> str:
        return f"{self.token_type} {self.access_token}"


class TCGPlayerClient:
    """Minimal authenticated client for TCGplayer REST API.

    This implements client-credentials auth with in-memory token caching
    and exposes basic authorized GET calls for integration work.
    """

    def __init__(self, *, timeout: float = 30.0):
        self._timeout = timeout
        self._token: TCGToken | None = None

    def _assert_credentials(self) -> tuple[str, str]:
        public = settings.tcgplayer_public_key
        private = settings.tcgplayer_private_key
        if not public or not private:
            raise RuntimeError(
                "Missing TCGplayer credentials. Set TCGPLAYER_PUBLIC_KEY and "
                "TCGPLAYER_PRIVATE_KEY in your environment."
            )
        return public, private

    async def _request_token(self, client: httpx.AsyncClient) -> TCGToken:
        public, private = self._assert_credentials()
        url = f"{settings.tcgplayer_api_base}/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": public,
            "client_secret": private,
        }
        response = await client.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()

        expires_in = int(payload.get("expires_in", 0))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 1))

        return TCGToken(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "bearer"),
            expires_at=expires_at,
        )

    async def _get_token(self, client: httpx.AsyncClient) -> TCGToken:
        now = datetime.now(timezone.utc)
        if self._token and self._token.expires_at > now:
            return self._token
        self._token = await self._request_token(client)
        return self._token

    async def _authorized_get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._get_token(client)
            base = settings.tcgplayer_api_base.rstrip("/")
            version = settings.tcgplayer_api_version.strip("/")
            url = f"{base}/{version}/{path.lstrip('/')}"
            response = await client.get(
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "Authorization": token.authorization_header(),
                    "User-Agent": settings.scraper_user_agent,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_categories(self) -> dict:
        return await self._authorized_get("catalog/categories")


async def smoke_test_categories() -> dict:
    """Fetch catalog categories to validate credentials and bearer flow."""
    client = TCGPlayerClient()
    return await client.get_categories()


if __name__ == "__main__":
    import asyncio

    data = asyncio.run(smoke_test_categories())
    print(f"Success={data.get('Success')} count={len(data.get('Results') or [])}")
