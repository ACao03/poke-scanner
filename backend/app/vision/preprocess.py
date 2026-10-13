import cv2
import numpy as np

CARD_W, CARD_H = 750, 1050


def normalize(img: np.ndarray) -> np.ndarray:
    """Mild CLAHE. Kept gentle so pHash values stay stable."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)



def find_card_quad(img: np.ndarray) -> np.ndarray | None:
    """Return the outer card boundary as a 4-point quad, or None if
    no convincing card shape is found."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 30, 100)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    h, w = img.shape[:2]
    img_area = float(h * w)
    TARGET_AR = 0.716
    AR_TOL = 0.15  # 0.566 – 0.866

    best = None
    best_area = 0.0
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        area = cv2.contourArea(approx)
        if area < 0.4 * img_area:
            # Reject anything covering less than 40% of the frame —
            # that's an inner panel, not a card photographed on a desk
            continue

        x, y, bw, bh = cv2.boundingRect(approx)
        ar = bw / bh if bh > 0 else 0
        if not (TARGET_AR - AR_TOL <= ar <= TARGET_AR + AR_TOL):
            continue

        if area > best_area:
            best = approx.reshape(4, 2).astype(np.float32)
            best_area = area

    return best


def order_pts(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)],
         pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype=np.float32,
    )


def warp_card(img: np.ndarray, quad: np.ndarray) -> np.ndarray:
    src = order_pts(quad)
    dst = np.array(
        [[0, 0], [CARD_W - 1, 0], [CARD_W - 1, CARD_H - 1], [0, CARD_H - 1]],
        np.float32,
    )
    mtx = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, mtx, (CARD_W, CARD_H))



def quad_touches_edges(quad: np.ndarray, img_shape: tuple[int, int], margin: int = 20) -> bool:
    """True if any of the quad's corners is within `margin` px of the frame."""
    h, w = img_shape[:2]
    for x, y in quad:
        if x < margin or y < margin or x > w - margin or y > h - margin:
            return True
    return False


def preprocess(raw_bytes: bytes) -> tuple[np.ndarray, np.ndarray]:
    arr = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise ValueError("bad image")

    h, w = arr.shape[:2]

    quad = find_card_quad(arr)
    if quad is not None and not quad_touches_edges(quad, arr.shape, margin=20):
        # Card found, and its corners are well inside the frame → real
        # photo with background. Warp.
        card = warp_card(arr, quad)
    else:
        # Either no card detected, or the detected quad extends to the
        # frame edges → clean scan. Just resize, don't warp.
        card = cv2.resize(arr, (CARD_W, CARD_H))

    card = normalize(card)
    art = card[
        int(0.11 * CARD_H) : int(0.58 * CARD_H),
        int(0.08 * CARD_W) : int(0.92 * CARD_W),
    ]
    return card, art
