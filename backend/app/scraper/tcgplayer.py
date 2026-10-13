import asyncio
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Card, CardVariant, Price, Set
from app.vision.embed import embed_image_from_url

POKEMON_API = "https://api.pokemontcg.io/v2"
CACHE_DIR = Path(".cache/pokemontcg")


def _cache_path(kind: str, key: str, page: int) -> Path:
    p = CACHE_DIR / kind / key
    p.mkdir(parents=True, exist_ok=True)
    return p / f"page_{page}.json"


def _read_cache(kind: str, key: str, page: int) -> dict | None:
    fp = _cache_path(kind, key, page)
    if fp.exists():
        try:
            return json.loads(fp.read_text())
        except Exception:
            return None
    return None


def _write_cache(kind: str, key: str, page: int, payload: dict) -> None:
    _cache_path(kind, key, page).write_text(json.dumps(payload))


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    *,
    retries: int = 5,
) -> dict:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 429:
                wait = (2 ** attempt) * 2 + random.random()
                print(f"    429 rate-limited, waiting {wait:.1f}s")
                await asyncio.sleep(wait)
                continue
            if 500 <= r.status_code < 600:
                wait = (2 ** attempt) * 2 + random.random()
                print(f"    {r.status_code} from upstream, waiting {wait:.1f}s")
                await asyncio.sleep(wait)
                last_exc = httpx.HTTPStatusError(
                    f"server {r.status_code}", request=r.request, response=r
                )
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.RequestError, httpx.TimeoutException) as e:
            last_exc = e
            wait = (2 ** attempt) * 2 + random.random()
            print(f"    network error ({type(e).__name__}), waiting {wait:.1f}s")
            await asyncio.sleep(wait)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"exhausted retries for {url}")


async def fetch_sets(client: httpx.AsyncClient, page: int = 1) -> dict:
    cached = _read_cache("sets", "_all", page)
    if cached:
        print(f"  [cache] sets page {page}")
        return cached
    data = await _get_with_retry(
        client, f"{POKEMON_API}/sets", {"page": page, "pageSize": 100}
    )
    _write_cache("sets", "_all", page, data)
    return data


async def fetch_cards(client: httpx.AsyncClient, set_id: str, page: int = 1) -> dict:
    cached = _read_cache("cards", set_id, page)
    if cached:
        print(f"  [cache] {set_id} page {page}")
        return cached
    data = await _get_with_retry(
        client,
        f"{POKEMON_API}/cards",
        {"q": f"set.id:{set_id}", "page": page, "pageSize": 250},
    )
    _write_cache("cards", set_id, page, data)
    return data


async def upsert_set(db: Session, s: dict) -> Set:
    obj = db.query(Set).filter_by(code=s["id"]).one_or_none()
    if not obj:
        obj = Set(code=s["id"])
        db.add(obj)
    obj.name_en = s.get("name")
    obj.language = "en"
    db.flush()
    return obj


def _now():
    return datetime.now(timezone.utc)


def _record_prices(db: Session, variant: CardVariant, tcg_prices: dict) -> int:
    """Snapshot the price dict into the Price table."""
    if not tcg_prices:
        return 0
    inserted = 0
    now = _now()
    for variant_key, fields in tcg_prices.items():
        if not isinstance(fields, dict):
            continue
        if variant.variant != variant_key:
            continue
        db.add(
            Price(
                variant_id=variant.id,
                captured_at=now,
                market=fields.get("market"),
                low=fields.get("low"),
                mid=fields.get("mid"),
                high=fields.get("high"),
            )
        )
        inserted += 1
    return inserted


async def upsert_card(db: Session, set_obj: Set, c: dict) -> Card:
    number = c.get("number")
    obj = (
        db.query(Card)
        .filter_by(set_id=set_obj.id, card_number=number, language="en")
        .one_or_none()
    )
    if not obj:
        obj = Card(set_id=set_obj.id, card_number=number, language="en")
        db.add(obj)
        db.flush()
    obj.name_en = c.get("name")
    obj.rarity = (c.get("rarity") or "").lower() or None
    images = c.get("images") or {}
    obj.image_url = images.get("large") or images.get("small")

    if obj.image_url and obj.embedding is None:
        try:
            emb, ph = await embed_image_from_url(obj.image_url)
            obj.embedding = emb
            obj.phash = ph
        except Exception as e:
            print(f"    embed failed for {obj.name_en}: {e}")

    # Variants + prices come together in the API response
    tcg = (c.get("tcgplayer") or {}).get("prices") or {}
    existing = {v.variant: v for v in obj.variants}
    for variant_key, fields in tcg.items():
        v = existing.get(variant_key)
        if v is None:
            v = CardVariant(card_id=obj.id, variant=variant_key)
            db.add(v)
            db.flush()
        _record_prices(db, v, {variant_key: fields})

    return obj


async def scrape_all(limit_sets: int | None = None):
    async with httpx.AsyncClient(
        headers={"User-Agent": settings.scraper_user_agent},
        timeout=45,
    ) as client:
        db = SessionLocal()
        try:
            page = 1
            processed_sets = 0
            while True:
                data = await fetch_sets(client, page)
                sets = data.get("data", [])
                if not sets:
                    break

                for s in sets:
                    set_code = s.get("id")
                    printed_total = s.get("printedTotal") or s.get("total") or 0

                    # Skip if we already have the full set
                    existing_count = db.scalar(
                        select(func.count())
                        .select_from(Card)
                        .join(Set)
                        .where(Set.code == set_code)
                    )
                    if printed_total and existing_count >= printed_total:
                        print(f"=== set {set_code} : already have {existing_count} cards, skipping ===")
                        processed_sets += 1
                        if limit_sets and processed_sets >= limit_sets:
                            return
                        continue

                    print(f"=== set {set_code} : {s.get('name')} (target {printed_total}) ===")
                    try:
                        set_obj = await upsert_set(db, s)
                    except Exception as e:
                        print(f"  upsert_set failed for {set_code}: {e}")
                        db.rollback()
                        continue

                    cpage = 1
                    while True:
                        try:
                            cdata = await fetch_cards(client, set_code, cpage)
                        except Exception as e:
                            print(f"  giving up on {set_code} page {cpage}: {e}")
                            db.rollback()
                            break

                        cards = cdata.get("data", [])
                        if not cards:
                            break

                        for c in cards:
                            try:
                                await upsert_card(db, set_obj, c)
                            except Exception as e:
                                print(f"  upsert_card failed for {c.get('name')}: {e}")
                                db.rollback()
                                continue

                        db.commit()
                        print(f"  {set_code} page {cpage}: +{len(cards)} cards")
                        cpage += 1
                        await asyncio.sleep(0.5)

                    processed_sets += 1
                    if limit_sets and processed_sets >= limit_sets:
                        db.commit()
                        return
                page += 1
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(scrape_all(limit_sets=3))
