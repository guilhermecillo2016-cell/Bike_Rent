"""
servicos_tecnicos/pagamentos/tokenizador.py
----------------------------------------------
Serviço técnico "Pagamentos" do diagrama de arquitetura.

Simula a tokenização feita por um gateway de pagamento real (ex:
Stripe, Cielo): recebe os dados do cartão, devolve um token opaco e
os últimos 4 dígitos para exibição — nunca devolve nem guarda o
número completo do cartão ou o CVV. Trocar essa função por uma
chamada real de gateway é a única mudança necessária para produção.
"""

import re
import uuid


def detectar_bandeira(numero_cartao: str) -> str:
    numero = re.sub(r"\D", "", numero_cartao)
    if numero.startswith("4"):
        return "Visa"
    if numero[:2] in {"51", "52", "53", "54", "55"}:
        return "Mastercard"
    if numero[:2] in {"34", "37"}:
        return "American Express"
    return "Desconhecida"


def tokenizar(numero_cartao: str) -> dict:
    """Retorna {token, ultimos_digitos, bandeira} a partir do número do cartão."""
    numero = re.sub(r"\D", "", numero_cartao)
    return {
        "token": "tok_" + uuid.uuid4().hex[:20],
        "ultimos_digitos": numero[-4:],
        "bandeira": detectar_bandeira(numero),
    }
