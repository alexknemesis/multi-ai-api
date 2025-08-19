# FastAPI REST

## Requisitos
- Python 3.9+
- Windows PowerShell

## Pasos rápidos (Windows)

1) Crear entorno virtual
```
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Actualizar pip e instalar dependencias
```
python -m pip install -U pip
pip install -r requirements.txt
```

3) Ejecutar el servidor
```
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4) Probar
- http://127.0.0.1:8000/ping
- http://127.0.0.1:8000/docs
