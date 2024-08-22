provider "aws" {
  region = "us-west-2"
}

# Reference the existing secret from Secrets Manager
data "aws_secretsmanager_secret" "existing_secret" {
  name = "your-secret-name"  # Replace with your actual secret name
}

data "aws_secretsmanager_secret_version" "existing_secret_version" {
  secret_id = data.aws_secretsmanager_secret.existing_secret.id
}

# Create a compute environment for AWS Batch
resource "aws_batch_compute_environment" "example" {
  compute_environment_name = "example-environment"
  type                     = "MANAGED"

  compute_resources {
    instance_role      = "ecsInstanceRole"
    instance_type      = ["m5.large"]
    max_vcpus          = 16
    min_vcpus          = 0
    desired_vcpus      = 2
    subnets            = ["subnet-12345678"]
    security_group_ids = ["sg-12345678"]
    type               = "EC2"
  }
}

# Create a job definition for AWS Batch, referencing the secret values as environment variables
resource "aws_batch_job_definition" "example" {
  name = "example-job"
  type = "container"

  container_properties = jsonencode({
    image       = "your-docker-image"
    vcpus       = 2
    memory      = 4096
    environment = [
      {
        name  = "MY_ENV_VAR"
        value = "some-static-value"
      },
      {
        name  = "SECRET_USERNAME"
        value = jsondecode(data.aws_secretsmanager_secret_version.existing_secret_version.secret_string)["USERNAME"]
      },
      {
        name  = "SECRET_PASSWORD"
        value = jsondecode(data.aws_secretsmanager_secret_version.existing_secret_version.secret_string)["PASSWORD"]
      }
    ],
    jobRoleArn = "arn:aws:iam::account-id:role/ecsTaskExecutionRole",
  })
}

# Create a job queue for AWS Batch
resource "aws_batch_job_queue" "example" {
  name                 = "example-queue"
  state                = "ENABLED"
  priority             = 1
  compute_environments = [aws_batch_compute_environment.example.name]
}
