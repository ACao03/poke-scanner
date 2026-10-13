from datetime import datetime, timezone
import asyncio
import sys

from celery import Celery
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db import SessionLocal
from app.models import Card, CardVariant, Price, Set
from app.scraper.open_tcg import OpenTCGClient

celery = Celery("poke", broker=settings.redis_url, backend=settings.redis_url)

celery.conf.beat_schedule = {
	"refresh-prices-daily": {
		"task": "app.scraper.tasks.refresh_prices",
		"schedule": 86400,
	},
}


@celery.task
def refresh_prices():
	"""Refresh prices via configured provider.

	When OPEN_TCG_ENABLED=true, use Open TCG API as a non-partner fallback source.
	Otherwise keep placeholder behavior for partner-only integrations.
	"""
	if settings.open_tcg_enabled:
		return asyncio.run(_refresh_prices_open_tcg(dry_run=False))

	db = SessionLocal()
	try:
		for v in db.query(CardVariant).filter(CardVariant.tcgplayer_product_id.isnot(None)).all():
			db.add(
				Price(
					variant_id=v.id,
					captured_at=datetime.now(timezone.utc),
					market=0,
					low=0,
					mid=0,
					high=0,
				)
			)
		db.commit()
		return {"source": "placeholder", "inserted": 0}
	finally:
		db.close()


@celery.task
def refresh_prices_smoke_test():
	"""Dry-run Open TCG pricing pass without writing rows.

	Returns matching statistics so ingestion can be validated safely.
	"""
	if not settings.open_tcg_enabled:
		return {
			"source": "open_tcg",
			"dry_run": True,
			"error": "OPEN_TCG_ENABLED is false",
		}
	try:
		return asyncio.run(_refresh_prices_open_tcg(dry_run=True))
	except SQLAlchemyError as exc:
		return {
			"source": "open_tcg",
			"dry_run": True,
			"error": "database_unavailable",
			"detail": str(exc),
		}
	except Exception as exc:  # pragma: no cover - defensive guard for smoke diagnostics
		return {
			"source": "open_tcg",
			"dry_run": True,
			"error": "smoke_test_failed",
			"detail": str(exc),
		}


def _norm(value: str | None) -> str:
	return (value or "").strip().lower().replace(" ", "")


def _pick(row: dict, keys: tuple[str, ...]) -> str | None:
	for key in keys:
		value = row.get(key)
		if value not in (None, ""):
			return str(value)
	return None


def _pick_price(row: dict, key: str) -> float | None:
	value = row.get(key)
	if value is None and isinstance(row.get("prices"), dict):
		value = row["prices"].get(key)
	if value is None:
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _variant_from_row(row: dict) -> str:
	return (
		_pick(row, ("variant", "finish", "printing", "printType", "condition"))
		or "normal"
	)


async def _refresh_prices_open_tcg(*, dry_run: bool) -> dict:
	client = OpenTCGClient()
	remote_sets = await client.fetch_sets()
	remote_by_code: dict[str, dict] = {}
	for item in remote_sets:
		for key in ("code", "setCode", "abbreviation"):
			code = _norm(_pick(item, (key,)))
			if code:
				remote_by_code[code] = item

	db = SessionLocal()
	matched_sets = 0
	scanned_rows = 0
	matched_rows = 0
	variants_created = 0
	inserted = 0
	try:
		for local_set in db.scalars(select(Set)).all():
			remote = remote_by_code.get(_norm(local_set.code))
			if not remote:
				continue

			remote_set_id = _pick(remote, ("id", "setId", "set_id"))
			if not remote_set_id:
				continue
			matched_sets += 1

			rows = await client.fetch_set_pricing(remote_set_id)
			scanned_rows += len(rows)
			cards_by_number = {
				c.card_number: c
				for c in db.scalars(select(Card).where(Card.set_id == local_set.id)).all()
			}

			for row in rows:
				card_number = _pick(row, ("number", "cardNumber", "collectorNumber", "card_number"))
				if not card_number:
					continue
				card = cards_by_number.get(str(card_number))
				if not card:
					continue
				matched_rows += 1

				variant_name = _variant_from_row(row)
				variant = next((v for v in card.variants if _norm(v.variant) == _norm(variant_name)), None)
				if variant is None:
					if dry_run:
						variants_created += 1
						inserted += 1
						continue
					variant = CardVariant(card_id=card.id, variant=variant_name)
					db.add(variant)
					db.flush()
					variants_created += 1

				if dry_run:
					inserted += 1
					continue

				db.add(
					Price(
						variant_id=variant.id,
						captured_at=datetime.now(timezone.utc),
						market=_pick_price(row, "market"),
						low=_pick_price(row, "low"),
						mid=_pick_price(row, "mid"),
						high=_pick_price(row, "high"),
					)
				)
				inserted += 1

		if dry_run:
			db.rollback()
		else:
			db.commit()
		return {
			"source": "open_tcg",
			"dry_run": dry_run,
			"remote_sets": len(remote_sets),
			"matched_sets": matched_sets,
			"scanned_rows": scanned_rows,
			"matched_rows": matched_rows,
			"variants_created": variants_created,
			"inserted": inserted,
		}
	finally:
		db.close()


if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == "smoke":
		print(refresh_prices_smoke_test())
	else:
		print(refresh_prices())
