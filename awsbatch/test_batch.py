import os
import pytest
from moto import mock_batch
from BatchService import submit_job, parse_batch_job_name

@mock_batch
@patch.dict(os.environ, {
    "QUEUE_NAME": "example-queue",
    "QUEUE_DEFINITION_NAME": "example-job-definition"
})
def test_submit_job():
    """Test the submit_job function."""
    # Assuming boto3 client is properly configured with moto
    response = submit_job("us-west-2", "example-bucket", "test-file.txt", 1234)
    
    # Validate the mock response
    assert "jobName" in response

def test_parse_batch_job_name():
    """Test the parse_batch_job_name function."""
    file_name = "test-file.txt"
    job_name = parse_batch_job_name(file_name)

    assert job_name.startswith("job-")
    assert "test-file" in job_name
