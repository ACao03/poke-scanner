from __future__ import annotations

import httpx

from app.config import settings


def _listify(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("Results", "results", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


class OpenTCGClient:
    def __init__(self):
        self.base = settings.open_tcg_base.rstrip("/")
        self.version = settings.open_tcg_api_version.strip("/")
        self.game_id = settings.open_tcg_game_id
        self.timeout = settings.open_tcg_timeout_seconds

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        if settings.open_tcg_api_key:
            headers["Authorization"] = f"Bearer {settings.open_tcg_api_key}"
        url = f"{self.base}/{self.version}/{self.game_id}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def fetch_sets(self) -> list[dict]:
        payload = await self._get("sets")
        return _listify(payload)

    async def fetch_set_pricing(self, set_id: str | int) -> list[dict]:
        payload = await self._get(f"sets/{set_id}/pricing")
        return _listify(payload)

    async def fetch_set_skus(self, set_id: str | int) -> list[dict]:
        payload = await self._get(f"sets/{set_id}/skus")
        return _listify(payload)
