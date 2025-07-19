.PHONY: help install dev build test clean deploy

help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Start development servers"
	@echo "  build      - Build Docker images"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up containers and volumes"
	@echo "  deploy     - Deploy to AWS"

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev:
	@echo "Starting development environment..."
	docker-compose up -d postgres redis
	@echo "Waiting for services to start..."
	sleep 5
	@echo "Starting backend..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend..."
	cd frontend && npm run dev &
	@echo "Development servers started!"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"

build:
	@echo "Building Docker images..."
	docker-compose build

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest
	@echo "Running frontend tests..."
	cd frontend && npm run test

clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f

deploy:
	@echo "Deploying to AWS..."
	@echo "Building and pushing Docker images..."
	@./scripts/deploy.sh

# AWS specific targets
terraform-init:
	cd infrastructure/aws && terraform init

terraform-plan:
	cd infrastructure/aws && terraform plan

terraform-apply:
	cd infrastructure/aws && terraform apply

terraform-destroy:
	cd infrastructure/aws && terraform destroy