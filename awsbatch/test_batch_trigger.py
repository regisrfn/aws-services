import boto3
import time
from datetime import datetime, timezone
import pytest
import os

s3_client = boto3.client('s3', region_name='us-west-2')

bucket_name = 'your-bucket-name'
process_folder = 'process/'
processed_folder = 'processed/'
local_file_path = 'path/to/your/local/20240820_test.txt'  # Path to your local file
file_name = os.path.basename(local_file_path)  # Extracts the file name from the local file path
file_path = process_folder + file_name

@pytest.fixture(scope='function')
def setup_and_teardown():
    # No deletion, just setup before the test starts
    yield

def upload_file_to_s3(local_file, key):
    with open(local_file, 'rb') as file_data:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=file_data)

def list_s3_files_with_suffix(prefix, suffix):
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    files_with_suffix = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith(suffix)]
    return files_with_suffix

def get_file_last_modified(key):
    response = s3_client.head_object(Bucket=bucket_name, Key=key)
    return response['LastModified']

def test_s3_file_processing():
    # Record the start time of the test
    test_start_time = datetime.now(timezone.utc)

    # Upload the local file to the "process/" folder
    upload_file_to_s3(local_file_path, file_path)

    # Wait for some time to allow the file processing to take place
    time.sleep(30)  # wait for 30 seconds

    # List the files in the process/ folder with a specific suffix (.txt)
    process_folder_files = list_s3_files_with_suffix(process_folder, '.txt')
    assert len(process_folder_files) == 0, "Process folder should be empty after processing"

    # List the files in the processed/ folder with a specific suffix (.txt)
    processed_folder_files = list_s3_files_with_suffix(processed_folder, '.txt')
    assert len(processed_folder_files) > 0, "Processed folder should contain the file"

    # Ensure the file was moved and check its last modified date
    moved_file = processed_folder + file_name
    assert moved_file in processed_folder_files, "The file should have been moved to the processed/ folder"

    last_modified = get_file_last_modified(moved_file)
    assert last_modified > test_start_time, "File's last modified date should be after the test start time"

    # Download the file and check if it has 10 lines
    response = s3_client.get_object(Bucket=bucket_name, Key=moved_file)
    downloaded_content = response['Body'].read().decode('utf-8')
    assert downloaded_content.count('\n') == 10, "The file should have exactly 10 lines"
