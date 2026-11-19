# Flask + MongoDB on Kubernetes

This project is a simple REST API built with Flask that connects to a MongoDB database — both running inside a local Kubernetes cluster using Minikube. I built this as part of the FarAlpha SDE Intern assignment to get hands-on with container orchestration, service discovery, persistent storage, and autoscaling.

The idea is pretty simple: a Flask app that lets you store and retrieve JSON data from MongoDB, but the interesting part is how everything is deployed and managed through Kubernetes.

## What Does the App Do?

Three endpoints:

| Method | Route | What it does |
|--------|-------|-------------|
| GET | `/` | Shows a welcome message with the current server time |
| POST | `/data` | Takes a JSON payload and saves it to MongoDB |
| GET | `/data` | Returns all the saved documents |

Nothing fancy, but enough to demonstrate the full stack working end-to-end.

## Tech Stack

- **Python 3.9** / **Flask 2.0.2** — for the API
- **MongoDB 5.0** — as the database
- **PyMongo 3.12.0** — to talk to MongoDB from Python
- **Gunicorn** — production WSGI server (instead of Flask's dev server)
- **Kubernetes (Minikube)** — for orchestration
- **containerd** — container runtime
- **kubectl** — to interact with the cluster

## Project Structure

```
faralpha-k8s-assignment/
├── app/
│   ├── app.py                  # the flask app
│   ├── requirements.txt        # python deps
│   └── Dockerfile              # container image config
├── k8s/
│   ├── mongo-secret.yaml       # db credentials
│   ├── mongo-pv-pvc.yaml       # persistent storage for mongo
│   ├── mongo-service.yaml      # internal service for mongo
│   ├── mongo-statefulset.yaml  # mongo deployment
│   ├── flask-deployment.yaml   # flask deployment (2 replicas)
│   ├── flask-service.yaml      # exposes flask externally
│   └── flask-hpa.yaml          # autoscaler config
├── screenshots/                # proof that everything works
├── .gitignore
├── .dockerignore
└── README.md
```

## Prerequisites

You'll need these installed before getting started:

- **Windows 10/11** (64-bit) with virtualization enabled in BIOS
- **Python 3.8+**
- **Git**
- **Minikube** — for the local k8s cluster
- **kubectl** — to manage the cluster
- **Hyper-V** (Windows Pro/Enterprise) or **VirtualBox**

You do **not** need Docker Desktop. I used Minikube's built-in image building which works with containerd directly.

### Installing Minikube & kubectl

```bash
# with winget
winget install Kubernetes.minikube
winget install Kubernetes.kubectl
```

Or download them from:
- Minikube: https://minikube.sigs.k8s.io/docs/start/
- kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/

If you're using Hyper-V, enable it first (needs admin PowerShell + a reboot):
```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

## Running Locally (Without Kubernetes)

If you just want to test the Flask code without setting up a whole cluster:

```bash
cd faralpha-k8s-assignment
python -m venv venv
venv\Scripts\activate
pip install -r app/requirements.txt

# set mongo connection env vars
set MONGO_HOST=localhost
set MONGO_PORT=27017
set MONGO_DB=flaskdb

cd app
python app.py
```

The root endpoint (`/`) works without MongoDB. For `/data` endpoints you'd need a local MongoDB running.

## How I Built the Docker Image Without Docker

This was one of the tricky parts. Since I didn't have Docker Desktop installed, I couldn't just do `docker build`. But Minikube has a neat feature — `minikube image build` — which builds the image directly inside the Minikube VM using containerd. No Docker needed on the host machine.

```bash
minikube image build -t flask-app:latest ./app
```

Then in the deployment yaml, I set `imagePullPolicy: Never` so Kubernetes uses the local image instead of trying to pull from Docker Hub.

To verify the image exists:
```bash
minikube image ls | findstr flask-app
```

## Deploying to Kubernetes

### 1. Start the cluster

```bash
# pick one depending on what you have
minikube start --driver=hyperv --container-runtime=containerd --memory=4096 --cpus=2

# or with virtualbox
minikube start --driver=virtualbox --container-runtime=containerd --memory=4096 --cpus=2
```

Check it's running:
```bash
kubectl get nodes
```

### 2. Build the Flask image

```bash
minikube image build -t flask-app:latest ./app
```

### 3. Deploy everything

Order matters here — secrets and storage need to exist before the pods that use them.

```bash
# mongo stuff first
kubectl apply -f k8s/mongo-secret.yaml
kubectl apply -f k8s/mongo-pv-pvc.yaml
kubectl apply -f k8s/mongo-service.yaml
kubectl apply -f k8s/mongo-statefulset.yaml

# wait for mongo to come up
kubectl wait --for=condition=ready pod/mongo-0 --timeout=120s

# then flask
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
kubectl apply -f k8s/flask-hpa.yaml
```

### 4. Access the app

```bash
minikube service flask-service --url
```

This gives you something like `http://192.168.49.2:30007`. Hit that URL and you should see the welcome message.

## MongoDB Setup

### Authentication

MongoDB credentials are stored in a Kubernetes Secret (`mongo-secret.yaml`). The values are base64 encoded — not encrypted, just encoded. In a real production setup you'd use something like Sealed Secrets or a vault, but for this project base64 is what k8s expects.

The Secret gets mounted as environment variables in both the MongoDB pod (for creating the root user on first boot) and the Flask pods (for connecting with those credentials).

### Why StatefulSet?

I used a StatefulSet instead of a regular Deployment for MongoDB. The main reason is that StatefulSets give pods a stable identity — the pod is always called `mongo-0`, not some random hash. This is important for databases because if the pod restarts, it comes back with the same name and gets reconnected to the same storage volume.

For this project I only need 1 replica, but if I ever wanted to set up a MongoDB replica set, the StatefulSet pattern would already handle the complexity of ordered startup and stable naming.

### Persistent Storage

The PV/PVC setup makes sure MongoDB data doesn't disappear when the pod restarts.

- **PersistentVolume (PV)** — allocates 1Gi on the node at `/data/mongo`. I used `hostPath` since Minikube is a single-node cluster. The `Retain` reclaim policy means data stays even if you delete the PVC.

- **PersistentVolumeClaim (PVC)** — this is what the pod actually uses. It requests 1Gi and binds to the PV.

MongoDB's container mounts the PVC at `/data/db` which is MongoDB's default data directory.

I tested this by inserting data, deleting the mongo-0 pod, waiting for it to come back, and checking that the data was still there. It works — see the screenshot in `screenshots/04-db-persistence.png`.

## Services

**Flask Service (NodePort)** — Exposes the Flask app on port 30007. NodePort is the simplest way to access a service from outside the cluster when using Minikube. In a cloud setup you'd probably use a LoadBalancer or Ingress instead.

**MongoDB Service (ClusterIP)** — This is intentionally internal-only. There's no reason for MongoDB to be accessible from outside the cluster. Only Flask pods need to reach it, and they can do that through the internal DNS.

## Kubernetes DNS — How Flask Finds MongoDB

This is probably the coolest part of the setup. When you create a Service in Kubernetes, it automatically gets a DNS name. So instead of hardcoding MongoDB's IP address (which can change), Flask just uses the service name `mongo-service` as the hostname.

The full DNS name follows this pattern:
```
<service-name>.<namespace>.svc.cluster.local
```

So for MongoDB it's `mongo-service.default.svc.cluster.local`. But since Flask is in the same namespace, I can just use `mongo-service` and it resolves fine.

In the Flask deployment, `MONGO_HOST` is set to `mongo-service`:
```yaml
env:
  - name: MONGO_HOST
    value: "mongo-service"
```

And in the Python code:
```python
mongo_host = os.environ.get("MONGO_HOST", "localhost")
```

So the connection string ends up being something like:
```
mongodb://admin:faralpha2024@mongo-service:27017/flaskdb?authSource=admin
```

This way, even if the MongoDB pod gets rescheduled to a different IP, the DNS name stays the same and Flask can still connect without any config changes.

## Horizontal Pod Autoscaler

The HPA watches CPU usage across Flask pods and scales between 2 and 5 replicas. If average CPU goes above 70%, it adds more pods. When load drops, it scales back down (after a ~5 min cooldown).

Config:
- Min replicas: 2 (so there's always redundancy)
- Max replicas: 5
- Target: 70% average CPU utilization

You need metrics-server enabled for this to work:
```bash
minikube addons enable metrics-server
```

### Testing autoscaling

I used a simple load generator:
```bash
kubectl run load-gen --image=busybox --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://flask-service:5000/data; done"
```

Then watched the HPA:
```bash
kubectl get hpa flask-app-hpa --watch
```

After a couple minutes of sustained load, replicas went from 2 to 4. The screenshot (`03-hpa-autoscaling.png`) shows the progression.

To stop the load:
```bash
kubectl delete pod load-gen
```

## Resource Requests and Limits

Both Flask and MongoDB have resource constraints:

```yaml
resources:
  requests:
    cpu: "200m"
    memory: "250Mi"
  limits:
    cpu: "500m"
    memory: "500Mi"
```

Here's what each one means:

- **CPU request (200m)** — the pod is guaranteed 0.2 cores. The scheduler won't put it on a node that doesn't have this much available.
- **CPU limit (500m)** — the pod can use up to 0.5 cores. If it tries to use more, it gets throttled (runs slower but doesn't crash).
- **Memory request (250Mi)** — guaranteed 250MB of RAM. Used for scheduling.
- **Memory limit (500Mi)** — hard cap. If the pod exceeds this, it gets killed (OOMKilled) and restarted. Unlike CPU, memory can't be throttled.

The gap between request and limit allows pods to burst when the node has spare capacity, while still maintaining a minimum guarantee. Kubernetes calls this the "Burstable" QoS class.

## API Testing

Once everything is deployed:

```bash
# root endpoint
curl http://<minikube-ip>:30007/
# Welcome to the Flask app! The current time is: 2026-11-19 17:22:14

# insert some data
curl -X POST http://<minikube-ip>:30007/data \
  -H "Content-Type: application/json" \
  -d '{"name": "FarAlpha", "type": "fintech"}'
# {"id":"674c8a1e3f2b1a0012d4e567","message":"Data inserted successfully"}

# get all data
curl http://<minikube-ip>:30007/data
# [{"name":"FarAlpha","type":"fintech"}]

# test error handling — sending non-json
curl -X POST http://<minikube-ip>:30007/data -d "not json"
# {"error":"Request body must be valid JSON"}
```

## Persistence Test

To verify data survives a pod crash:

1. Insert some data
2. Delete the mongo pod: `kubectl delete pod mongo-0`
3. Wait for it to come back: `kubectl get pods -w`
4. Query the data again — it should still be there

This works because the data is on the PersistentVolume, not inside the container. The container is ephemeral but the volume persists.

## Docker Build & Push (For Other Environments)

If you're on a machine that has Docker installed, or in a CI/CD pipeline:

```bash
docker build -t flask-app:latest ./app
docker tag flask-app:latest yourusername/flask-app:latest
docker login
docker push yourusername/flask-app:latest
```

Then update the deployment to pull from the registry:
```yaml
image: yourusername/flask-app:latest
imagePullPolicy: Always
```

This isn't needed for local Minikube development — it's just for when you want to deploy somewhere else.

## Some Design Choices

**Why Gunicorn?** Flask's built-in server is single-threaded and meant only for development. Gunicorn handles concurrent requests properly with multiple worker processes. Pretty much every Flask app in production uses it.

**Why containerd?** Kubernetes actually deprecated Docker as a runtime since v1.24. containerd is the standard now — it's lighter and doesn't carry all of Docker's extra tooling. Plus it meant I could skip installing Docker Desktop entirely.

**Why `imagePullPolicy: Never`?** Since the image is built directly inside Minikube with `minikube image build`, it only exists locally. Setting this tells Kubernetes not to try pulling from a remote registry.

**Why ClusterIP for MongoDB?** Security. The database should only be reachable from inside the cluster. There's no reason to expose port 27017 to the outside world.

## Troubleshooting

**Pod stuck in CrashLoopBackOff:**
```bash
kubectl logs <pod-name> --previous
kubectl describe pod <pod-name>
```
Usually means the app is crashing on startup — check if MongoDB is up and credentials match.

**Flask can't connect to MongoDB:**
```bash
kubectl get endpoints mongo-service
kubectl run dns-test --image=busybox --rm -it -- nslookup mongo-service
```

**Image not found (ErrImageNeverPull):**
```bash
# rebuild inside minikube
minikube image build -t flask-app:latest ./app
minikube image ls | findstr flask-app
```

**HPA showing `<unknown>` metrics:**
```bash
minikube addons enable metrics-server
# wait a minute then check
kubectl top pods
```

## Cleanup

```bash
kubectl delete -f k8s/
minikube stop
# or to delete everything: minikube delete
```

## Screenshots

| File | What it shows |
|------|--------------|
| `01-pods-services.png` | All pods running, services listed, PVC bound |
| `02-api-crud-test.png` | POST and GET requests working |
| `03-hpa-autoscaling.png` | HPA scaling pods from 2 to 4 under load |
| `04-db-persistence.png` | Data still there after deleting mongo-0 |
