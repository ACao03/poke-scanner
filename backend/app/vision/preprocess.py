import cv2
import numpy as np

CARD_W, CARD_H = 750, 1050


def find_card_quad(img: np.ndarray) -> np.ndarray | None:
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (5, 5), 0)
	edges = cv2.Canny(gray, 50, 150)
	edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
	contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
	for c in contours:
		peri = cv2.arcLength(c, True)
		approx = cv2.approxPolyDP(c, 0.02 * peri, True)
		if len(approx) == 4 and cv2.contourArea(approx) > 0.2 * img.shape[0] * img.shape[1]:
			return approx.reshape(4, 2).astype(np.float32)
	return None


def order_pts(pts: np.ndarray) -> np.ndarray:
	s = pts.sum(axis=1)
	d = np.diff(pts, axis=1).ravel()
	return np.array(
		[pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
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


def normalize(img: np.ndarray) -> np.ndarray:
	lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
	l, a, b = cv2.split(lab)
	l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
	return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def preprocess(raw_bytes: bytes) -> tuple[np.ndarray, np.ndarray]:
	"""Return (full card crop, art box crop)."""
	arr = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
	if arr is None:
		raise ValueError("bad image")
	quad = find_card_quad(arr)
	card = warp_card(arr, quad) if quad is not None else cv2.resize(arr, (CARD_W, CARD_H))
	card = normalize(card)
	art = card[int(0.11 * CARD_H) : int(0.58 * CARD_H), int(0.08 * CARD_W) : int(0.92 * CARD_W)]
	return card, art
