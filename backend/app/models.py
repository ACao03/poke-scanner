from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Set(Base):
	__tablename__ = "sets"

	id: Mapped[int] = mapped_column(primary_key=True)
	code: Mapped[str] = mapped_column(String(32), unique=True)
	name_en: Mapped[str | None]
	name_jp: Mapped[str | None]
	language: Mapped[str] = mapped_column(String(2), default="en")
	cards: Mapped[list["Card"]] = relationship(back_populates="set")


class Card(Base):
	__tablename__ = "cards"

	id: Mapped[int] = mapped_column(primary_key=True)
	set_id: Mapped[int] = mapped_column(ForeignKey("sets.id"))
	card_number: Mapped[str] = mapped_column(String(16))
	name_en: Mapped[str | None]
	name_jp: Mapped[str | None]
	rarity: Mapped[str | None]
	language: Mapped[str] = mapped_column(String(2), default="en")
	image_url: Mapped[str | None]
	phash: Mapped[str | None] = mapped_column(String(32))
	embedding: Mapped[list[float] | None] = mapped_column(Vector(512))

	set: Mapped[Set] = relationship(back_populates="cards")
	variants: Mapped[list["CardVariant"]] = relationship(back_populates="card")

	__table_args__ = (
		UniqueConstraint("set_id", "card_number", "language", name="uq_card"),
		Index(
			"ix_cards_embedding",
			"embedding",
			postgresql_using="ivfflat",
			postgresql_ops={"embedding": "vector_cosine_ops"},
		),
	)


class CardVariant(Base):
	__tablename__ = "card_variants"

	id: Mapped[int] = mapped_column(primary_key=True)
	card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
	variant: Mapped[str] = mapped_column(String(32))
	tcgplayer_product_id: Mapped[str | None]
	card: Mapped[Card] = relationship(back_populates="variants")


class Price(Base):
	__tablename__ = "prices"

	id: Mapped[int] = mapped_column(primary_key=True)
	variant_id: Mapped[int] = mapped_column(ForeignKey("card_variants.id"))
	captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
	market: Mapped[float | None] = mapped_column(Numeric(10, 2))
	low: Mapped[float | None] = mapped_column(Numeric(10, 2))
	mid: Mapped[float | None] = mapped_column(Numeric(10, 2))
	high: Mapped[float | None] = mapped_column(Numeric(10, 2))

	__table_args__ = (Index("ix_prices_variant_time", "variant_id", "captured_at"),)
