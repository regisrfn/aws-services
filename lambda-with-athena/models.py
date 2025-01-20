
from pydantic import BaseModel

class QueryPayload(BaseModel):
    tipo_arquivo: str
    numero_documento: str
    data_inicio: str
    data_fim: str
    cnpj_base_participante: str
    agencia: str
    conta: str
    tipo_pessoa: str

    class Config:
        schema_extra = {
            "example": {
                "tipo_arquivo": "example_type",
                "numero_documento": "123456789",
                "data_inicio": "2023-01-01",
                "data_fim": "2023-01-31",
                "cnpj_base_participante": "12345678000195",
                "agencia": "1234",
                "conta": "56789-0",
                "tipo_pessoa": "fisica"
            }
        }
