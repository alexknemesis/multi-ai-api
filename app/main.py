from fastapi import FastAPI
from .routers import ping, openai_image, gemini, runware, bfl

app = FastAPI(title="FastAPI REST")

# Routers
app.include_router(ping.router, tags=["health"])  # /ping
app.include_router(openai_image.router)  # /image/*
app.include_router(gemini.router)  # /gemini/*
app.include_router(runware.router)  # /runware/*
app.include_router(bfl.router)  # /bfl/*


@app.get("/", tags=["root"])
def root():
    return {"message": "API is running"}
