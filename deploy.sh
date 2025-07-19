#!/bin/bash

# WOPS AI AWS Deployment Script
# This script deploys the WOPS AI application to AWS using your credentials

set -e

echo "🚀 WOPS AI AWS Deployment Script"
echo "=================================="

# Check if AWS credentials are provided
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ Error: AWS credentials not set"
    echo "Please set the following environment variables:"
    echo "export AWS_ACCESS_KEY_ID=your_access_key_here"
    echo "export AWS_SECRET_ACCESS_KEY=your_secret_key_here"
    echo "export AWS_SESSION_TOKEN=your_session_token_here  # if using temporary credentials"
    echo "export AWS_REGION=us-west-2"
    exit 1
fi

# Set default region if not provided
export AWS_REGION=${AWS_REGION:-us-west-2}

echo "✅ AWS Region: $AWS_REGION"
echo "✅ AWS Access Key ID: ${AWS_ACCESS_KEY_ID:0:10}..."

# Project configuration
PROJECT_NAME="wops-ai"
ENVIRONMENT="development"

echo "📋 Project: $PROJECT_NAME"
echo "📋 Environment: $ENVIRONMENT"

# Step 1: Build and push Docker images to ECR
echo ""
echo "🐳 Step 1: Building and pushing Docker images..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create ECR repositories if they don't exist
echo "📦 Creating ECR repositories..."
aws ecr describe-repositories --repository-names "$PROJECT_NAME-backend" --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name "$PROJECT_NAME-backend" --region $AWS_REGION

aws ecr describe-repositories --repository-names "$PROJECT_NAME-frontend" --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name "$PROJECT_NAME-frontend" --region $AWS_REGION

# Get ECR login token
echo "🔑 Getting ECR login token..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BACKEND_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-backend"
ECR_FRONTEND_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-frontend"

echo "📦 Backend ECR URI: $ECR_BACKEND_URI"
echo "📦 Frontend ECR URI: $ECR_FRONTEND_URI"

# Build and push backend
echo "🔨 Building backend Docker image..."
cd backend
docker build -t $ECR_BACKEND_URI:latest .
echo "📤 Pushing backend to ECR..."
docker push $ECR_BACKEND_URI:latest

# Build and push frontend
echo "🔨 Building frontend Docker image..."
cd ../frontend
docker build -t $ECR_FRONTEND_URI:latest .
echo "📤 Pushing frontend to ECR..."
docker push $ECR_FRONTEND_URI:latest

cd ..

# Step 2: Deploy infrastructure with Terraform
echo ""
echo "🏗️  Step 2: Deploying infrastructure with Terraform..."

cd infrastructure/aws

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Plan deployment
echo "📋 Planning Terraform deployment..."
terraform plan \
    -var="project_name=$PROJECT_NAME" \
    -var="environment=$ENVIRONMENT" \
    -var="aws_region=$AWS_REGION" \
    -var="backend_image_uri=$ECR_BACKEND_URI:latest" \
    -var="frontend_image_uri=$ECR_FRONTEND_URI:latest" \
    -out=tfplan

# Apply deployment
echo "🚀 Applying Terraform deployment..."
echo "This will create AWS resources. Continue? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    terraform apply tfplan
    
    # Get outputs
    echo ""
    echo "✅ Deployment completed!"
    echo "📝 Getting deployment information..."
    
    ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "Not available")
    BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null || echo "Not available")
    FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "Not available")
    
    echo ""
    echo "🌐 Application URLs:"
    echo "   Load Balancer: http://$ALB_DNS"
    echo "   Backend API: $BACKEND_URL"
    echo "   Frontend: $FRONTEND_URL"
    echo ""
    echo "🔍 You can check the status in the AWS Console:"
    echo "   ECS: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION"
    echo "   EC2 Load Balancers: https://console.aws.amazon.com/ec2/v2/home?region=$AWS_REGION#LoadBalancers:"
    
else
    echo "❌ Deployment cancelled."
    exit 1
fi

cd ../..

echo ""
echo "✅ Deployment script completed!"
echo "🎉 Your WOPS AI application should be available shortly at the URLs above."
echo ""
echo "📚 Next steps:"
echo "1. Configure your domain and SSL certificate"
echo "2. Set up monitoring and alerts"
echo "3. Configure your Snowflake connection"
echo "4. Add your API keys to AWS Secrets Manager"