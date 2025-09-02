# FastAPI REST

## Requisitos
- Python 3.9+
- Windows PowerShell

## Pasos rápidos (Windows)

1) Crear y activar el entorno virtual (PowerShell)
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

CMD (opcional):
```
python -m venv .venv
.\.venv\Scripts\activate.bat
```

2) Actualizar pip e instalar dependencias
```
python -m pip install -U pip
python -m pip install -r requirements.txt
```

3) Variables de entorno
- Copia `env.example` a `.env` si es necesario.
- Define: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `RUNWARE_API_KEY`, `BFL_API_KEY`.

4) Ejecutar el servidor
```
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5) Probar
- http://127.0.0.1:8000/ping
- http://127.0.0.1:8000/docs
