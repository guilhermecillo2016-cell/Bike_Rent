"""
main.py
-------
Ponto de entrada da aplicação. Sobe o FastAPI, registra as rotas de
Apresentação (WebClient e AdminWeb) e serve o front-end estático.

Rodar:
    uvicorn main:app --reload

Depois acesse http://127.0.0.1:8000/ (site do ciclista) e
http://127.0.0.1:8000/admin.html (área administrativa).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apresentacao import webclient, adminweb

app = FastAPI(title="Rota — Bike Sharing API")

app.include_router(webclient.router)
app.include_router(adminweb.router)

FRONTEND_DIR = Path(__file__).parent / "apresentacao" / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
