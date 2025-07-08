# main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-east-1"  # ajuste para a sua região
}

# 1) Cria o tópico SNS
resource "aws_sns_topic" "meu_topico" {
  name = "meu-topico"
}

# 2) Cria duas filas SQS
resource "aws_sqs_queue" "fila1" {
  name                       = "fila1"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 1209600
}

resource "aws_sqs_queue" "fila2" {
  name                       = "fila2"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 1209600
}

# 3) Dados das filas para obter ARN
data "aws_sqs_queue" "fila1_info" {
  queue_url = aws_sqs_queue.fila1.id
}

data "aws_sqs_queue" "fila2_info" {
  queue_url = aws_sqs_queue.fila2.id
}

# 4) Política que permite ao SNS publicar em cada fila
resource "aws_sqs_queue_policy" "fila1_policy" {
  queue_url = data.aws_sqs_queue.fila1_info.url

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Sid       = "Allow-SNS-SendMessage"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = data.aws_sqs_queue.fila1_info.arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_sns_topic.meu_topico.arn
        }
      }
    }]
  })
}

resource "aws_sqs_queue_policy" "fila2_policy" {
  queue_url = data.aws_sqs_queue.fila2_info.url

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Sid       = "Allow-SNS-SendMessage"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = data.aws_sqs_queue.fila2_info.arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_sns_topic.meu_topico.arn
        }
      }
    }]
  })
}

# 5) Subscriptions: inscreve cada fila no tópico SNS
resource "aws_sns_topic_subscription" "sub_fila1" {
  topic_arn = aws_sns_topic.meu_topico.arn
  protocol  = "sqs"
  endpoint  = data.aws_sqs_queue.fila1_info.arn

  # garante que a policy já esteja aplicada
  depends_on = [aws_sqs_queue_policy.fila1_policy]
}

resource "aws_sns_topic_subscription" "sub_fila2" {
  topic_arn = aws_sns_topic.meu_topico.arn
  protocol  = "sqs"
  endpoint  = data.aws_sqs_queue.fila2_info.arn

  depends_on = [aws_sqs_queue_policy.fila2_policy]
}
