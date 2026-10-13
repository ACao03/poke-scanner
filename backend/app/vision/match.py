import imagehash
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Card
from app.vision.embed import embed_pil, phash_pil


def hamming_bits(a: str, b: str) -> int:
    """Hamming distance in bits (0 = identical, 64 = opposite) for 64-bit phash."""
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


def identify(db: Session, pil_full: Image.Image, pil_art: Image.Image, top_k: int = 5):
    emb = np.array(embed_pil(pil_art), dtype=np.float32)
    ph = phash_pil(pil_full)

    # Widen the ANN net — ask pgvector for 500 candidates, then rerank locally
    stmt = (
        select(Card)
        .where(Card.embedding.is_not(None))
        .order_by(Card.embedding.cosine_distance(emb))
        .limit(500)
    )
    candidates = list(db.scalars(stmt))

    scored = []
    for c in candidates:
        # Cosine SIMILARITY (1.0 = identical, -1.0 = opposite)
        emb_c = np.array(c.embedding, dtype=np.float32)
        cos_sim = float(np.dot(emb, emb_c))  # both already normalized

        # pHash similarity: 1.0 when identical, 0.0 when maximally different
        if c.phash:
            ph_bits = hamming_bits(ph, c.phash)          # 0..64
            ph_sim = 1.0 - (ph_bits / 64.0)              # 1..0
        else:
            ph_sim = None

        # Weighted combination. pHash dominates because it captures
        # exact-artwork similarity; ResNet18 contributes a coarse tiebreak.
        if ph_sim is not None:
            score = 0.6 * ph_sim + 0.4 * max(cos_sim, 0.0)
        else:
            score = max(cos_sim, 0.0)

        scored.append((score, c))

    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[:top_k]
