from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.api.cards import _to_out
from app.db import get_db
from app.schemas import Candidate, IdentifyResponse
from app.vision.match import identify as do_identify
from app.vision.preprocess import preprocess

router = APIRouter(tags=["identify"])


@router.post("/identify", response_model=IdentifyResponse)
async def identify(file: UploadFile = File(...), db: Session = Depends(get_db)):
	raw = await file.read()
	card_bgr, art_bgr = preprocess(raw)
	pil_full = Image.fromarray(card_bgr[:, :, ::-1])
	pil_art = Image.fromarray(art_bgr[:, :, ::-1])
	results = do_identify(db, pil_full, pil_art)
	return IdentifyResponse(
		candidates=[
			Candidate(card=_to_out(c), confidence=round(float(s), 4))
			for s, c in results
		]
	)
