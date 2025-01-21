
from pydantic import BaseModel, ConfigDict
from typing import Literal

class QueryPayload(BaseModel):
    tipo_arquivo: Literal['json', 'csv']
    numero_documento: str
    data_inicio: str
    data_fim: str
    cnpj_base_participante: str
    agencia: str
    conta: str
    tipo_pessoa: Literal['fisica', 'juridica']

    model_config = ConfigDict(
        str_max_length=100,
        validate_assignment=True,
        use_enum_values=True
    )
