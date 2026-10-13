import imagehash
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Card
from app.vision.embed import embed_pil, phash_pil


def hamming(a: str, b: str) -> int:
	return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


def identify(db: Session, pil_full: Image.Image, pil_art: Image.Image, top_k: int = 5):
	emb = np.array(embed_pil(pil_art), dtype=np.float32)
	ph = phash_pil(pil_full)

	stmt = (
		select(Card)
		.where(Card.embedding.is_not(None))
		.order_by(Card.embedding.cosine_distance(emb))
		.limit(200)
	)
	candidates = list(db.scalars(stmt))

	scored = []
	for c in candidates:
		art_sim = 1.0 - float(np.dot(emb, np.array(c.embedding)))
		ph_sim = hamming(ph, c.phash) / 64.0 if c.phash else 1.0
		score = 0.7 * (1 - art_sim) + 0.3 * (1 - ph_sim)
		scored.append((score, c))
	scored.sort(key=lambda t: t[0], reverse=True)
	return scored[:top_k]
