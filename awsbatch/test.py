import json
import pytest
from lambda_function import lambda_handler
from unittest.mock import patch

@pytest.fixture
def s3_event():
    """Fixture for a sample S3 event."""
    return {
        "Records": [
            {
                "awsRegion": "us-west-2",
                "s3": {
                    "bucket": {
                        "name": "example-bucket"
                    },
                    "object": {
                        "key": "test-file.txt",
                        "size": 1234
                    }
                }
            }
        ]
    }

@patch('lambda_function.submit_job')
def test_lambda_handler(mock_submit_job, s3_event):
    """Test the lambda_handler function."""
    mock_submit_job.return_value = {"jobId": "example-job-id"}

    response = lambda_handler(s3_event, {})
    
    mock_submit_job.assert_called_once_with(
        "us-west-2", "example-bucket", "test-file.txt", 1234
    )

    assert response == json.dumps({"resultado": "Job ID: example-job-id"})
