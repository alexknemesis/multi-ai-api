from fastapi import FastAPI
from .routers import ping, image, gemini

app = FastAPI(title="FastAPI REST")

# Routers
app.include_router(ping.router, tags=["health"])  # /ping
app.include_router(image.router)  # /image/*
app.include_router(gemini.router)  # /gemini/*


@app.get("/", tags=["root"])
def root():
    return {"message": "API is running"}
