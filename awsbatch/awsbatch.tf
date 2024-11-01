provider "aws" {
  region = "us-west-2"
}

### 1. VPC and Networking Resources ###

# Create a VPC
resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"
}

# Create a Subnet
resource "aws_subnet" "my_subnet" {
  vpc_id     = aws_vpc.my_vpc.id
  cidr_block = "10.0.1.0/24"
}

# Create a Security Group
resource "aws_security_group" "my_security_group" {
  vpc_id = aws_vpc.my_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

### 2. ECS Cluster ###

resource "aws_ecs_cluster" "batch_ecs_cluster" {
  name = "my-batch-ecs-cluster"
}

### 3. AWS Batch Compute Environment with Fargate ###

resource "aws_batch_compute_environment" "my_compute_environment" {
  compute_environment_name = "my-fargate-compute-environment"
  type                     = "MANAGED"

  compute_resources {
    type               = "FARGATE"    # Use Fargate for serverless containers
    max_vcpus          = 10           # Maximum vCPUs for this environment
    subnets            = [aws_subnet.my_subnet.id]
    security_group_ids = [aws_security_group.my_security_group.id]
  }

  state        = "ENABLED"
  service_role = aws_iam_role.batch_service_role.arn
}

### 4. AWS Batch Job Queue ###

resource "aws_batch_job_queue" "my_job_queue" {
  name                = "my-fargate-job-queue"
  state               = "ENABLED"
  priority            = 1

  compute_environment_order {
    compute_environment = aws_batch_compute_environment.my_compute_environment.arn
    order               = 1
  }
}

### 5. AWS Batch Job Definition ###

resource "aws_batch_job_definition" "my_job_definition" {
  name        = "my-fargate-job-definition"
  type        = "container"

  container_properties = jsonencode({
    image     = "busybox"
    vcpus     = 1
    memory    = 512
    command   = ["echo", "Hello AWS Batch on Fargate!"]
    networkConfiguration = {
      assignPublicIp = "ENABLED"
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/aws/batch/job"
        "awslogs-region"        = "us-west-2"
        "awslogs-stream-prefix" = "fargate"
      }
    }
  })

  platform_capabilities = ["FARGATE"]  # Specify Fargate platform
}

### 6. IAM Roles ###

# IAM Role for Batch service
resource "aws_iam_role" "batch_service_role" {
  name = "batch-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "batch.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_policy" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

### 7. CloudWatch Log Group for Batch Jobs ###

resource "aws_cloudwatch_log_group" "batch_log_group" {
  name              = "/aws/batch/job"
  retention_in_days = 7
}

resource "null_resource" "tag_ecs_cluster" {
  provisioner "local-exec" {
    command = <<EOT
      # Define the search string for the cluster name
      search_string="example-compute-environment"

      # Retrieve the cluster ARN containing the search string
      cluster_arn=$(aws ecs list-clusters --query "clusterArns[?contains(@, '$search_string')]" --output text)

      # Check if a cluster was found, then apply tags
      if [ -n "$cluster_arn" ]; then
        aws ecs tag-resource --resource-arn $cluster_arn --tags Key=Environment,Value=production Key=Project,Value=batch-processing
        echo "Tagged ECS cluster: $cluster_arn"
      else
        echo "No matching ECS cluster found for search string: $search_string"
        exit 1
      fi
    EOT
  }
}

