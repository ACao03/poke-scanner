from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CardVariant, Price

router = APIRouter(prefix="/cards", tags=["prices"])


@router.get("/{card_id}/prices")
def prices(card_id: int, db: Session = Depends(get_db)):
	variants = db.scalars(select(CardVariant).where(CardVariant.card_id == card_id)).all()
	out = {}
	for v in variants:
		rows = db.scalars(
			select(Price)
			.where(Price.variant_id == v.id)
			.order_by(desc(Price.captured_at))
			.limit(90)
		).all()
		out[v.variant] = [
			{
				"at": r.captured_at.isoformat(),
				"market": float(r.market or 0),
				"low": float(r.low or 0),
				"mid": float(r.mid or 0),
				"high": float(r.high or 0),
			}
			for r in rows
		]
	return out
