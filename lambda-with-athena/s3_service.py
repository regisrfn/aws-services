
import boto3
from aws_lambda_powertools import Logger

logger = Logger(service="S3Service")

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = "ccsrelacionamentocliente-detalhamento-dev"
        self.s3_prefix = "athena_results/"

    def save_dataframe_to_s3(self, df, file_name: str):
        """
        Save a Pandas DataFrame to S3 as a JSON file.

        Args:
            df (pd.DataFrame): DataFrame to save.
            file_name (str): Name of the file to save in S3.
        """
        json_content = df.to_json(orient="records", indent=4, force_ascii=False)
        s3_path = f"{self.s3_prefix}{file_name}"

        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_path,
            Body=json_content,
            ContentType="application/json"
        )
        logger.info(f"JSON file saved to S3 at s3://{self.s3_bucket}/{s3_path}")
        return s3_path
