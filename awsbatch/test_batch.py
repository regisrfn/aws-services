import pytest
from unittest.mock import patch, MagicMock
from src.service.BatchService import submit_job

@patch('src.service.BatchService.boto3.client')
def test_submit_job(mock_boto_client):
    # Arrange
    mock_batch = MagicMock()
    mock_boto_client.return_value = mock_batch
    
    # Mocking the submit_job function of the boto3 batch client
    mock_batch.submit_job.return_value = {
        'jobId': 'test_job_id',
        'jobName': 'test_job_name'
    }
    
    # Act
    response = submit_job(
        region='us-east-1',
        bucket_name='test_bucket',
        input_file_name='test_file.txt',
        input_file_size=12345
    )
    
    # Assert
    assert response['jobId'] == 'test_job_id'
    assert response['jobName'] == 'test_job_name'
    mock_batch.submit_job.assert_called_once_with(
        jobName='test_job_name',
        jobQueue='QUEUE_NAME',
        jobDefinition='QUEUE_DEFINITION_NAME',
        containerOverrides={
            'environment': [
                {'name': 'INPUT_BUCKET', 'value': 'test_bucket'},
                {'name': 'FILE_NAME', 'value': 'test_file.txt'},
                {'name': 'FILE_SIZE', 'value': '12345'},
                {'name': 'REGION', 'value': 'us-east-1'}
            ]
        }
    )

