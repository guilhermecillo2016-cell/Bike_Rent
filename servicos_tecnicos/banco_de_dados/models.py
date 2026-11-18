"""
servicos_tecnicos/banco_de_dados/models.py
----------------------------------------------
Camada de COMPATIBILIDADE. As classes de domínio ficam cada uma no seu
arquivo, dentro de dominio/<pacote>/, com o nome do diagrama:

    Usuario            dominio/usuario/usuario.py
    Estacao            dominio/estacao/estacao.py
    Bicicleta          dominio/bicicleta/bicicleta.py  (+ estados_bicicleta.py)
    Locacao            dominio/locacao/locacao.py
    PacoteMinutos      dominio/pacote/pacote_minutos.py
    Pagamento          dominio/pagamento/pagamento.py
    Cartao             dominio/pagamento/cartao.py
    ReporteAvaria      dominio/avaria/reporte_avaria.py
    ComprovanteViagem  dominio/comprovante/comprovante_viagem.py
    EventoAuditoria    dominio/auditoria/evento_auditoria.py

Aqui só se reimporta tudo e se mantêm os nomes antigos (LocacaoORM etc.)
para quem ainda importa por este módulo.
"""

from dominio.auditoria.evento_auditoria import EventoAuditoria
from dominio.avaria.reporte_avaria import ReporteAvaria
from dominio.bicicleta.bicicleta import Bicicleta
from dominio.comprovante.comprovante_viagem import ComprovanteViagem
from dominio.estacao.estacao import Estacao
from dominio.locacao.locacao import Locacao
from dominio.pacote.pacote_minutos import PacoteMinutos
from dominio.pagamento.cartao import Cartao
from dominio.pagamento.pagamento import Pagamento
from dominio.usuario.usuario import Usuario

# Nomes antigos
UsuarioORM = Usuario
EstacaoORM = Estacao
BicicletaORM = Bicicleta
LocacaoORM = Locacao
PacoteMinutosORM = PacoteMinutos
PagamentoORM = Pagamento
CartaoORM = Cartao
ReporteAvariaORM = ReporteAvaria
ComprovanteORM = ComprovanteViagem
EventoAuditoriaORM = EventoAuditoria

__all__ = [
    "Usuario", "Estacao", "Bicicleta", "Locacao", "PacoteMinutos", "Pagamento",
    "Cartao", "ReporteAvaria", "ComprovanteViagem", "EventoAuditoria",
    "UsuarioORM", "EstacaoORM", "BicicletaORM", "LocacaoORM", "PacoteMinutosORM",
    "PagamentoORM", "CartaoORM", "ReporteAvariaORM", "ComprovanteORM",
    "EventoAuditoriaORM",
]
