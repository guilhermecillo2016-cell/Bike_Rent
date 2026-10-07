"""
servicos_tecnicos/iot
------------------------
Stub para o serviço técnico "IoT" do diagrama de arquitetura.
Futuramente: comunicação com travas/sensores das bicicletas e
estações, usado pelos domínios Bicicleta e Estacao.
"""
from servicos_tecnicos.iot.trava_inteligente import TravaInteligente
from servicos_tecnicos.iot.mock import TravaMock

_instancia: TravaInteligente | None = None

def get_trava() -> TravaInteligente:
    global _instancia
    if _instancia is None:
        _instancia = TravaMock()
    return _instancia

def set_trava(trava : TravaInteligente) -> None:
    """Permite trocar a implementação (testes ou trava real no futuro)"""
    global _instancia
    _instancia = trava