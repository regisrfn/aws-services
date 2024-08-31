import boto3
import time
from datetime import datetime, timezone
import pytest
import os

class S3FileProcessIntegrationTest:
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name='us-west-2')
        self.bucket_name = 'your-bucket-name'
        self.process_folder = 'process/'
        self.processed_folder = 'processed/'
        self.local_file_path = 'path/to/your/local/20240820_test.txt'
        self.file_name = os.path.basename(self.local_file_path)
        self.file_path = self.process_folder + self.file_name

    @pytest.fixture(scope='function', autouse=True)
    def setup_and_teardown(self):
        # Ensure the bucket is ready before starting the test
        yield

    def upload_file_to_s3(self):
        with open(self.local_file_path, 'rb') as file_data:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=self.file_path, Body=file_data)

    def list_s3_files_with_suffix(self, prefix, suffix):
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        files_with_suffix = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith(suffix)]
        return files_with_suffix

    def get_file_last_modified(self, key):
        response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
        return response['LastModified']

    def download_file_from_s3(self, key):
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read().decode('utf-8')

    def test_s3_file_processing(self):
        # Record the start time of the test
        test_start_time = datetime.now(timezone.utc)

        # Upload the local file to the "process/" folder
        self.upload_file_to_s3()

        # Wait for some time to allow the file processing to take place
        time.sleep(30)  # wait for 30 seconds

        # List the files in the process/ folder with a specific suffix (.txt)
        process_folder_files = self.list_s3_files_with_suffix(self.process_folder, '.txt')
        assert len(process_folder_files) == 0, "Process folder should be empty after processing"

        # List the files in the processed/ folder with a specific suffix (.txt)
        processed_folder_files = self.list_s3_files_with_suffix(self.processed_folder, '.txt')
        assert len(processed_folder_files) > 0, "Processed folder should contain the file"

        # Ensure the file was moved and check its last modified date
        moved_file = self.processed_folder + self.file_name
        assert moved_file in processed_folder_files, "The file should have been moved to the processed/ folder"

        last_modified = self.get_file_last_modified(moved_file)
        assert last_modified > test_start_time, "File's last modified date should be after the test start time"

        # Download the file and check if it has 10 lines
        downloaded_content = self.download_file_from_s3(moved_file)
        assert downloaded_content.count('\n') == 10, "The file should have exactly 10 lines"

