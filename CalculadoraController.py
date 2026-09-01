from model.CalculadoraService import CalculadoraService
from view.CalculadoraView import CalculadoraView


class CalculadoraController:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def somar(self):
        a, b = self.view.obter_numeros()
        self.view.mostrar_resultado(self.model.somar(a, b))

    def subtrair(self):
        a, b = self.view.obter_numeros()
        self.view.mostrar_resultado(self.model.subtrair(a, b))

    def multiplicar(self):
        a, b = self.view.obter_numeros()
        self.view.mostrar_resultado(self.model.multiplicar(a, b))

    def dividir(self):
        a, b = self.view.obter_numeros()
        self.view.mostrar_resultado(self.model.dividir(a, b))

service = CalculadoraService()
view = CalculadoraView(None)
controller = CalculadoraController(service, view)
controller.somar()