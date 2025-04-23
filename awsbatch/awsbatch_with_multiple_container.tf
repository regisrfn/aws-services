provider "aws" {
  region = var.region
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "subnets" {
  description = "List of subnets for Fargate"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for Fargate"
  type        = list(string)
}

variable "main_image" {
  description = "Docker image for main container"
  type        = string
}

variable "main_vcpus" {
  description = "vCPU units for main container"
  type        = number
  default     = 1
}

variable "main_memory" {
  description = "Memory (MiB) for main container"
  type        = number
  default     = 2048
}

variable "dd_api_key" {
  description = "Datadog API key"
  type        = string
  sensitive   = true
}

variable "dd_site" {
  description = "Datadog site (e.g. datadoghq.com)"
  type        = string
  default     = "datadoghq.com"
}

variable "log_group_name" {
  description = "CloudWatch Logs group"
  type        = string
  default     = "/aws/batch/job"
}

# IAM Role for AWS Batch service
data "aws_iam_policy_document" "batch_service_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "batch_service_role" {
  name               = "batch-service-role"
  assume_role_policy = data.aws_iam_policy_document.batch_service_assume_role.json
}

resource "aws_iam_role_policy_attachment" "batch_service_role_attach" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# IAM Execution Role for ECS Fargate tasks
data "aws_iam_policy_document" "batch_execution_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "batch_execution_role" {
  name               = "batch-execution-role"
  assume_role_policy = data.aws_iam_policy_document.batch_execution_assume_role.json
}

resource "aws_iam_role_policy_attachment" "batch_execution_attach" {
  role       = aws_iam_role.batch_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role that the containers assume
data "aws_iam_policy_document" "batch_job_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "batch_job_role" {
  name               = "batch-job-role"
  assume_role_policy = data.aws_iam_policy_document.batch_job_assume_role.json
}

# AWS Batch Compute Environment
resource "aws_batch_compute_environment" "batch_ce" {
  compute_environment_name = "batch-compute-env"
  service_role             = aws_iam_role.batch_service_role.arn
  type                     = "MANAGED"

  compute_resources {
    type               = "FARGATE"
    max_vcpus          = 256
    subnets            = var.subnets
    security_group_ids = var.security_group_ids
  }
}

# AWS Batch Job Queue
resource "aws_batch_job_queue" "batch_jq" {
  name     = "batch-job-queue"
  priority = 1

  compute_environment_order {
    compute_environment = aws_batch_compute_environment.batch_ce.arn
    order               = 1
  }
}

# AWS Batch Job Definition with multiple containers
resource "aws_batch_job_definition" "batch_jd" {
  name                  = "batch-multi-container-job"
  type                  = "container"
  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    ecsProperties = {
      executionRoleArn = aws_iam_role.batch_execution_role.arn
      taskRoleArn      = aws_iam_role.batch_job_role.arn
      taskProperties   = [
        {
          containers = [
            {
              name      = "main"
              image     = var.main_image
              vcpus     = var.main_vcpus
              memory    = var.main_memory
              essential = true
              logConfiguration = {
                logDriver = "awslogs"
                options = {
                  awslogs-group         = var.log_group_name
                  awslogs-region        = var.region
                  awslogs-stream-prefix = "main"
                }
              }
            },
            {
              name      = "datadog-log"
              image     = "public.ecr.aws/datadog/agent:latest"
              essential = false
              logConfiguration = {
                logDriver = "awslogs"
                options = {
                  awslogs-group         = var.log_group_name
                  awslogs-region        = var.region
                  awslogs-stream-prefix = "dd-log"
                }
              }
              environment = [
                { name = "DD_API_KEY", value = var.dd_api_key },
                { name = "ECS_FARGATE", value = "true" },
                { name = "DD_SITE", value = var.dd_site },
              ]
            },
            {
              name      = "datadog-apm"
              image     = "public.ecr.aws/datadog/apm:latest"
              essential = false
              logConfiguration = {
                logDriver = "awslogs"
                options = {
                  awslogs-group         = var.log_group_name
                  awslogs-region        = var.region
                  awslogs-stream-prefix = "dd-apm"
                }
              }
              environment = [
                { name = "DD_API_KEY", value = var.dd_api_key },
                { name = "ECS_FARGATE", value = "true" },
                { name = "DD_SITE", value = var.dd_site },
              ]
            }
          ]
        }
      ]
    }
  })
}

output "job_definition_arn" {
  description = "ARN of the AWS Batch Job Definition"
  value       = aws_batch_job_definition.batch_jd.arn
}

output "execution_role_arn" {
  description = "ARN of the ECS Execution Role"
  value       = aws_iam_role.batch_execution_role.arn
}
