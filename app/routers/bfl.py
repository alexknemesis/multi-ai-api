import os
import re
import time
import base64
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/bfl", tags=["bfl"])

BFL_API_URL = "https://api.bfl.ai/v1/flux-kontext-pro"
POLLING_INTERVAL_SECONDS = 3
MAX_POLLING_ATTEMPTS = 20


class BFLKontextRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Texto que describe la edición a realizar")
    image_base64: str = Field(..., min_length=1, description="Imagen en base64 (puede incluir prefijo data:image/...)")
    creature_name: Optional[str] = Field("UnknownCreature", description="Nombre de la criatura para organizar las imágenes")
    prompt_label: Optional[str] = Field("image", description="Etiqueta base del archivo de salida")


class BFLKontextResponse(BaseModel):
    result_image_url: str
    saved_path: str


@router.post("/flux-kontext", response_model=BFLKontextResponse)
def flux_kontext(body: BFLKontextRequest):
    api_key = os.getenv("BFL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta BFL_API_KEY en variables de entorno")

    prompt = body.prompt.strip()
    image_b64 = body.image_base64.strip()

    if not prompt or not image_b64:
        raise HTTPException(status_code=400, detail="Faltan datos obligatorios (prompt o image_base64)")

    # Si la imagen viene con prefijo data:image, quitarlo
    if image_b64.startswith("data:image"):
        parts = image_b64.split(",", 1)
        image_b64 = parts[1] if len(parts) == 2 else image_b64

    payload = {
        "prompt": prompt,
        "input_image": image_b64,
        "safety_tolerance": 2,
        "output_format": "png",
        "prompt_upsampling": False,
    }

    headers = {
        "accept": "application/json",
        "x-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=60) as client:
            initial_response = client.post(BFL_API_URL, json=payload, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de red al llamar a BFL: {e}")

    if initial_response.status_code != 200:
        try:
            details = initial_response.json()
        except Exception:
            details = initial_response.text
        raise HTTPException(status_code=initial_response.status_code, detail={"error": "API error inicial", "details": details})

    try:
        initial_data = initial_response.json()
        polling_url = initial_data.get("polling_url")
        request_id = initial_data.get("id")
    except Exception:
        polling_url = None
        request_id = None

    if not polling_url:
        raise HTTPException(status_code=502, detail={"error": "API error: polling URL no recibido.", "details": initial_response.text})

    # Polling
    poll_headers = {"accept": "application/json", "x-key": api_key}
    poll_client = httpx.Client(timeout=60)
    try:
        for _ in range(MAX_POLLING_ATTEMPTS):
            try:
                poll_response = poll_client.get(polling_url, headers=poll_headers)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Error durante el polling: {e}")

            if poll_response.status_code != 200:
                try:
                    details = poll_response.json()
                except Exception:
                    details = poll_response.text
                raise HTTPException(status_code=poll_response.status_code, detail={"error": "Error en polling", "details": details})

            try:
                poll_data = poll_response.json()
            except Exception:
                raise HTTPException(status_code=502, detail="Respuesta de polling inválida")

            status = poll_data.get("status")
            if status == "Ready":
                result = poll_data.get("result") or {}
                image_result_url = result.get("sample")
                if not image_result_url:
                    raise HTTPException(status_code=502, detail={"error": "Procesado pero sin URL de imagen.", "details": poll_data})

                # Guardar imagen localmente
                safe_creature = re.sub(r"[^\w\-_ ]", "", body.creature_name or "UnknownCreature").replace(" ", "_")
                safe_label = re.sub(r"[^\w\-_ ]", "", body.prompt_label or "image").replace(" ", "_")
                output_dir = Path(os.getenv("IMAGE_OUTPUT_DIR", "generated")) / "bfl" / safe_creature
                try:
                    output_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"No se pudo crear el directorio de salida: {e}")

                base_url = (image_result_url or "").split("?", 1)[0]
                ext = os.path.splitext(base_url)[1].lower()
                if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                    ext = ".png"

                filename = f"{safe_label}_{int(time.time())}{ext}"
                file_path = output_dir / filename

                try:
                    with httpx.Client(timeout=120) as dl_client:
                        img_resp = dl_client.get(image_result_url)
                    if img_resp.status_code != 200:
                        raise HTTPException(status_code=502, detail=f"No se pudo descargar la imagen: status {img_resp.status_code}")
                    with open(file_path, "wb") as f:
                        f.write(img_resp.content)
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Imagen generada pero no se pudo guardar localmente: {e}")

                return BFLKontextResponse(result_image_url=image_result_url, saved_path=str(file_path))

            elif status in ("Failed", "Error"):
                raise HTTPException(status_code=502, detail={"error": f"Falló el procesamiento en BFL (Status: {status}).", "details": poll_data.get("details") or poll_data})

            time.sleep(POLLING_INTERVAL_SECONDS)
    finally:
        poll_client.close()

    raise HTTPException(status_code=503, detail={"error": "El procesamiento está tardando demasiado.", "status": "Timeout", "request_id": request_id})


@router.post("/flux-kontext-file", response_model=BFLKontextResponse)
def flux_kontext_file(
    prompt: str = Form(..., min_length=1, description="Texto que describe la edición a realizar"),
    image_file: UploadFile = File(..., description="Imagen a subir (png, jpg, jpeg, webp)"),
    creature_name: Optional[str] = Form("UnknownCreature", description="Nombre de la criatura para organizar las imágenes"),
    prompt_label: Optional[str] = Form("image", description="Etiqueta base del archivo de salida"),
):
    try:
        # Lectura síncrona del archivo
        content = image_file.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer la imagen: {e}")

    if not content:
        raise HTTPException(status_code=400, detail="Archivo de imagen vacío")

    # Convertir a base64 sin prefijo data:
    image_b64 = base64.b64encode(content).decode("utf-8")

    # Reutilizar la lógica del endpoint JSON
    body = BFLKontextRequest(
        prompt=prompt,
        image_base64=image_b64,
        creature_name=creature_name,
        prompt_label=prompt_label,
    )
    return flux_kontext(body)
