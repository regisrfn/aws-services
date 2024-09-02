resource "aws_cloudwatch_event_rule" "batch_job_failure_rule" {
  name        = "batch-job-failure-rule"
  description = "Capture AWS Batch job failure events"
  event_pattern = jsonencode({
    "source": ["aws.batch"],
    "detail-type": ["Batch Job State Change"],
    "detail": {
      "status": ["FAILED"]
    }
  })
}

resource "aws_sns_topic" "batch_failure_topic" {
  name = "batch-failure-topic"
}


resource "aws_cloudwatch_event_target" "send_to_sns" {
  rule = aws_cloudwatch_event_rule.batch_job_failure_rule.name
  arn  = aws_sns_topic.batch_failure_topic.arn
}

resource "aws_sns_topic_policy" "batch_failure_topic_policy" {
  arn = aws_sns_topic.batch_failure_topic.arn

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = "*",
        Action = "SNS:Publish",
        Resource = aws_sns_topic.batch_failure_topic.arn,
        Condition = {
          ArnEquals = {
            "aws:SourceArn": aws_cloudwatch_event_rule.batch_job_failure_rule.arn
          }
        }
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "lambda_subscription" {
  topic_arn = aws_sns_topic.batch_failure_topic.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.job_failure_lambda.arn
}