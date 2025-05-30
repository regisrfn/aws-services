###############################################################################
# VARIABLES
###############################################################################
variable "region" {
  description = "Região AWS"
  type        = string
  default     = "sa-east-1"
}

variable "cluster_name" {
  description = "Nome do ECS Cluster já existente"
  type        = string
}

variable "service_name" {
  description = "Nome do serviço ECS que será criado"
  type        = string
}

variable "image" {
  description = "URI da imagem Docker (ECR ou outro registry)"
  type        = string
}

variable "container_port" {
  description = "Porta em que o container escuta"
  type        = number
  default     = 3000
}

variable "desired_count" {
  description = "Número de instâncias do serviço"
  type        = number
  default     = 2
}

variable "vpc_id" {
  description = "ID da VPC onde o NLB e ECS irão rodar"
  type        = string
}

variable "subnet_ids" {
  description = "Lista de subnets públicas para o NLB"
  type        = list(string)
}

###############################################################################
# PROVIDER
###############################################################################
provider "aws" {
  region = var.region
}

###############################################################################
# DATA SOURCES
###############################################################################
data "aws_ecs_cluster" "existing" {
  cluster_name = var.cluster_name
}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "ecs_task_inline" {
  statement {
    sid     = "AllowS3ReadOnly"
    effect  = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
    ]
    resources = ["*"]
  }
}

###############################################################################
# SECURITY GROUP (apenas para as Tasks)
###############################################################################
resource "aws_security_group" "ecs_sg" {
  name        = "${var.service_name}-ecs-sg"
  description = "Allow traffic to container port"
  vpc_id      = data.aws_vpc.selected.id

  # Agora aceita direto de internet (ou use um CIDR mais restrito)
  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
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

###############################################################################
# NETWORK LOAD BALANCER
###############################################################################
resource "aws_lb" "app" {
  name               = "${var.service_name}-nlb"
  internal           = false
  load_balancer_type = "network"
  subnets            = var.subnet_ids
}

resource "aws_lb_target_group" "app_tg" {
  name        = "${var.service_name}-tg"
  port        = var.container_port
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.selected.id

  health_check {
    protocol            = "TCP"
    port                = "${var.container_port}"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "tcp" {
  load_balancer_arn = aws_lb.app.arn
  port              = var.container_port
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }
}

###############################################################################
# IAM ROLES & POLICIES
###############################################################################
resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "${var.service_name}-exec-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "exec_attach" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.service_name}-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "ecs_task_inline_policy" {
  name   = "${var.service_name}-task-inline-policy"
  role   = aws_iam_role.ecs_task_role.id
  policy = data.aws_iam_policy_document.ecs_task_inline.json
}

###############################################################################
# ECS TASK DEFINITION
###############################################################################
resource "aws_ecs_task_definition" "app" {
  family                   = var.service_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = var.service_name
      image = var.image
      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]
      essential = true
    }
  ])
}

###############################################################################
# ECS SERVICE
###############################################################################
resource "aws_ecs_service" "app" {
  name            = var.service_name
  cluster         = data.aws_ecs_cluster.existing.id
  launch_type     = "FARGATE"
  desired_count   = var.desired_count
  task_definition = aws_ecs_task_definition.app.arn

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false    # recommended para tasks ficarem só acessíveis via NLB
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app_tg.arn
    container_name   = var.service_name
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.tcp]
}

###############################################################################
# OUTPUTS
###############################################################################
output "nlb_dns_name" {
  description = "DNS público do Network Load Balancer"
  value       = aws_lb.app.dns_name
}
