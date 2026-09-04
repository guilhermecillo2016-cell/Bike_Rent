from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from domain.CalculadoraService import CalculadoraService

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
 
templates = Jinja2Templates(directory=TEMPLATES_DIR)
service = CalculadoraService()
 
 
class CalculadoraView:
    
 
    def mostrar_formulario(self, request: Request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {"resultado": None, "erro": None},
        )
 
    def somar(self, request: Request, num1: float, num2: float):
        resultado = service.somar(num1, num2)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "resultado": resultado,
                "num1": num1,
                "num2": num2,
                "erro": None,
            },
        )
 
 
view = CalculadoraView()
 
 
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return view.mostrar_formulario(request)
 
 
@app.post("/somar", response_class=HTMLResponse)
def somar(request: Request, num1: float = Form(...), num2: float = Form(...)):
    return view.somar(request, num1, num2)
 
 
if __name__ == "__main__":
    import uvicorn
 
    uvicorn.run("CalculadoraView:app", host="127.0.0.1", port=8000, reload=True)