from datetime import datetime
from pydantic import BaseModel
from servicos_tecnicos.banco_de_dados.enums import StatusAvaria


class AvariaPublic(BaseModel):
    id: int
    descricao: str
    data_hora: datetime
    usuario_email: str
    bicicleta_id: int
    status: StatusAvaria