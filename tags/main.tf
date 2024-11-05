provider "aws" {
  region = "us-east-1"
}

# List of security group ARNs to tag
variable "security_group_arns" {
  description = "List of security group ARNs to tag"
  type        = list(string)
  default     = [
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0",
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abcdef1234567890"
  ]
}

# Define the new tags to apply
variable "new_tags" {
  description = "Tags to apply to the security groups"
  type        = map(string)
  default     = {
    Environment = "production"
    Project     = "network"
    Owner       = "team-name"
  }
}

# Fetch each security group by ARN
data "aws_security_group" "selected_security_groups" {
  for_each = toset(var.security_group_arns)
  arn      = each.value
}

# Use null_resource to apply tags using the AWS CLI
resource "null_resource" "tag_security_groups" {
  for_each = data.aws_security_group.selected_security_groups

  provisioner "local-exec" {
    command = <<EOT
      aws ec2 create-tags --resources ${each.value.id} --tags $(for k in "${!var.new_tags[@]}"; do echo Key=$k,Value=${var.new_tags[$k]}; done | tr '\n' ' ')
    EOT
  }

  depends_on = [data.aws_security_group.selected_security_groups]
}
