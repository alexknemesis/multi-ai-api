# API Documentation

Base URL: http://127.0.0.1:8000

## Variables de entorno
- `OPENAI_API_KEY` (para endpoints de `image` - OpenAI gpt-image-1)
- `GEMINI_API_KEY` (para endpoints de `gemini`)
- `RUNWARE_API_KEY` (para endpoint de `runware`)
- `BFL_API_KEY` (para endpoint de `bfl`)

---

## Salud

- Metodo: GET
- Path: `/ping`
- Respuesta:
```json
{
  "message": "pong"
}
```

---

## Raíz

- Metodo: GET
- Path: `/`
- Respuesta:
```json
{
  "message": "API is running"
}
```

---

## Runware: Generación de imagen

- Metodo: POST
- Path: `/runware/generate`
- Headers: `Content-Type: application/json`
- Body (JSON):
```json
{
  "prompt": "a cute robot made of leaves, studio lighting",
  "model": "rundiffusion:130@100"
}
```
`model` es opcional. Si no se envía, se usa `rundiffusion:130@100` por defecto.

- Respuesta (200):
```json
{
  "image_url": "https://im.runware.ai/image/ws/2/ii/f19923c4-a6fd-49f6-8bff-75d484742cb9.png",
  "saved_path": "generated/runware/runware_a-cute-robot_1724123456.png"
}
```

- cURL (Bash):
```bash
curl -X POST "http://127.0.0.1:8000/runware/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cute robot made of leaves, studio lighting"}'
```

- cURL (PowerShell):
```powershell
curl.exe -X POST "http://127.0.0.1:8000/runware/generate" `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"a cute robot made of leaves, studio lighting\"}"
```

Nota: La imagen se guarda automáticamente en `generated/runware/` (o en `<IMAGE_OUTPUT_DIR>/runware` si se define la variable `IMAGE_OUTPUT_DIR`).

---

## BFL (Black Forest Labs): Flux-Kontext

- Metodo: POST
- Path: `/bfl/flux-kontext`
- Headers: `Content-Type: application/json`
- Body (JSON):
```json
{
  "prompt": "mejorar contraste y colores",
  "image_base64": "data:image/png;base64,iVBOR...", 
  "creature_name": "DragonAzul",
  "prompt_label": "enhance"
}
```
`creature_name` y `prompt_label` son opcionales.

- Respuesta (200):
```json
{
  "result_image_url": "https://.../result.png",
  "saved_path": "generated/bfl/DragonAzul/enhance_1724123456.png"
}
```

- cURL (Bash):
```bash
curl -X POST "http://127.0.0.1:8000/bfl/flux-kontext" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"mejorar contraste y colores",
    "image_base64":"data:image/png;base64,REEMPLAZA_AQUI",
    "creature_name":"DragonAzul",
    "prompt_label":"enhance"
  }'
```

- cURL (PowerShell):
```powershell
curl.exe -X POST "http://127.0.0.1:8000/bfl/flux-kontext" `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"mejorar contraste y colores\",\"image_base64\":\"data:image/png;base64,REEMPLAZA_AQUI\",\"creature_name\":\"DragonAzul\",\"prompt_label\":\"enhance\"}"
```

Nota: La imagen se guarda automáticamente en `generated/bfl/<CREATURE_NAME>/` (o en `<IMAGE_OUTPUT_DIR>/bfl/<CREATURE_NAME>` si se define `IMAGE_OUTPUT_DIR`).

---

### BFL: Flux-Kontext (archivo)

- Metodo: POST
- Path: `/bfl/flux-kontext-file`
- Content-Type: `multipart/form-data`
- Fields (form-data):
  - `prompt` (text, requerido)
  - `image_file` (file, requerido; tipos: png/jpg/jpeg/webp)
  - `creature_name` (text, opcional)
  - `prompt_label` (text, opcional)

- Respuesta (200):
```json
{
  "result_image_url": "https://.../result.png",
  "saved_path": "generated/bfl/DragonAzul/enhance_1724123456.png"
}
```

- cURL (Bash):
```bash
curl -X POST "http://127.0.0.1:8000/bfl/flux-kontext-file" \
  -F "prompt=mejorar contraste y colores" \
  -F "image_file=@./generated/runware/ejemplo.png" \
  -F "creature_name=DragonAzul" \
  -F "prompt_label=enhance"
```

