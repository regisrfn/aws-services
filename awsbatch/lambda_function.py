import json
import boto3
import os

# Initialize clients
batch_client = boto3.client('batch')
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    # Parse the S3 event
    print("Received event: " + json.dumps(event, indent=2))

    # Loop through the records (there can be multiple records in the event)
    for record in event['Records']:
        # Get the bucket name and file key from the event
        bucket_name = record['s3']['bucket']['name']
        file_key = record['s3']['object']['key']
        file_size = record['s3']['object']['size']

        print(f"Bucket: {bucket_name}, File: {file_key}, Size: {file_size}")

        # Define job parameters
        job_name = f"process-{file_key.split('/')[-1]}"
        job_queue = os.environ['JOB_QUEUE']
        job_definition = os.environ['JOB_DEFINITION']

        # Parameters that will be passed to the AWS Batch job
        parameters = {
            'bucket_name': bucket_name,
            'file_key': file_key,
            'file_size': str(file_size)
        }

        # Submit the job to AWS Batch
        response = batch_client.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            parameters=parameters
        )

        print(f"Submitted Batch Job: {response['jobId']}")

    return {
        'statusCode': 200,
        'body': json.dumps('Job submitted successfully')
    }
