import boto3


def assume_role(role_arn, session_name):
    sts_client = boto3.client('sts')
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )

    credentials = response['Credentials']
    return {
        'aws_access_key_id': credentials['AccessKeyId'],
        'aws_secret_access_key': credentials['SecretAccessKey'],
        'aws_session_token': credentials['SessionToken']
    }

def get_secret(secret_name, region_name, role_arn, session_name):
    assumed_role_credentials = assume_role(role_arn, session_name)

    # Create a Secrets Manager client
    secrets_manager = boto3.client(
        'secretsmanager',
        region_name=region_name,
        aws_access_key_id=assumed_role_credentials['aws_access_key_id'],
        aws_secret_access_key=assumed_role_credentials['aws_secret_access_key'],
        aws_session_token=assumed_role_credentials['aws_session_token']
    )

    # Retrieve the secret value
    get_secret_value_response = secrets_manager.get_secret_value(SecretId=secret_name)

    # Extract and print the secret value
    secret_value = get_secret_value_response['SecretString']
    print(secret_value)

# Example usage
get_secret('your-secret-name', 'your-region', 'arn:aws:iam::your-account-id:role/your-role', 'YourSessionName')
