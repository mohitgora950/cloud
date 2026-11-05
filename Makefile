.PHONY: all up down train test lint clean

# Default target
all: test

# Task 6: make up builds and deploys the whole system from a fresh clone
up:
	@echo "Creating k3d cluster from cluster/k3d.yaml..."
	k3d cluster create --config cluster/k3d.yaml || true
	@echo "Deploying SeaweedFS in namespace data..."
	kubectl apply -f cluster/seaweedfs.yaml
	@echo "Creating application namespace and secrets..."
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/secret.yaml
	@echo "Building service container image..."
	docker build -t command-parser:v1 -f service/Dockerfile .
	@echo "Importing image into k3d cluster..."
	k3d image import command-parser:v1 -c cloud-cluster
	@echo "Deploying application, service, ingress, and HPA..."
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	kubectl apply -f k8s/ingress.yaml
	kubectl apply -f k8s/hpa.yaml
	@echo "Deployment complete! Application running on http://localhost:8080/parse"

# Task 6: make down deletes the cluster
down:
	@echo "Deleting k3d cluster cloud-cluster..."
	k3d cluster delete cloud-cluster

# Task 2: make train reading config.yaml, supports SUBSET=50
train:
	@echo "Executing Pythia-70m training..."
ifdef SUBSET
	python training/train.py --subset $(SUBSET)
else
	python training/train.py
endif

# Unit testing
test:
	python -m pytest tests/test_service.py -v

# Linting
lint:
	flake8 service/ worker/ training/ tests/ tools/ --count --max-line-length=127 --statistics

# Cleaning artifacts
clean:
	rm -rf models/test __pycache__ */__pycache__
