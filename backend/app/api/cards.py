from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Card, Set
from app.schemas import CardOut

router = APIRouter(prefix="/cards", tags=["cards"])


def _to_out(c: Card) -> CardOut:
	return CardOut(
		id=c.id,
		name_en=c.name_en,
		name_jp=c.name_jp,
		card_number=c.card_number,
		set_code=c.set.code,
		language=c.language,
		image_url=c.image_url,
	)


@router.get("/search")
def search(
	q: str = Query(..., min_length=1),
	lang: str | None = None,
	limit: int = 20,
	db: Session = Depends(get_db),
):
	stmt = select(Card).join(Set)
	like = f"%{q.lower()}%"
	stmt = stmt.where(
		or_(
			Card.name_en.ilike(like),
			Card.name_jp.ilike(like),
			Card.card_number.ilike(like),
		)
	)
	if lang:
		stmt = stmt.where(Card.language == lang)
	rows = db.scalars(stmt.limit(limit)).all()
	return [_to_out(c) for c in rows]


@router.get("/{card_id}")
def get_card(card_id: int, db: Session = Depends(get_db)):
	c = db.get(Card, card_id)
	return _to_out(c) if c else None
