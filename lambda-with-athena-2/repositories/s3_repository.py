import boto3

class S3Repository:
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name

    def upload_file(self, file_path: str, key: str):
        self.s3.upload_file(file_path, self.bucket_name, key)
