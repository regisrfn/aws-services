provider "aws" {
  region = "us-east-1"  # ajuste para sua região
}

# 1) IAM Role para o AWS Batch Service
resource "aws_iam_role" "batch_service_role" {
  name = "aws-batch-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "batch.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role_attach" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# 2) IAM Role para execução de Tasks ECS/Fargate
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# 3) Compute Environment
resource "aws_batch_compute_environment" "batch_ce" {
  compute_environment_name = "batch-ce"
  type                     = "MANAGED"
  service_role             = aws_iam_role.batch_service_role.arn

  compute_resources {
    type               = "FARGATE"
    max_vcpus          = 256
    subnets            = ["subnet-01234567","subnet-89abcdef"]  # seus subnets
    security_group_ids = ["sg-01234567"]                      # seu SG
  }
}

# 4) Job Queue
resource "aws_batch_job_queue" "batch_queue" {
  name     = "batch-queue"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.batch_ce.arn
  }
}

# 5) Job Definition com múltiplos containers via ecs_properties
resource "aws_batch_job_definition" "batch_job" {
  name                  = "batch-job-definition"
  type                  = "container"
  platform_capabilities = ["FARGATE"]
  execution_role_arn    = aws_iam_role.ecs_task_execution_role.arn

  # define múltiplos containers (app + datadog-apm + log-router)
  ecs_properties = jsonencode({
    taskProperties = [
      {
        containers = [
          {
            name  = "app-container"
            image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:latest"
            essential = true
            resourceRequirements = [
              { type = "VCPU",  value = "2"    },
              { type = "MEMORY", value = "4096" }
            ]
            command = ["./start.sh"]
          },
          {
            name  = "datadog-apm"
            image = "public.ecr.aws/datadog/agent:latest"
            essential   = false
            environment = [
              { name = "DD_APM_ENABLED",          value = "true"  },
              { name = "DD_APM_NON_LOCAL_TRAFFIC",value = "true"  }
            ]
            resourceRequirements = [
              { type = "VCPU",  value = "0.25" },
              { type = "MEMORY", value = "512"  }
            ]
          },
          {
            name  = "log-router"
            image = "public.ecr.aws/datadog/logs-router:latest"
            essential = false
            firelensConfiguration = {
              type    = "fluentbit"
              options = { "enable-ecs-log-metadata" = "true" }
            }
            resourceRequirements = [
              { type = "VCPU",  value = "0.25" },
              { type = "MEMORY", value = "256"  }
            ]
          }
        ]
      }
    ]
  })
}
