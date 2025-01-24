import json
from pydantic import BaseModel, ValidationError

class PayloadModel(BaseModel):
    tipo_arquivo: str
    numero_documento: str
    data_inicio: str
    data_fim: str = None
    cnpj_base_participante: str
    agencia: str
    conta: str
    tipo_pessoa: str

class DataService:
    def convert_to_json(self, df) -> str:
        return df.to_json(orient='records', indent=4)

    def save(self, json_data: str, s3_repo, key: str):
        temp_file_path = '/tmp/temp_result.json'
        with open(temp_file_path, 'w') as temp_file:
            temp_file.write(json_data)
        s3_repo.upload_file(temp_file_path, key)
