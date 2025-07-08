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

# 3) Política que permite ao SNS publicar em cada fila
resource "aws_sqs_queue_policy" "fila1_policy" {
  queue_url = aws_sqs_queue.fila1.id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Sid       = "Allow-SNS-SendMessage"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.fila1.arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_sns_topic.meu_topico.arn
        }
      }
    }]
  })
}

resource "aws_sqs_queue_policy" "fila2_policy" {
  queue_url = aws_sqs_queue.fila2.id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Sid       = "Allow-SNS-SendMessage"
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.fila2.arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_sns_topic.meu_topico.arn
        }
      }
    }]
  })
}

# 4) Subscriptions: inscreve cada fila no tópico SNS
resource "aws_sns_topic_subscription" "sub_fila1" {
  topic_arn = aws_sns_topic.meu_topico.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.fila1.arn

  depends_on = [aws_sqs_queue_policy.fila1_policy]
}

resource "aws_sns_topic_subscription" "sub_fila2" {
  topic_arn = aws_sns_topic.meu_topico.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.fila2.arn

  depends_on = [aws_sqs_queue_policy.fila2_policy]
}
