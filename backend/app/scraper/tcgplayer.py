import asyncio

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Card, CardVariant, Set
from app.vision.embed import embed_image_from_url

POKEMON_API = "https://api.pokemontcg.io/v2"


async def fetch_sets(client: httpx.AsyncClient, page: int = 1) -> dict:
	r = await client.get(f"{POKEMON_API}/sets", params={"page": page, "pageSize": 100})
	r.raise_for_status()
	return r.json()


async def fetch_cards(client: httpx.AsyncClient, set_id: str, page: int = 1) -> dict:
	r = await client.get(
		f"{POKEMON_API}/cards",
		params={"q": f"set.id:{set_id}", "page": page, "pageSize": 250},
	)
	r.raise_for_status()
	return r.json()


async def upsert_set(db: Session, s: dict) -> Set:
	obj = db.query(Set).filter_by(code=s["id"]).one_or_none()
	if not obj:
		obj = Set(code=s["id"])
		db.add(obj)
	obj.name_en = s.get("name")
	obj.language = "en"
	return obj


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
			print(f"embed failed for {obj.name_en}: {e}")

	tcg = (c.get("tcgplayer") or {}).get("prices") or {}
	existing = {v.variant for v in obj.variants}
	for variant_key in tcg.keys():
		if variant_key not in existing:
			db.add(CardVariant(card_id=obj.id, variant=variant_key))
	return obj


async def scrape_all(limit_sets: int | None = None):
	async with httpx.AsyncClient(
		headers={"User-Agent": settings.scraper_user_agent},
		timeout=30,
	) as client:
		db = SessionLocal()
		try:
			page = 1
			fetched = 0
			while True:
				data = await fetch_sets(client, page)
				sets = data.get("data", [])
				if not sets:
					break
				for s in sets:
					set_obj = await upsert_set(db, s)
					db.flush()
					cpage = 1
					while True:
						cdata = await fetch_cards(client, s["id"], cpage)
						cards = cdata.get("data", [])
						if not cards:
							break
						for c in cards:
							await upsert_card(db, set_obj, c)
						db.commit()
						cpage += 1
						await asyncio.sleep(0.5)
					fetched += 1
					if limit_sets and fetched >= limit_sets:
						db.commit()
						return
				page += 1
		finally:
			db.close()


if __name__ == "__main__":
	asyncio.run(scrape_all(limit_sets=3))
