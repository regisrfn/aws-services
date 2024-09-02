provider "aws" {
  region = "us-west-2"
}

# Define the SNS topic
resource "aws_sns_topic" "batch_failure_topic" {
  name = "batch-failure-topic"
}

# Retrieve current AWS account ID and region
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# Create the IAM policy document for the SNS topic
data "aws_iam_policy_document" "sns_topic_policy" {
  statement {
    effect = "Allow"

    actions = [
      "SNS:Publish",
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    resources = [
      aws_sns_topic.batch_failure_topic.arn,
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"

      values = [
        "arn:aws:events:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:rule/batch-job-failure-rule",
      ]
    }
  }
}

# Attach the policy to the SNS topic
resource "aws_sns_topic_policy" "batch_failure_topic_policy" {
  arn    = aws_sns_topic.batch_failure_topic.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

# Define the EventBridge rule to monitor failed jobs for a specific job queue
resource "aws_cloudwatch_event_rule" "batch_job_failure_rule" {
  name        = "batch-job-failure-rule"
  description = "Capture AWS Batch job failure events for a specific queue"
  event_pattern = jsonencode({
    "source": ["aws.batch"],
    "detail-type": ["Batch Job State Change"],
    "detail": {
      "status": ["FAILED"],
      "jobQueue": ["your-job-queue-name"]  # Replace with your specific job queue name
    }
  })
}

# EventBridge target to send events to the SNS topic
resource "aws_cloudwatch_event_target" "send_to_sns" {
  rule = aws_cloudwatch_event_rule.batch_job_failure_rule.name
  arn  = aws_sns_topic.batch_failure_topic.arn

  input_transformer {
    input_paths = {
      jobName = "$.detail.jobName"
      jobId   = "$.detail.jobId"
      queue   = "$.detail.jobQueue"
    }

    input_template = jsonencode({
      data = {
        message = "Job <jobName> with ID <jobId> in queue <queue> has failed."
      }
    })
  }
}
