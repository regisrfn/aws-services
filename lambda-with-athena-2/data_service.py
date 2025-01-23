import json

class DataService:
    def convert_to_json(self, df) -> str:
        return df.to_json(orient='records', indent=4)

    def save_json_to_s3(self, json_data: str, s3_repo, key: str):
        file_path = '/tmp/result.json'
        with open(file_path, 'w') as file:
            file.write(json_data)
        s3_repo.upload_file(file_path, key)
        print(f"Arquivo salvo no S3 com a chave: {key}")
