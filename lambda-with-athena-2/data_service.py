import json
import os
import uuid
import tempfile

class DataService:
    def convert_to_json(self, df) -> str:
        """Converte um DataFrame para uma string JSON."""
        return df.to_json(orient='records', indent=4)

    def save(self, json_data: str, s3_repo=None, key: str = None, file_path: str = None):
        """
        Salva os dados JSON no local especificado.

        Argumentos:
        - json_data (str): Dados JSON a serem salvos.
        - s3_repo (S3Repository): Repositório S3, se desejar fazer o upload.
        - key (str): Caminho no S3 (requer s3_repo).
        - file_path (str): Caminho no sistema de arquivos local.

        """
        if not file_path and not (s3_repo and key):
            raise ValueError("Você deve fornecer um file_path ou um s3_repo com key para salvar os dados.")

        # Gerar caminho temporário único
        temp_file_path = os.path.join(tempfile.gettempdir(), f"temp_result_{uuid.uuid4().hex}.json")

        try:
            # Salvar JSON no arquivo temporário
            with open(temp_file_path, 'w') as temp_file:
                temp_file.write(json_data)

            if file_path:
                # Salvar localmente
                os.rename(temp_file_path, file_path)
                print(f"Arquivo JSON salvo localmente em: {file_path}")
            elif s3_repo and key:
                # Upload para o S3
                s3_repo.upload_file(temp_file_path, key)
                print(f"Arquivo JSON salvo no S3 com a chave: {key}")
        finally:
            # Remover o arquivo temporário se ele ainda existir
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
