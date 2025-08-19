import os
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/gemini", tags=["gemini"])

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


class GeminiRequest(BaseModel):
    system_prompt: str = Field(..., min_length=1, description="Instrucciones del sistema para el agente")
    user_prompt: str = Field(..., min_length=1, description="Mensaje del usuario")


class GeminiResponse(BaseModel):
    output_text: str


def _extract_text(resp_json: dict) -> str:
    try:
        candidates = resp_json.get("candidates") or []
        if not candidates:
            return ""
        parts = []
        content = candidates[0].get("content") or {}
        for p in content.get("parts", []):
            t = p.get("text")
            if isinstance(t, str):
                parts.append(t)
        return "\n".join(parts).strip()
    except Exception:
        return ""


@router.post("/generate", response_model=GeminiResponse)
def generate(body: GeminiRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta GEMINI_API_KEY en variables de entorno")

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": body.user_prompt}],
            }
        ],
        # System prompt como systemInstruction en v1beta
        "systemInstruction": {
            "parts": [{"text": body.system_prompt}],
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    }

    try:
        with httpx.Client(timeout=60) as client:
            r = client.post(GEMINI_ENDPOINT, headers=headers, json=payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de red al llamar a Gemini: {e}")

    if r.status_code != 200:
        # Devuelve mensaje de error de Gemini para depurar
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise HTTPException(status_code=502, detail={"status": r.status_code, "error": detail})

    data = r.json()
    text = _extract_text(data)
    return GeminiResponse(output_text=text)
