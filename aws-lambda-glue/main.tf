terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

############################
# Variáveis (inline simples)
############################
locals {
  name_prefix         = "eventos"
  bucket_name         = "meu-bucket-eventos-datalake"   # deve ser único global
  glue_database_name  = "db_eventos"
  glue_table_name     = "eventos_bronze"
  s3_prefix           = "bronze/eventos"
  lambda_zip_path     = "build/lambda.zip"
  lambda_reserved_concurrency = 12         # Ajuste conforme capacidade alvo
  lambda_timeout_seconds       = 90        # Com batch_size=300 processamento deve ser curto
  sqs_visibility_timeout       = 180       # ~2x timeout lambda
  batch_size                   = 300
  batching_window_seconds      = 300       # 5 min
}

############################
# S3 Bucket
############################
resource "aws_s3_bucket" "dados" {
  bucket        = local.bucket_name
  force_destroy = false

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_s3_bucket_versioning" "dados" {
  bucket = aws_s3_bucket.dados.id
  versioning_configuration {
    status = "Enabled"
  }
}

# (Opcional: encryption, lifecycle for older partitions)
resource "aws_s3_bucket_server_side_encryption_configuration" "enc" {
  bucket = aws_s3_bucket.dados.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

############################
# SNS Topic
############################
resource "aws_sns_topic" "eventos" {
  name = "${local.name_prefix}-topic"
}

############################
# SQS (principal + DLQ)
############################
resource "aws_sqs_queue" "dlq" {
  name = "${local.name_prefix}-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "main" {
  name                       = "${local.name_prefix}-queue"
  visibility_timeout_seconds = local.sqs_visibility_timeout
  message_retention_seconds  = 604800  # 7 dias
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}

# Permitir SNS publicar na SQS
data "aws_iam_policy_document" "sqs_policy" {
  statement {
    sid = "Allow-SNS-SendMessage"
    actions = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.main.arn]
    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_sns_topic.eventos.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "main_policy" {
  queue_url = aws_sqs_queue.main.id
  policy    = data.aws_iam_policy_document.sqs_policy.json
}

############################
# SNS Subscription -> SQS
############################
resource "aws_sns_topic_subscription" "sns_to_sqs" {
  topic_arn = aws_sns_topic.eventos.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.main.arn
  # (Opcional) filter_policy se quiser filtrar tipos.
  # filter_policy = jsonencode({ eventType = ["pedido_criado"] })
}

############################
# Glue Database & Table
############################
resource "aws_glue_catalog_database" "db" {
  name = local.glue_database_name
}

# Tabela Bronze (particionada dia/hora)
resource "aws_glue_catalog_table" "table" {
  name          = local.glue_table_name
  database_name = aws_glue_catalog_database.db.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.dados.bucket}/${local.s3_prefix}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "id_evento"
      type = "string"
    }
    columns {
      name = "tipo"
      type = "string"
    }
    columns {
      name = "ts_evento"
      type = "timestamp"
    }
    # (Adicionar mais colunas de payload se quiser)
  }

  partition_keys {
    name = "anomesdia"
    type = "string"
  }
  partition_keys {
    name = "hh"
    type = "string"
  }
}

############################
# IAM Roles / Policies
############################

# Lambda Assume
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [aws_sqs_queue.main.arn]
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.dados.arn,
      "${aws_s3_bucket.dados.arn}/*"
    ]
  }

  statement {
    actions = [
      "glue:GetTable",
      "glue:BatchCreatePartition"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_inline" {
  name   = "${local.name_prefix}-lambda-policy"
  policy = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_inline.arn
}

############################
# Lambda Function
############################

# (Se usar layer para pyarrow, criar aws_lambda_layer_version e referenciar)
# resource "aws_lambda_layer_version" "pyarrow_layer" { ... }

resource "aws_lambda_function" "consumer" {
  function_name = "${local.name_prefix}-consumer"
  runtime       = "python3.12"
  handler       = "app.handler"
  role          = aws_iam_role.lambda_role.arn
  filename      = local.lambda_zip_path
  source_code_hash = filebase64sha256(local.lambda_zip_path)
  timeout       = local.lambda_timeout_seconds
  memory_size   = 512
  reserved_concurrent_executions = local.lambda_reserved_concurrency

  environment {
    variables = {
      BUCKET_DADOS = aws_s3_bucket.dados.bucket
      GLUE_DB      = aws_glue_catalog_database.db.name
      GLUE_TABLE   = aws_glue_catalog_table.table.name
      S3_PREFIX    = local.s3_prefix
      REGISTER_PARTITIONS = "true"
      # Para tuning:
      LOG_LEVEL    = "INFO"
    }
  }

  # layers = [aws_lambda_layer_version.pyarrow_layer.arn] # se usar layer
}

############################
# Event Source Mapping SQS -> Lambda
############################
resource "aws_lambda_event_source_mapping" "sqs_mapping" {
  event_source_arn                   = aws_sqs_queue.main.arn
  function_name                      = aws_lambda_function.consumer.arn
  batch_size                         = local.batch_size
  maximum_batching_window_in_seconds = local.batching_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
}

############################
# Outputs
############################
output "sns_topic_arn" {
  value = aws_sns_topic.eventos.arn
}

output "sqs_queue_url" {
  value = aws_sqs_queue.main.id
}

output "lambda_name" {
  value = aws_lambda_function.consumer.function_name
}
