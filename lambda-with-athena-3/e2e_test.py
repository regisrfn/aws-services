import unittest
import boto3
import json
import time

class TestStepFunctionsIntegration(unittest.TestCase):
    def setUp(self):
        self.client = boto3.client('stepfunctions', region_name='us-east-1')  # Adjust region
        self.state_machine_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:YourStateMachine"  # Replace with your ARN

    def test_step_function_execution(self):
        # Arrange
        input_data = json.dumps({"key": "value"})  # Replace with your input data

        # Act
        # Start the Step Function execution
        response = self.client.start_execution(
            stateMachineArn=self.state_machine_arn,
            input=input_data
        )
        execution_arn = response['executionArn']

        # Wait for the execution to complete (polling)
        while True:
            status_response = self.client.describe_execution(
                executionArn=execution_arn
            )
            status = status_response['status']
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                break
            time.sleep(2)  # Avoid excessive polling

        # Assert
        self.assertEqual(status, "SUCCEEDED")  # Check if the Step Function succeeded
        self.assertIn("executionArn", response)  # Ensure the execution ARN is returned
        print(f"Execution {execution_arn} completed with status: {status}")

if __name__ == "__main__":
    unittest.main()
