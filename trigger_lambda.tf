provider "aws" {
  region = "us-west-2"
}

# Create a CloudWatch Log Group for EventBridge Logs
resource "aws_cloudwatch_log_group" "eventbridge_log_group" {
  name = "/aws/events/batch-job-failure-rule"
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

# Create the Lambda Function
resource "aws_lambda_function" "batch_failure_lambda" {
  filename         = "lambda_function_payload.zip"
  function_name    = "batch_failure_handler"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("lambda_function_payload.zip")

  environment {
    variables = {
      # Add any environment variables you need here
    }
  }
}

# EventBridge Rule for Batch Job Failures
resource "aws_cloudwatch_event_rule" "batch_job_failure_rule" {
  name        = "batch-job-failure-rule"
  description = "Capture AWS Batch job failure events and trigger Lambda"
  event_pattern = jsonencode({
    "source": ["aws.batch"],
    "detail-type": ["Batch Job State Change"],
    "detail": {
      "status": ["FAILED"]
    }
  })
}

# Attach the Lambda Function as a Target for the EventBridge Rule
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.batch_job_failure_rule.name
  arn       = aws_lambda_function.batch_failure_lambda.arn
}

# Grant EventBridge Permission to Invoke the Lambda Function
resource "aws_lambda_permission" "allow_eventbridge_invoke" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_failure_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.batch_job_failure_rule.arn
}

# Enable Logging for the EventBridge Rule
resource "aws_cloudwatch_event_target" "eventbridge_logging_target" {
  rule      = aws_cloudwatch_event_rule.batch_job_failure_rule.name
  arn       = aws_cloudwatch_log_group.eventbridge_log_group.arn
}

# Grant EventBridge Permission to Log to CloudWatch Logs
resource "aws_iam_role_policy_attachment" "eventbridge_logs_policy" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}
