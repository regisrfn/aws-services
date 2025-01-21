
import boto3
import json

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = "ccsrelacionamentocliente-detalhamento-dev"
        self.s3_prefix = "athena_results/"

    def save_results_to_s3(self, results: list, file_name: str):
        json_content = json.dumps(results, ensure_ascii=False, indent=4)

        s3_path = f"{self.s3_prefix}{file_name}"

        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_path,
            Body=json_content,
            ContentType="application/json"
        )

        print(f"Arquivo JSON salvo em: s3://{self.s3_bucket}/{s3_path}")
        return s3_path
