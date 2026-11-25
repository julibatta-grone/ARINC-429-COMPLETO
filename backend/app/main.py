"""Punto de entrada FastAPI y servidor de la interfaz estática."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.database import initialize_database
from backend.app.routers import instruments, sends


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="ARINC-429-completo",
    description="Gestión de instrumentos y envíos de un banco de pruebas aeronáutico.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(instruments.router)
app.include_router(sends.router)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
