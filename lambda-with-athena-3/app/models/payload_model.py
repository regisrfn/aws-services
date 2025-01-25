from pydantic import BaseModel, Field

class PayloadModel(BaseModel):
    tipo_arquivo: str = Field(..., description="Type of the file")
    numero_documento: str = Field(..., description="Document number")
    data_inicio: str = Field(..., regex=r"\d{4}-\d{2}-\d{2}", description="Start date in YYYY-MM-DD")
    data_fim: str = Field(..., regex=r"\d{4}-\d{2}-\d{2}", description="End date in YYYY-MM-DD")
    cnpj_base_participante: str = Field(..., description="CNPJ of the participant")
    agencia: str = Field(..., description="Bank branch")
    conta: str = Field(..., description="Account number")
    tipo_pessoa: str = Field(..., description="Person type (e.g., F for individual)")