- cURL (PowerShell):
```powershell
curl.exe -X POST "http://127.0.0.1:8000/bfl/flux-kontext-file" `
  -F "prompt=mejorar contraste y colores" `
  -F "image_file=@.\generated\runware\ejemplo.png" `
  -F "creature_name=DragonAzul" `
  -F "prompt_label=enhance"
```

Nota: Requiere `python-multipart` (ya incluido en `requirements.txt`). La imagen resultante se guarda en `generated/bfl/<CREATURE_NAME>/` (o `<IMAGE_OUTPUT_DIR>/bfl/<CREATURE_NAME>` si se define `IMAGE_OUTPUT_DIR`).

---

## Gemini: Texto

- Metodo: POST
- Path: `/gemini/generate`
- Headers: `Content-Type: application/json`
- Body (JSON):
```json
{
  "system_prompt": "Responde de forma concisa.",
  "user_prompt": "Resume este texto..."
}
```
- Respuesta (200):
```json
{
  "output_text": "Texto generado por Gemini"
}
```

- cURL (Bash):
```bash
curl -X POST "http://127.0.0.1:8000/gemini/generate" \
  -H "Content-Type: application/json" \
  -d '{"system_prompt":"Responde de forma concisa.","user_prompt":"Resume este texto..."}'
```

- cURL (PowerShell):
```powershell
curl.exe -X POST "http://127.0.0.1:8000/gemini/generate" `
  -H "Content-Type: application/json" `
  -d "{\"system_prompt\":\"Responde de forma concisa.\",\"user_prompt\":\"Resume este texto...\"}"
```

---

## OpenAI Images (gpt-image-1): Generar imagen

- Metodo: POST
- Path: `/image/generate`
- Headers: `Content-Type: application/json`
- Body (JSON):
```json
{
  "prompt": "un dragón azul sobre una montaña nevada",
  "size": "1024x1024",
  "quality": "high"
}
```
- Query opcional: `download` (boolean). Si `true`, devuelve archivo como descarga.

- Respuesta (200) cuando `download` es `false` (por defecto):
```json
{
  "image_b64": "<BASE64_PNG>...",
  "content_type": "image/png",
  "saved_path": "generated/dragon_azul_169...png"
}
```

- cURL (Bash):
```bash
curl -X POST "http://127.0.0.1:8000/image/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"un dragón azul sobre una montaña nevada","size":"1024x1024","quality":"high"}'
```

- cURL (PowerShell):
```powershell
curl.exe -X POST "http://127.0.0.1:8000/image/generate" `
  -H "Content-Type: application/json" `
  -d "{\"prompt\":\"un dragón azul sobre una montaña nevada\",\"size\":\"1024x1024\",\"quality\":\"high\"}"
```

---

## OpenAI Images (gpt-image-1): Editar imagen con referencias (1-8 archivos)

Requiere `multipart/form-data` y tener instalado `python-multipart`.

- Metodo: POST
- Path: `/image/edit`
- Query opcional: `download` (boolean)
- Fields (form-data):
  - `prompt` (text)
  - `size` (text, p.ej. `1024x1024`)
  - `quality` (text, `low` | `high`)
  - `images` (file, 1 a 8 archivos, tipos: png/jpg/jpeg/webp)

- Respuesta (200) cuando `download=false`:
```json
{
  "image_b64": "<BASE64_PNG>...",
  "content_type": "image/png",
  "saved_path": "generated/edits/edit_...png"
}
```

- cURL (Bash, 2 imágenes de ejemplo):
```bash
curl -X POST "http://127.0.0.1:8000/image/edit?download=false" \
  -F "prompt=mejorar contraste y colores" \
  -F "size=1024x1024" \
  -F "quality=high" \
  -F "images=@./ejemplo1.png" \
  -F "images=@./ejemplo2.jpg"
```

- cURL (PowerShell, 2 imágenes de ejemplo):
```powershell
curl.exe -X POST "http://127.0.0.1:8000/image/edit?download=false" `
  -F "prompt=mejorar contraste y colores" `
  -F "size=1024x1024" `
  -F "quality=high" `
  -F "images=@.\ejemplo1.png" `
  -F "images=@.\ejemplo2.jpg"
```

---

## Notas
- Para probar rápido via UI: `http://127.0.0.1:8000/docs`
- Si usas PowerShell, escapa comillas en JSON como en el ejemplo de Runware.
- Asegúrate de definir las API keys en `.env` o en variables de entorno del sistema.
