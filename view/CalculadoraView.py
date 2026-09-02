from flask import Flask, request, render_template
import os
import sys

# Adiciona a pasta raiz ('Bike_Rent') ao caminho de busca do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from domain.CalculadoraService import CalculadoraService

app = Flask(__name__)
service = CalculadoraService()


class CalculadoraView:
    """Camada de apresentação (View) — agora também trata as requisições web."""

    def mostrar_formulario(self):
        return render_template("index.html", resultado=None, erro=None)

    def somar(self):
        try:
            num1 = float(request.form["num1"])
            num2 = float(request.form["num2"])
        except (ValueError, KeyError):
            return render_template("index.html", resultado=None,
                                    erro="Por favor, insira dois números válidos.")

        resultado = service.somar(num1, num2)
        return render_template("index.html", resultado=resultado,
                                num1=num1, num2=num2, erro=None)


view = CalculadoraView()


@app.route("/", methods=["GET"])
def index():
    return view.mostrar_formulario()


@app.route("/somar", methods=["POST"])
def somar():
    return view.somar()


if __name__ == "__main__":
    app.run(debug=True)