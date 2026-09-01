class CalculadoraView:
    def __init__(self, controller):
        self.controller = controller

    def mostrar_menu(self):
        print("=== Calculadora ===")
        print("1. Somar")
        print("2. Subtrair")
        print("3. Multiplicar")
        print("4. Dividir")
        print("5. Sair")

    def obter_opcao(self):
        opcion = input("Selecione uma opção: ")
        return opcion

    def obter_numeros(self):
        num1 = float(input("Digite o primeiro número: "))
        num2 = float(input("Digite o segundo número: "))
        return num1, num2

    def mostrar_resultado(self, resultado):
        print(f"Resultado: {resultado}")

    def mostrar_error(self, mensaje):
        print(f"Error: {mensaje}")