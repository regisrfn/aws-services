# main.tf
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

#######################
# Variáveis
#######################
variable "name_prefix" {
  type    = string
  default = "mycompany"
}
variable "bucket_name" {
  type    = string
  default = "mycompany-eventos-bronze"
}
variable "glue_database_name" {
  type    = string
  default = "db_eventos"
}
variable "glue_table_name" {
  type    = string
  default = "eventos_raw"
}
variable "s3_prefix" {
  type    = string
  default = "bronze/eventos"
}
variable "lambda_zip_path" {
  type    = string
  default = "build/lambda.zip"
}

#######################
# S3 Bucket
#######################
resource "aws_s3_bucket" "dados" {
  bucket        = var.bucket_name
  force_destroy = false

  versioning {
    enabled = true
  }
}

#######################
# SQS + DLQ
#######################
resource "aws_sqs_queue" "eventos_dlq" {
  name = "${var.name_prefix}-eventos-dlq"
}

resource "aws_sqs_queue" "eventos" {
  name                       = "${var.name_prefix}-eventos"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 1209600  # 14 dias

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.eventos_dlq.arn
    maxReceiveCount     = 5
  })
}

#######################
# Glue Database & Table
#######################
resource "aws_glue_catalog_database" "db" {
  name = var.glue_database_name
}

resource "aws_glue_catalog_table" "eventos" {
  database_name = aws_glue_catalog_database.db.name
  name          = var.glue_table_name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.dados.bucket}/${var.s3_prefix}/"
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
      name = "valor"
      type = "double"
    }
    columns {
      name = "ts_evento"
      type = "timestamp"
    }
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

#######################
# IAM Role & Policy
#######################
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
  name               = "${var.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [aws_sqs_queue.eventos.arn]
  }
  statement {
    actions = [
      "s3:PutObject",
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

resource "aws_iam_policy" "lambda_policy" {
  name   = "${var.name_prefix}-lambda-policy"
  policy = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

#######################
# Lambda Function
#######################
resource "aws_lambda_function" "consumer" {
  function_name = "${var.name_prefix}-consumer"
  role          = aws_iam_role.lambda_role.arn
  runtime       = "python3.12"
  handler       = "app.handler"
  timeout       = 60
  memory_size   = 512

  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      BUCKET_DADOS = aws_s3_bucket.dados.bucket
      GLUE_DB      = aws_glue_catalog_database.db.name
      GLUE_TABLE   = aws_glue_catalog_table.eventos.name
      S3_PREFIX    = var.s3_prefix
    }
  }

  # Protege contra picos excessivos
  reserved_concurrent_executions = 50
}

#######################
# SQS → Lambda Mapping
#######################
resource "aws_lambda_event_source_mapping" "sqs_mapping" {
  event_source_arn                   = aws_sqs_queue.eventos.arn
  function_name                      = aws_lambda_function.consumer.arn
  batch_size                         = 100
  maximum_batching_window_in_seconds = 30
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
}
