import os
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import re
import time
from pathlib import Path

load_dotenv()

router = APIRouter(prefix="/runware", tags=["runware"])

RUNWARE_ENDPOINT = "https://api.runware.ai/v1/generate"


class RunwareRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Texto que describe la imagen a generar")
    model: Optional[str] = Field(
        None,
        description="Modelo de Runware, ej: 'rundiffusion:130@100' (opcional)",
    )


class RunwareResponse(BaseModel):
    image_url: str
    saved_path: str


@router.post("/generate", response_model=RunwareResponse)
def generate_image(body: RunwareRequest):
    api_key = os.getenv("RUNWARE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta RUNWARE_API_KEY en variables de entorno")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    task_uuid = str(uuid.uuid4())
    model_to_use = body.model or "rundiffusion:130@100"

    payload = [
        {
            "taskType": "imageInference",
            "taskUUID": task_uuid,
            "positivePrompt": body.prompt,
            "model": model_to_use,
            "outputType": "URL",
            "outputFormat": "PNG",
            "outputQuality": 95,
            "numberResults": 1,
            "includeCost": False,
            "width": 768,
            "height": 768,
        }
    ]

    try:
        with httpx.Client(timeout=60) as client:
            r = client.post(RUNWARE_ENDPOINT, headers=headers, json=payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de red al llamar a Runware: {e}")

    if r.status_code != 200:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise HTTPException(status_code=502, detail={"status": r.status_code, "error": detail})

    try:
        out = r.json()
        data_list = out.get("data") or []
        first = data_list[0] if isinstance(data_list, list) and data_list else None
        image_url = first.get("imageURL") if isinstance(first, dict) else None
    except Exception:
        image_url = None

    if not image_url:
        raise HTTPException(status_code=502, detail="La respuesta de Runware.ai no contiene 'imageURL'.")

    # Descargar y guardar localmente
    output_dir = Path(os.getenv("IMAGE_OUTPUT_DIR", "generated")) / "runware"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el directorio de salida: {e}")

    # Crear nombre de archivo seguro
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", body.prompt).strip("-")
    slug = re.sub(r"-+", "-", slug)
    base_url = image_url.split("?")[0]
    ext = os.path.splitext(base_url)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"
    filename = f"runware_{slug[:40]}_{int(time.time())}{ext}"
    file_path = output_dir / filename

    try:
        with httpx.Client(timeout=120) as client:
            img_resp = client.get(image_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error descargando la imagen de Runware: {e}")

    if img_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"No se pudo descargar la imagen: status {img_resp.status_code}")

    try:
        with open(file_path, "wb") as f:
            f.write(img_resp.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la imagen: {e}")

    return RunwareResponse(image_url=image_url, saved_path=str(file_path))
