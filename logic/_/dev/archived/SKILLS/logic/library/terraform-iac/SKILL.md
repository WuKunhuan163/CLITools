---
name: terraform-iac
description: Terraform Infrastructure as Code patterns. Use when working with terraform iac concepts or setting up related projects.
---

# Terraform Infrastructure as Code

## Core Principles

- **Declarative**: Define desired state; Terraform determines how to achieve it
- **State Management**: Remote state (S3, GCS) with locking for team collaboration
- **Modules**: Reusable infrastructure components
- **Plan Before Apply**: Always review `terraform plan` before applying

## Key Patterns

### Resource Definition
```hcl
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = "t3.micro"
  tags = { Name = "web-server", Environment = var.env }
}
```

### Module Usage
```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  cidr    = "10.0.0.0/16"
}
```

### Remote State
```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
  }
}
```

## Best Practices
- Use `terraform fmt` and `terraform validate` in CI
- Tag all resources for cost tracking
- Use workspaces or separate state files per environment
- Never store secrets in `.tf` files
