import io

import httpx
import imagehash
import numpy as np
import timm
import torch
from PIL import Image

_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = timm.create_model("resnet18", pretrained=True, num_classes=0).eval().to(_device)
_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def _prep(pil: Image.Image, size: int = 224) -> torch.Tensor:
	img = pil.convert("RGB").resize((size, size))
	x = torch.from_numpy(np.asarray(img)).float() / 255.0
	x = x.permute(2, 0, 1).unsqueeze(0)
	return (x - _MEAN) / _STD


@torch.no_grad()
def embed_pil(pil: Image.Image) -> list[float]:
	x = _prep(pil).to(_device)
	v = _model(x).cpu().numpy().ravel()
	v = v / (np.linalg.norm(v) + 1e-8)
	if v.shape[0] < 512:
		v = np.pad(v, (0, 512 - v.shape[0]))
	return v[:512].tolist()


def phash_pil(pil: Image.Image) -> str:
	return str(imagehash.phash(pil.convert("RGB")))


async def embed_image_from_url(url: str) -> tuple[list[float], str]:
	async with httpx.AsyncClient(timeout=30) as client:
		r = await client.get(url)
		r.raise_for_status()
	pil = Image.open(io.BytesIO(r.content))
	return embed_pil(pil), phash_pil(pil)
