from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cards, identify, prices

app = FastAPI(title="Pokemon TCG Card Scanner")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(cards.router)
app.include_router(identify.router)
app.include_router(prices.router)


@app.get("/health")
def health():
	return {"ok": True}
