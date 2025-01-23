import json
import os
import uuid
import tempfile
from pydantic import BaseModel, ValidationError

class PayloadModel(BaseModel):
    tipo_arquivo: str
    numero_documento: str
    data_inicio: str
    data_fim: str
    cnpj_base_participante: str
    agencia: str
    conta: str
    tipo_pessoa: str

class DataService:
    def convert_to_json(self, df) -> str:
        return df.to_json(orient='records', indent=4)

    def save_to_temp(self, json_data: str) -> str:
        temp_file_path = os.path.join(tempfile.gettempdir(), f"temp_result_{uuid.uuid4().hex}.json")
        with open(temp_file_path, 'w') as temp_file:
            temp_file.write(json_data)
        return temp_file_path

    def save(self, json_data: str, s3_repo=None, key: str = None, file_path: str = None):
        temp_file_path = self.save_to_temp(json_data)
        try:
            if file_path:
                os.rename(temp_file_path, file_path)
                print(f"Arquivo JSON salvo localmente em: {file_path}")
            elif s3_repo and key:
                s3_repo.upload_file(temp_file_path, key)
                print(f"Arquivo JSON salvo no S3 com a chave: {key}")
            else:
                raise ValueError("Você deve fornecer um file_path ou um s3_repo com key para salvar os dados.")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def validate_payload(self, payload: dict) -> PayloadModel:
        try:
            return PayloadModel(**payload)
        except ValidationError as e:
            raise ValueError(f"Erro de validação do payload: {e}")
