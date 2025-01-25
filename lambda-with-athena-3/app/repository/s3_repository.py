import json
import boto3
from config import logger

s3_client = boto3.client("s3")

def save_to_s3(bucket: str, key: str, data: dict):
    try:
        logger.info(f"Saving JSON to S3: Bucket={bucket}, Key={key}")
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=4),
            ContentType="application/json",
        )
        logger.info("JSON successfully saved to S3.")
    except Exception as e:
        logger.exception(f"Failed to save to S3: {e}")
        raise
