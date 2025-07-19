# AWS Deployment Guide

This guide covers deploying WOPS AI to AWS using your credentials.

## Prerequisites

1. **AWS Credentials**: You need AWS Access Key ID, Secret Access Key, and Session Token
2. **Docker**: Ensure Docker is installed and running
3. **Terraform**: Terraform should be installed (the script will check)
4. **Snowflake Access**: You'll need Snowflake connection details

## Quick Deployment

### Step 1: Set AWS Credentials

```bash
export AWS_ACCESS_KEY_ID="your_access_key_here"
export AWS_SECRET_ACCESS_KEY="your_secret_key_here"
export AWS_SESSION_TOKEN="your_session_token_here"  # if using temporary credentials
export AWS_REGION="us-west-2"
```

### Step 2: Configure Snowflake (Optional for initial deployment)

Create a `infrastructure/aws/terraform.tfvars` file:

```hcl
# AWS Configuration
aws_region = "us-west-2"
project_name = "wops-ai"
environment = "development"

# Snowflake Configuration
snowflake_account = "your-account"
snowflake_user = "your-username"
snowflake_warehouse = "your-warehouse"
snowflake_database = "your-database"
```

### Step 3: Deploy

```bash
./deploy.sh
```

This script will:
1. Build Docker images for backend and frontend
2. Create ECR repositories and push images
3. Deploy infrastructure using Terraform
4. Set up ECS services with load balancer

## What Gets Created

### AWS Resources:
- **VPC** with public/private subnets
- **ECS Cluster** running Fargate tasks
- **Application Load Balancer** with health checks
- **ECR Repositories** for Docker images
- **RDS PostgreSQL** instance (for production data)
- **DynamoDB Tables** for user management
- **S3 Bucket** for file storage
- **Secrets Manager** for API keys
- **CloudWatch** logs and monitoring

### Architecture:
```
Internet → ALB → ECS (Backend + Frontend) → RDS/DynamoDB
                                        → S3
                                        → Secrets Manager
```

## Environment Configuration

The deployment uses environment-based configuration:

- **Local**: SQLite + Console emails
- **Development**: PostgreSQL + SES emails
- **Production**: PostgreSQL + SES emails

## Post-Deployment Steps

### 1. Add API Keys to Secrets Manager

```bash
# OpenAI API Key
aws secretsmanager put-secret-value \
    --secret-id wops-ai-openai-key \
    --secret-string "your-openai-key"

# Anthropic API Key
aws secretsmanager put-secret-value \
    --secret-id wops-ai-anthropic-key \
    --secret-string "your-anthropic-key"

# Google API Key
aws secretsmanager put-secret-value \
    --secret-id wops-ai-google-key \
    --secret-string "your-google-key"
```

### 2. Configure Domain (Optional)

1. Create a Route 53 hosted zone
2. Get an SSL certificate from ACM
3. Update `terraform.tfvars` with domain and certificate ARN
4. Re-run deployment

### 3. Test the Deployment

```bash
# Get the ALB DNS name
terraform output alb_dns_name

# Test backend health
curl http://your-alb-dns/health

# Test frontend
curl http://your-alb-dns
```

## Monitoring and Logs

- **CloudWatch Logs**: Available for both backend and frontend
- **ECS Service Metrics**: CPU, memory, task count
- **ALB Metrics**: Request count, latency, errors

Access logs at:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups
```

## Scaling

The deployment is configured for:
- **Backend**: 2 tasks (can auto-scale based on CPU/memory)
- **Frontend**: 2 tasks (stateless, can scale easily)
- **RDS**: Single instance (can upgrade to Multi-AZ)

## Security Features

- **VPC**: Private subnets for ECS tasks
- **Security Groups**: Restrictive rules
- **IAM Roles**: Least privilege access
- **Secrets Manager**: Encrypted API key storage
- **Email Domain Restriction**: Only ClipboardHealth emails

## Cost Optimization

- **Fargate**: Pay only for running tasks
- **RDS**: t3.micro for development
- **S3**: Standard storage class
- **CloudWatch**: 5GB free tier

Estimated monthly cost: ~$50-100 for development environment

## Troubleshooting

### Common Issues:

1. **Docker Build Fails**:
   ```bash
   # Check if Docker is running
   docker info
   ```

2. **ECR Push Fails**:
   ```bash
   # Re-authenticate with ECR
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com
   ```

3. **ECS Tasks Fail**:
   ```bash
   # Check ECS service events
   aws ecs describe-services --cluster wops-ai-cluster --services wops-ai-backend
   ```

4. **Health Check Fails**:
   - Verify the `/health` endpoint works locally
   - Check CloudWatch logs for errors

### Getting Help:

1. Check CloudWatch logs
2. Review ECS service events
3. Verify security group rules
4. Test endpoints individually

## Clean Up

To remove all AWS resources:

```bash
cd infrastructure/aws
terraform destroy
```

**Warning**: This will delete all data and resources permanently.

---

## Next Steps

1. **Set up monitoring alerts**
2. **Configure backup strategies**
3. **Implement CI/CD pipeline**
4. **Add custom domain and SSL**
5. **Set up staging environment**