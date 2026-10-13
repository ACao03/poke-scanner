from typing import Optional

from pydantic import BaseModel


class CardOut(BaseModel):
	id: int
	name_en: Optional[str]
	name_jp: Optional[str]
	card_number: str
	set_code: str
	language: str
	image_url: Optional[str]

	class Config:
		from_attributes = True


class Candidate(BaseModel):
	card: CardOut
	confidence: float


class IdentifyResponse(BaseModel):
	candidates: list[Candidate]
