provider "aws" {
  region = "us-east-1"
}

# List of security group ARNs to track changes
variable "security_group_arns" {
  description = "List of security group ARNs to tag"
  type        = list(string)
  default     = [
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0",
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abcdef1234567890"
  ]
}

# Map of security group ARNs to their respective repo_id values
variable "security_group_repo_ids" {
  description = "Map of security group ARNs to repo_id values"
  type        = map(string)
  default     = {
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0" = "123"
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abcdef1234567890" = "456"
  }
}

# Use null_resource to apply tags using AWS CLI
resource "null_resource" "tag_security_groups" {
  for_each = toset(var.security_group_arns)

  provisioner "local-exec" {
    # Inline extraction of security group ID and application of the repo_id tag from map
    command = <<EOT
      aws ec2 create-tags --resources $(echo ${each.key} | awk -F'/' '{print $NF}') --tags '[
        {"Key": "repo_id", "Value": "${var.security_group_repo_ids[each.key]}"}
      ]' || echo "Failed to tag security group ${each.key}, continuing with other groups."
    EOT
  }
}
