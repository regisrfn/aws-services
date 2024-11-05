provider "aws" {
  region = "us-east-1"
}

variable "security_group_arns" {
  description = "List of security group ARNs to tag"
  type        = list(string)
  default     = [
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0",
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abcdef1234567890"
  ]
}

variable "new_tags" {
  description = "Tags to apply to the security groups"
  type        = map(string)
  default     = {
    environment = "production"
    project     = "network"
    owner       = "team-name"
  }
}

# Fetch each security group by ARN
data "aws_security_group" "selected_security_groups" {
  for_each = toset(var.security_group_arns)
  arn      = each.value
}

# Use null_resource to apply tags using AWS CLI with properly formatted lowercase keys
resource "null_resource" "tag_security_groups" {
  for_each = data.aws_security_group.selected_security_groups

  provisioner "local-exec" {
    command = <<EOT
      aws ec2 create-tags --resources ${each.value.id} --tags '[
        ${join(",", [for k, v in var.new_tags : "{\"key\": \"${k}\", \"value\": \"${v}\"}"])}
      ]'
    EOT
  }

  depends_on = [data.aws_security_group.selected_security_groups]
}
