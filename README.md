# Flask + MongoDB on Kubernetes (Minikube)

A containerized Flask REST API backed by MongoDB, deployed on a local Kubernetes cluster using Minikube. Built as part of the FarAlpha SDE Intern Assignment to demonstrate working knowledge of container orchestration, persistent storage, service discovery, and horizontal autoscaling.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Technologies Used](#technologies-used)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Getting Started](#getting-started)
   - [Python Virtual Environment Setup](#python-virtual-environment-setup)
   - [Local Flask Testing (Without Kubernetes)](#local-flask-testing-without-kubernetes)
7. [Flask Application Details](#flask-application-details)
8. [Dockerfile Explanation](#dockerfile-explanation)
9. [Kubernetes Deployment Guide](#kubernetes-deployment-guide)
   - [Step 1: Start Minikube](#step-1-start-minikube)
   - [Step 2: Build the Docker Image (Without Docker Desktop)](#step-2-build-the-docker-image-without-docker-desktop)
   - [Step 3: Deploy MongoDB](#step-3-deploy-mongodb)
   - [Step 4: Deploy Flask](#step-4-deploy-flask)
   - [Step 5: Access the Application](#step-5-access-the-application)
10. [MongoDB Configuration](#mongodb-configuration)
    - [Authentication Setup](#authentication-setup)
    - [StatefulSet Explained](#statefulset-explained)
    - [Persistent Volume and PVC](#persistent-volume-and-pvc)
11. [Kubernetes Services](#kubernetes-services)
12. [Kubernetes DNS and Service Discovery](#kubernetes-dns-and-service-discovery)
13. [Horizontal Pod Autoscaler (HPA)](#horizontal-pod-autoscaler-hpa)
14. [Resource Requests and Limits](#resource-requests-and-limits)
15. [API Testing](#api-testing)
16. [Persistence Testing](#persistence-testing)
17. [Autoscaling Testing](#autoscaling-testing)
18. [Docker Build & Push (For CI/CD or External Environments)](#docker-build--push-for-cicd-or-external-environments)
19. [Design Decisions](#design-decisions)
20. [Troubleshooting](#troubleshooting)
21. [Screenshots](#screenshots)

---

## Project Overview

This project deploys a simple Flask REST API that talks to a MongoDB database, all running inside a Kubernetes cluster managed by Minikube. The whole thing runs locally without needing a cloud provider or Docker Desktop.

The Flask app exposes three endpoints — a root welcome page, a POST endpoint to store JSON data in MongoDB, and a GET endpoint to retrieve that data. MongoDB runs as a StatefulSet with persistent storage so data survives pod restarts. The Flask deployment runs with at least 2 replicas and scales up to 5 based on CPU usage.

## Problem Statement

Design and deploy a containerized web application on Kubernetes that demonstrates:
- Building and deploying container images locally
- Database deployment with authentication and persistent storage
- Service discovery using Kubernetes DNS
- Horizontal autoscaling based on resource metrics
- Proper resource management and production-ready configuration

## Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.9** | Application runtime |
| **Flask 2.0.2** | Lightweight web framework for the REST API |
| **PyMongo 3.12.0** | MongoDB driver for Python |
| **Gunicorn 20.1.0** | Production WSGI server (replaces Flask's dev server) |
| **MongoDB 5.0** | NoSQL document database |
| **Kubernetes** | Container orchestration platform |
| **Minikube** | Runs a local single-node Kubernetes cluster |
| **containerd** | Container runtime (used instead of Docker) |
| **kubectl** | CLI tool for interacting with Kubernetes |

## Project Structure

```
faralpha-k8s-assignment/
│
├── app/
│   ├── app.py                  # Flask application code
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile              # Container image definition
│
├── k8s/
│   ├── mongo-secret.yaml       # MongoDB credentials (base64 encoded)
│   ├── mongo-pv-pvc.yaml       # Persistent Volume + Claim for MongoDB data
│   ├── mongo-service.yaml      # Internal ClusterIP service for MongoDB
│   ├── mongo-statefulset.yaml  # MongoDB StatefulSet with auth
│   ├── flask-deployment.yaml   # Flask Deployment (2 replicas)
│   ├── flask-service.yaml      # NodePort service to expose Flask
│   └── flask-hpa.yaml          # Horizontal Pod Autoscaler config
│
├── screenshots/                # Evidence of running deployment
│   ├── 01-pods-services.png
│   ├── 02-api-crud-test.png
│   ├── 03-hpa-autoscaling.png
│   └── 04-db-persistence.png
│
├── .gitignore
├── .dockerignore
└── README.md
```

## Prerequisites

Before getting started, make sure you have these installed:

- **Windows 10/11** (64-bit) with hardware virtualization enabled in BIOS
- **Python 3.8+** — [python.org/downloads](https://www.python.org/downloads/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **Minikube** — [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start/)
- **kubectl** — [kubernetes.io/docs/tasks/tools](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)
- **Hyper-V** enabled (Windows Pro/Enterprise) **OR VirtualBox** installed

> **Note:** Docker Desktop is NOT required. We use Minikube's built-in image building capability with the containerd runtime.

### Installing Minikube and kubectl on Windows

```bash
# using winget (recommended)
winget install Kubernetes.minikube
winget install Kubernetes.kubectl

# or download directly:
# minikube: https://minikube.sigs.k8s.io/docs/start/
# kubectl: https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe
```

### Enabling Hyper-V (if using Hyper-V driver)

Open PowerShell as Administrator:
```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```
This requires a reboot. After reboot, Hyper-V will be available as a Minikube driver.

---

## Getting Started

### Python Virtual Environment Setup

Setting up a virtual environment keeps the project dependencies isolated from the system Python:

```bash
# navigate to the project
cd faralpha-k8s-assignment

# create a virtual environment
python -m venv venv

# activate it
# on Windows:
venv\Scripts\activate

# on Linux/Mac:
# source venv/bin/activate

# install dependencies
pip install -r app/requirements.txt
```

### Local Flask Testing (Without Kubernetes)

You can run the Flask app locally to test the code before deploying to Kubernetes. You'd need a local MongoDB instance running for the database endpoints to work, but the root endpoint works without it.

```bash
# set environment variables (PowerShell)
$env:MONGO_HOST = "localhost"
$env:MONGO_PORT = "27017"
$env:MONGO_DB = "flaskdb"

# run the flask development server
cd app
python app.py
```

The app will be available at `http://localhost:5000`.

---

## Flask Application Details

The Flask app (`app/app.py`) is a straightforward REST API with three endpoints:

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Returns a welcome message with the current timestamp |
| POST | `/data` | Accepts a JSON body and stores it in MongoDB |
| GET | `/data` | Retrieves all stored documents from MongoDB |

### How the MongoDB Connection Works

The app reads connection details from environment variables instead of hardcoding them. This is a standard practice — it means the same code works in development (pointing to localhost) and in Kubernetes (pointing to the mongo-service DNS name) without any changes.

```python
mongo_host = os.environ.get("MONGO_HOST", "localhost")
mongo_port = os.environ.get("MONGO_PORT", "27017")
mongo_user = os.environ.get("MONGO_USERNAME", "")
mongo_pass = os.environ.get("MONGO_PASSWORD", "")
```

If credentials are provided, the app builds an authenticated MongoDB URI:
```
mongodb://admin:faralpha2024@mongo-service:27017/flaskdb?authSource=admin
```

### Error Handling

The app handles several failure scenarios:
- **Invalid JSON body** → 400 Bad Request
- **Empty JSON body** → 400 Bad Request
- **MongoDB connection failure** → 503 Service Unavailable
- **MongoDB timeout** → 503 Service Unavailable
- **Unexpected errors** → 500 Internal Server Error

The `_id` field is excluded from GET responses because it's MongoDB's internal identifier and isn't JSON-serializable without special handling.

---

## Dockerfile Explanation

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
```

What each part does:

1. **`python:3.9-slim`** — Uses a minimal Python image. The slim variant is about 150MB smaller than the full image while still having everything we need.

2. **`COPY requirements.txt` first** — Docker caches each layer. By copying and installing dependencies before the application code, Docker can reuse the cached dependency layer when only the app code changes. This makes rebuilds much faster.

3. **`--no-cache-dir`** — Tells pip not to cache downloaded packages inside the container. Keeps the image smaller.

4. **`EXPOSE 5000`** — Documents that the container listens on port 5000. It doesn't actually publish the port — that's handled by Kubernetes.

5. **Gunicorn** — Flask's built-in server is meant for development only. Gunicorn is a production-grade WSGI server that can handle multiple concurrent requests. We use 4 workers, which is a reasonable default for most workloads.

---

## Kubernetes Deployment Guide

### Step 1: Start Minikube

Start a local Kubernetes cluster using Minikube with the containerd runtime:

```bash
# using Hyper-V driver (Windows Pro/Enterprise)
minikube start --driver=hyperv --container-runtime=containerd --memory=4096 --cpus=2

# OR using VirtualBox driver
minikube start --driver=virtualbox --container-runtime=containerd --memory=4096 --cpus=2
```

Verify the cluster is running:
```bash
kubectl cluster-info
kubectl get nodes
```

Expected output:
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   1m    v1.28.x
```

### Step 2: Build the Docker Image (Without Docker Desktop)

Since we don't have Docker Desktop installed, we use Minikube's built-in image building capability. Minikube can build container images directly inside its VM using the containerd runtime — no Docker required on the host machine.

```bash
# build the Flask app image inside Minikube
minikube image build -t flask-app:latest ./app
```

This command sends the build context (the `./app` directory) to Minikube's VM and builds the image there using the Dockerfile. The resulting image is available inside Minikube immediately.

Verify the image was built:
```bash
minikube image ls | findstr flask-app
```

You should see `docker.io/library/flask-app:latest` in the list.

> **Why `imagePullPolicy: Never`?**
> In the Flask deployment manifest, we set `imagePullPolicy: Never` to tell Kubernetes not to try pulling the image from a remote registry. Since we built the image directly inside Minikube, it's already available locally.

### Step 3: Deploy MongoDB

Deploy the resources in this order — secrets first, then storage, then the service, and finally the StatefulSet:

```bash
# create the secret containing MongoDB credentials
kubectl apply -f k8s/mongo-secret.yaml

# create persistent volume and claim
kubectl apply -f k8s/mongo-pv-pvc.yaml

# create the internal service for MongoDB
kubectl apply -f k8s/mongo-service.yaml

# deploy the MongoDB StatefulSet
kubectl apply -f k8s/mongo-statefulset.yaml
```

Wait for MongoDB to be ready:
```bash
kubectl get pods -w
```

Wait until `mongo-0` shows `1/1 Running` before proceeding.

### Step 4: Deploy Flask

```bash
# deploy the Flask application (2 replicas)
kubectl apply -f k8s/flask-deployment.yaml

# expose Flask via NodePort service
kubectl apply -f k8s/flask-service.yaml

# set up the Horizontal Pod Autoscaler
kubectl apply -f k8s/flask-hpa.yaml
```

Check everything is running:
```bash
kubectl get all
```

### Step 5: Access the Application

Get the URL to access Flask through Minikube:

```bash
minikube service flask-service --url
```

This prints something like `http://192.168.49.2:30007`. Use that URL to hit the API.

Alternatively, if that doesn't work (some drivers have issues with service URLs), use:
```bash
# get minikube IP
minikube ip

# then access http://<minikube-ip>:30007
```

### Quick Deploy (All at Once)

If you want to deploy everything in one go:
```bash
kubectl apply -f k8s/mongo-secret.yaml
kubectl apply -f k8s/mongo-pv-pvc.yaml
kubectl apply -f k8s/mongo-service.yaml
kubectl apply -f k8s/mongo-statefulset.yaml

# wait for MongoDB to be ready
kubectl wait --for=condition=ready pod/mongo-0 --timeout=120s

kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
kubectl apply -f k8s/flask-hpa.yaml
```

---

## MongoDB Configuration

### Authentication Setup

MongoDB authentication is handled through Kubernetes Secrets. The `mongo-secret.yaml` file contains base64-encoded credentials:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mongo-secret
type: Opaque
data:
  mongo-username: YWRtaW4=        # "admin" in base64
  mongo-password: ZmFyYWxwaGEyMDI0  # "faralpha2024" in base64
```

The MongoDB container reads these through the `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` environment variables. When MongoDB starts for the first time, it automatically creates a root user with these credentials.

The Flask app also reads from the same secret (via `secretKeyRef` in its deployment) so both sides use the same credentials without hardcoding anything.

### StatefulSet Explained

I used a StatefulSet instead of a Deployment for MongoDB because:

1. **Stable network identity** — StatefulSet pods get predictable names like `mongo-0`, `mongo-1`, etc. This matters for databases because clients need to know which pod they're connecting to.

2. **Ordered startup/shutdown** — Pods are created one at a time in order and terminated in reverse order. Important for databases to avoid data corruption.

3. **Stable storage** — Each pod gets its own persistent volume that follows it across rescheduling. If `mongo-0` gets restarted on a different node, its data follows it.

For this project, we only need a single replica (`replicas: 1`) since it's a demonstration, not a production cluster.

### Persistent Volume and PVC

The PV/PVC setup ensures MongoDB data survives pod restarts:

**PersistentVolume (PV):**
- Allocates 1Gi of storage on the host at `/data/mongo`
- Uses `hostPath` since we're on Minikube (single-node cluster)
- `Retain` reclaim policy means data isn't deleted even if the PVC is removed

**PersistentVolumeClaim (PVC):**
- Requests 1Gi of storage with `ReadWriteOnce` access
- Binds to the PV automatically based on matching capacity and access mode

The MongoDB container mounts this storage at `/data/db`, which is where MongoDB stores its data files by default.

---

## Kubernetes Services

### Flask Service (NodePort)

```yaml
type: NodePort
ports:
  - port: 5000
    targetPort: 5000
    nodePort: 30007
```

- **port 5000** — The port inside the cluster where the service is reachable
- **targetPort 5000** — The port on the Flask container
- **nodePort 30007** — The port on the Minikube VM that maps to this service

NodePort is the right choice here because we need to access Flask from outside the cluster (our browser/terminal). The valid range for NodePort is 30000-32767.

### MongoDB Service (ClusterIP)

```yaml
type: ClusterIP
ports:
  - port: 27017
    targetPort: 27017
```

ClusterIP is the default service type and it's intentionally used here. It means MongoDB is only reachable from within the cluster. There's no reason for MongoDB to be accessible from outside — only the Flask pods need to talk to it, and they can reach it through the service's internal DNS name.

---

## Kubernetes DNS and Service Discovery

One of the really nice things about Kubernetes is its built-in DNS. When we create a Service, Kubernetes automatically creates a DNS entry for it. This means pods can find each other by service name instead of hardcoded IP addresses.

### How it Works

When Flask wants to connect to MongoDB, it uses the hostname `mongo-service`. Here's what happens behind the scenes:

1. Flask sends a DNS query for `mongo-service`
2. The cluster's CoreDNS server resolves it to the ClusterIP of the MongoDB service
3. The service forwards traffic to the actual MongoDB pod

### DNS Name Format

Kubernetes DNS follows this pattern:
```
<service-name>.<namespace>.svc.cluster.local
```

For our services:
- Flask: `flask-service.default.svc.cluster.local`
- MongoDB: `mongo-service.default.svc.cluster.local`

Since both services are in the same namespace (`default`), Flask can simply use `mongo-service` as the hostname — no need for the full FQDN.

### In the Flask App

The MongoDB connection in Flask uses the service name:
```python
mongo_host = os.environ.get("MONGO_HOST", "localhost")
# In Kubernetes, MONGO_HOST is set to "mongo-service"
```

And in the deployment manifest:
```yaml
env:
  - name: MONGO_HOST
    value: "mongo-service"
```

This is the connection flow:

```
Flask Pod → DNS lookup "mongo-service" → ClusterIP (10.96.x.x) → MongoDB Pod
```

### Why This Approach?

Using DNS-based service discovery means:
- If MongoDB pod restarts and gets a new IP, the service DNS still resolves correctly
- No hardcoded IPs anywhere in the code
- Same code works in any namespace — just change the MONGO_HOST env var

---

## Horizontal Pod Autoscaler (HPA)

The HPA automatically scales the Flask deployment between 2 and 5 replicas based on CPU utilization.

### Configuration

```yaml
minReplicas: 2
maxReplicas: 5
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

This means:
- **Always keep at least 2 replicas running** — ensures high availability
- **Scale up to 5 replicas** when average CPU usage across all pods exceeds 70%
- **Scale back down** when CPU drops below the threshold (there's a default cooldown period of 5 minutes)

### Enabling Metrics Server

The HPA needs the Metrics Server to get CPU/memory data from pods. On Minikube, enable it with:

```bash
minikube addons enable metrics-server
```

Verify it's working:
```bash
kubectl top pods
kubectl top nodes
```

### How HPA Calculates Desired Replicas

The formula is roughly:
```
desiredReplicas = ceil(currentReplicas × (currentCPU / targetCPU))
```

For example, if 2 pods are using 90% CPU each:
```
desired = ceil(2 × (90/70)) = ceil(2.57) = 3
```

So it would scale up to 3 replicas to bring the average back down.

---

## Resource Requests and Limits

Both Flask and MongoDB pods have resource constraints configured:

```yaml
resources:
  requests:
    cpu: "200m"
    memory: "250Mi"
  limits:
    cpu: "500m"
    memory: "500Mi"
```

### What Each Value Means

| Field | Value | Meaning |
|---|---|---|
| **CPU Request** | 200m | The pod is guaranteed 0.2 CPU cores (200 millicores). The scheduler uses this to decide where to place the pod — it won't schedule it on a node that doesn't have 200m available. |
| **CPU Limit** | 500m | The pod can burst up to 0.5 CPU cores if the node has spare capacity, but it will be throttled if it tries to use more than this consistently. |
| **Memory Request** | 250Mi | The pod is guaranteed 250 MiB of RAM. Similar to CPU request — used for scheduling decisions. |
| **Memory Limit** | 500Mi | If the pod tries to use more than 500 MiB, it gets OOM-killed (Out of Memory) and restarted. Memory isn't throttleable like CPU — if you exceed the limit, the process dies. |

### Why Both Requests and Limits?

- **Requests** = minimum guaranteed resources. This is what the scheduler uses to place pods on nodes. Setting this too high wastes resources; too low and the pod might not get enough to run properly.

- **Limits** = maximum allowed resources. This prevents a misbehaving pod from starving other pods on the same node. CPU over-limit causes throttling (slower, but still running). Memory over-limit causes OOM kill (pod restarts).

The gap between request and limit (200m→500m CPU, 250Mi→500Mi memory) allows burstable performance while maintaining a minimum guarantee. This is called a "Burstable" QoS class in Kubernetes.

---

## API Testing

Once the application is deployed and accessible, test the endpoints:

### 1. Root Endpoint
```bash
curl http://<minikube-ip>:30007/
```

Expected response:
```
Welcome to the Flask app! The current time is: 2024-11-19 12:30:45
```

### 2. POST Data
```bash
curl -X POST http://<minikube-ip>:30007/data \
  -H "Content-Type: application/json" \
  -d '{"name": "FarAlpha", "type": "fintech", "location": "India"}'
```

Expected response:
```json
{
  "message": "Data inserted successfully",
  "id": "655a1234abcd5678ef901234"
}
```

### 3. GET Data
```bash
curl http://<minikube-ip>:30007/data
```

Expected response:
```json
[
  {
    "name": "FarAlpha",
    "type": "fintech",
    "location": "India"
  }
]
```

### 4. Invalid Request (No JSON)
```bash
curl -X POST http://<minikube-ip>:30007/data \
  -H "Content-Type: text/plain" \
  -d "this is not json"
```

Expected response:
```json
{
  "error": "Request body must be valid JSON"
}
```

### 5. Check Pod Logs
```bash
kubectl logs -l app=flask-app --tail=20
```

---

## Persistence Testing

This test verifies that MongoDB data survives pod restarts:

### Step 1: Insert data
```bash
curl -X POST http://<minikube-ip>:30007/data \
  -H "Content-Type: application/json" \
  -d '{"test": "persistence check", "timestamp": "before-restart"}'
```

### Step 2: Verify data exists
```bash
curl http://<minikube-ip>:30007/data
```

### Step 3: Delete the MongoDB pod (simulate a crash)
```bash
kubectl delete pod mongo-0
```

The StatefulSet controller will automatically recreate the pod. Wait for it:
```bash
kubectl get pods -w
```

### Step 4: Verify data survived
```bash
# wait for mongo-0 to be Running again, then:
curl http://<minikube-ip>:30007/data
```

The data from Step 1 should still be there because it's stored on the PersistentVolume, which is independent of the pod lifecycle.

---

## Autoscaling Testing

### Generate Load

Open a separate terminal and run a load generator:

```bash
# using a busybox pod inside the cluster for more consistent load
kubectl run load-generator --image=busybox --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://flask-service:5000/data; done"
```

### Monitor HPA

In another terminal, watch the HPA:

```bash
kubectl get hpa flask-app-hpa --watch
```

Expected output (over a few minutes):
```
NAME            REFERENCE              TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
flask-app-hpa   Deployment/flask-app   12%/70%   2         5         2          5m
flask-app-hpa   Deployment/flask-app   78%/70%   2         5         3          6m
flask-app-hpa   Deployment/flask-app   85%/70%   2         5         4          7m
```

### Stop the Load

```bash
kubectl delete pod load-generator
```

After about 5 minutes of cooldown, the HPA will scale back down to 2 replicas.

### Verify Scaling Happened

```bash
kubectl describe hpa flask-app-hpa
kubectl get pods -l app=flask-app
```

---

## Docker Build & Push (For CI/CD or External Environments)

If you're on a machine with Docker installed (or in a CI pipeline), here's how to build and push the image to a container registry:

```bash
# build the image
docker build -t flask-app:latest ./app

# tag for Docker Hub (replace with your username)
docker tag flask-app:latest yourusername/flask-app:latest

# push to Docker Hub
docker login
docker push yourusername/flask-app:latest
```

If using a private registry, update the `flask-deployment.yaml` to use the full image name:
```yaml
image: yourusername/flask-app:latest
imagePullPolicy: Always  # change from Never to Always when using a registry
```

> **Note:** This section is for reference when deploying to environments that have Docker available (cloud VMs, CI/CD systems, etc.). For local development with Minikube, use the `minikube image build` workflow described in the [deployment guide](#step-2-build-the-docker-image-without-docker-desktop).

---

## Design Decisions

### Why StatefulSet for MongoDB?

A regular Deployment would technically work for a single MongoDB replica, but StatefulSet provides stable network identity and ordered lifecycle management, which are important for databases. If we ever needed to scale MongoDB to a replica set, the StatefulSet pattern already handles the complexity of stable pod names and volume claims.

### Why NodePort for Flask?

In a production environment, we'd use a LoadBalancer service (on a cloud provider) or an Ingress controller. But for local development with Minikube, NodePort is the simplest way to expose a service. It maps a port on the Minikube VM directly to the service.

### Why ClusterIP for MongoDB?

Databases should never be directly accessible from outside the cluster. ClusterIP restricts access to within the cluster only, which means only the Flask pods (or other pods in the same cluster) can connect to MongoDB. This is a security best practice.

### Why Gunicorn Instead of Flask's Dev Server?

Flask's built-in `app.run()` server is single-threaded and not suitable for production. It's designed for development only. Gunicorn is a mature WSGI HTTP server that can handle concurrent requests with multiple worker processes, provides better error handling, and is what most Flask applications use in production.

### Why containerd Instead of Docker Runtime?

Kubernetes deprecated Docker as a container runtime in v1.24. containerd is the standard runtime going forward and is more lightweight since it doesn't include Docker's extra tooling. Using containerd also means we can build and run containers without Docker Desktop installed.

### Why `imagePullPolicy: Never`?

Since we build the Flask image directly inside Minikube using `minikube image build`, the image only exists locally inside the VM. Setting `imagePullPolicy: Never` tells Kubernetes to skip trying to pull the image from Docker Hub or any other remote registry.

---

## Troubleshooting

### Pod is in CrashLoopBackOff

```bash
# check the pod logs for error details
kubectl logs <pod-name> --previous

# describe the pod for events
kubectl describe pod <pod-name>
```

Common causes:
- MongoDB credentials mismatch between the secret and what Flask is using
- MongoDB not ready yet when Flask starts (the readiness probe handles this)

### Flask Can't Connect to MongoDB

```bash
# verify the mongo service exists and has endpoints
kubectl get svc mongo-service
kubectl get endpoints mongo-service

# test DNS resolution from inside a pod
kubectl run dns-test --image=busybox --rm -it -- nslookup mongo-service
```

### Image Not Found

If you see `ErrImageNeverPull`:
```bash
# make sure the image was built inside Minikube
minikube image ls | findstr flask-app

# if not, rebuild it
minikube image build -t flask-app:latest ./app
```

### HPA Shows "unknown" for Metrics

```bash
# enable metrics server
minikube addons enable metrics-server

# wait a minute, then check
kubectl top pods
kubectl get hpa
```

### PersistentVolume Not Binding

```bash
kubectl get pv
kubectl get pvc

# if the PVC is stuck in Pending, describe it for details
kubectl describe pvc mongo-pvc
```

### Minikube Won't Start

```bash
# try deleting and recreating the cluster
minikube delete
minikube start --driver=hyperv --container-runtime=containerd --memory=4096 --cpus=2
```

---

## Screenshots

Evidence of the working deployment:

| Screenshot | Description |
|---|---|
| `01-pods-services.png` | Running Flask replicas, MongoDB StatefulSet, and Kubernetes Services |
| `02-api-crud-test.png` | Successful POST and GET API requests |
| `03-hpa-autoscaling.png` | HPA metrics showing actual replica scaling |
| `04-db-persistence.png` | Data retrieval after MongoDB pod restart |

---

## Cleanup

To tear down the entire deployment:

```bash
# delete all Kubernetes resources
kubectl delete -f k8s/flask-hpa.yaml
kubectl delete -f k8s/flask-service.yaml
kubectl delete -f k8s/flask-deployment.yaml
kubectl delete -f k8s/mongo-statefulset.yaml
kubectl delete -f k8s/mongo-service.yaml
kubectl delete -f k8s/mongo-pv-pvc.yaml
kubectl delete -f k8s/mongo-secret.yaml

# stop Minikube
minikube stop

# or delete the entire cluster
minikube delete
```

---

*Built for the FarAlpha SDE Intern Assignment*

