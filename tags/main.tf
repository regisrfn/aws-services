provider "aws" {
  region = "us-east-1"
}

# Map of security group ARNs to specific tag values
variable "security_group_tags" {
  description = "Map of security group ARNs to their respective repo_id tag values"
  type        = map(string)
  default     = {
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0" = "123"
    "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abcdef1234567890" = "456"
  }
}

# Define additional tags to apply to the security groups
variable "additional_tags" {
  description = "Additional tags to apply to the security groups"
  type        = map(string)
  default     = {
    Environment = "production"
    Project     = "network"
    Owner       = "team-name"
  }
}

# Use null_resource to apply tags using AWS CLI
resource "null_resource" "tag_security_groups" {
  for_each = var.security_group_tags

  provisioner "local-exec" {
    # Inline extraction of security group ID and application of tags with uppercase Key and Value
    command = <<EOT
      aws ec2 create-tags --resources $(echo ${each.key} | awk -F'/' '{print $NF}') --tags '[
        {"Key": "repo_id", "Value": "${each.value}"},
        ${join(",", [for k, v in var.additional_tags : "{\"Key\": \"${k}\", \"Value\": \"${v}\"}"])}
      ]' || echo "Failed to tag security group ${each.key}, continuing with other groups."
    EOT
  }
}
