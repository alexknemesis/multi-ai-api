import os
import base64
import re
import time
from pathlib import Path
from typing import Literal, List

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI

# Carga variables de entorno desde .env
load_dotenv()

# El cliente se inicializa dentro del endpoint para validar la API key

router = APIRouter(prefix="/image", tags=["image"])


class ImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Texto que describe la imagen a generar")
    size: str = Field(..., pattern=r"^\d+x\d+$", description="Tamaño de la imagen, ej: 256x256, 512x512, 1024x1024")
    quality: Literal["low", "high"] = Field(..., description="Calidad de la imagen")


class ImageResponse(BaseModel):
    image_b64: str
    content_type: str = "image/png"
    saved_path: str


@router.post("/edit", response_model=ImageResponse)
def edit_image(
    prompt: str = Form(..., min_length=1, description="Texto que describe la edición a realizar"),
    size: str = Form(..., description="Tamaño de la imagen, ej: 256x256, 512x512, 1024x1024"),
    quality: Literal["low", "high"] = Form(..., description="Calidad de la imagen"),
    images: List[UploadFile] = File(..., description="1-8 imágenes de referencia"),
    download: bool = Query(False, description="Si true, devuelve el archivo como descarga (attachment)"),
):
    """Edita/genera una imagen a partir de múltiples imágenes de referencia (hasta 8)."""
    # Validaciones básicas
    if not re.match(r"^\d+x\d+$", size or ""):
        raise HTTPException(status_code=422, detail="El parámetro 'size' debe tener el formato WIDTHxHEIGHT, p.ej. 1024x1024")

    if not images or len(images) == 0:
        raise HTTPException(status_code=400, detail="Debes enviar entre 1 y 8 imágenes en 'images'")
    if len(images) > 8:
        raise HTTPException(status_code=400, detail="Se permiten como máximo 8 imágenes de referencia")

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    for uf in images:
        if uf.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Tipo de imagen no soportado: {uf.content_type}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta OPENAI_API_KEY en variables de entorno")
    client = OpenAI(api_key=api_key)

    # Guardar referencias temporalmente para proporcionar archivos con nombre a la API
    tmp_dir = Path(os.getenv("IMAGE_TMP_DIR", "generated/tmp"))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    open_files = []
    tmp_paths = []
    ts = int(time.time())
    try:
        for idx, uf in enumerate(images[:8]):
            try:
                uf.file.seek(0)
                data = uf.file.read()
            except Exception:
                raise HTTPException(status_code=400, detail="No se pudo leer uno de los archivos subidos")

            ext = os.path.splitext(uf.filename or "")[1].lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
                # Si la extensión no es reconocida, predeterminar a .png
                ext = ".png"

            tmp_path = tmp_dir / f"ref_{ts}_{idx}{ext}"
            try:
                with open(tmp_path, "wb") as f:
                    f.write(data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al escribir archivo temporal: {e}")

            try:
                f = open(tmp_path, "rb")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al abrir archivo temporal: {e}")

            open_files.append(f)
            tmp_paths.append(tmp_path)

        # Llamada a la API de OpenAI para editar con múltiples imágenes
        try:
            img = client.images.edit(
                model="gpt-image-1",
                image=open_files,
                prompt=prompt,
                n=1,
                quality=quality,
                size=size,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")
    finally:
        # Cerrar handles
        for f in open_files:
            try:
                f.close()
            except Exception:
                pass
        # Limpiar archivos temporales
        for p in tmp_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

    try:
        b64_png = img.data[0].b64_json
    except Exception:
        raise HTTPException(status_code=500, detail="No se pudo obtener la imagen editada")

    # Decodificar y guardar
    try:
        image_bytes = base64.b64decode(b64_png)
    except Exception:
        raise HTTPException(status_code=500, detail="Error al decodificar la imagen base64")

    output_dir = Path(os.getenv("IMAGE_OUTPUT_DIR", "generated")) / "edits"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el directorio de salida: {e}")

    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", prompt).strip("-")
    slug = re.sub(r"-+", "-", slug)
    filename = f"edit_{slug[:40]}_{int(time.time())}.png" if slug else f"edit_{int(time.time())}.png"
    file_path = output_dir / filename

    try:
        with open(file_path, "wb") as f:
            f.write(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la imagen: {e}")

    if download:
        return FileResponse(
            path=str(file_path),
            media_type="image/png",
            filename=file_path.name,
        )

    return ImageResponse(image_b64=b64_png, saved_path=str(file_path))

@router.post("/generate", response_model=ImageResponse)
def generate_image(
    body: ImageRequest,
    download: bool = Query(False, description="Si true, devuelve el archivo como descarga (attachment)"),
):
    """Genera una imagen con gpt-image-1 y devuelve la imagen en Base64 (PNG)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta OPENAI_API_KEY en variables de entorno")

    client = OpenAI(api_key=api_key)

    prompt = body.prompt
    try:
        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            background="transparent",
            n=1,
            quality=body.quality,
            size=body.size,
            moderation="auto",
            output_format="png",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    try:
        b64_png = img.data[0].b64_json
    except Exception:
        raise HTTPException(status_code=500, detail="No se pudo obtener la imagen generada")

    # Decodificar y guardar localmente
    try:
        image_bytes = base64.b64decode(b64_png)
    except Exception:
        raise HTTPException(status_code=500, detail="Error al decodificar la imagen base64")

    output_dir = Path(os.getenv("IMAGE_OUTPUT_DIR", "generated"))
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el directorio de salida: {e}")

    # Crear un nombre de archivo seguro a partir del prompt
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", prompt).strip("-")
    slug = re.sub(r"-+", "-", slug)
    filename = f"{slug[:40]}_{int(time.time())}.png" if slug else f"image_{int(time.time())}.png"
    file_path = output_dir / filename

    try:
        with open(file_path, "wb") as f:
            f.write(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la imagen: {e}")

    if download:
        # Devuelve el archivo directamente como descarga
        return FileResponse(
            path=str(file_path),
            media_type="image/png",
            filename=file_path.name,
        )

    return ImageResponse(image_b64=b64_png, saved_path=str(file_path))
