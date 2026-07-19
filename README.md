# Fortel Stock Price Prediction

This repository contains a Flask stock forecasting app plus CI/CD and Kubernetes automation artifacts.

## Purpose
- Build a Docker image for the Flask app.
- Run a Jenkins pipeline that builds the image, scans it with Trivy, and pushes to Docker Hub.
- Optionally deploy to Kubernetes using the manifests in `k8s/`.
- Use GitHub webhooks to trigger Jenkins automatically.

---

## Prerequisites
- Docker installed on the Jenkins build agent.
- Jenkins installed and accessible.
- `ngrok` if your Jenkins server is local and not publicly reachable.
- A GitHub repository for this project.
- A Docker Hub account.
- Optional: `kubectl` and a Kubernetes cluster.

---

## Step 1: Configure Jenkins credentials

In Jenkins, create the following credentials:

1. `dockerhub-creds`
   - Type: Username with password
   - Username: your Docker Hub username
   - Password: your Docker Hub password or Docker Hub personal access token

2. `github-id` (optional)
   - Type: Username with password or Secret text
   - Use this if your Jenkins job needs GitHub checkout credentials for a private repo.

3. `kubeconfig` (optional)
   - Type: Secret file
   - Use this if you want Jenkins to apply Kubernetes manifests using `kubectl`.

---

## Step 2: Create the Jenkins pipeline job

Use one of these approaches:

### Option A: Pipeline job
1. In Jenkins, click **New Item**.
2. Enter a name and choose **Pipeline**.
3. Under **Pipeline**, choose **Pipeline script from SCM**.
4. Set SCM to **Git**, and enter the repository URL:
   - `https://github.com/rohan2800/fortel_stock-price-prediction.git`
5. Select credentials if needed (for `github-id`).
6. Set **Branch Specifier** to `*/main`.
7. Under **Build Triggers**, enable:
   - `GitHub hook trigger for GITScm polling`
8. Save the job.

### Option B: Multibranch Pipeline job
1. In Jenkins, click **New Item**.
2. Choose **Multibranch Pipeline**.
3. Add a **GitHub** branch source.
4. Provide repository URL and credentials if needed.
5. Save. A Multibranch Pipeline will discover branches automatically and can respond to webhooks.

---

## Step 3: Update the Jenkinsfile settings

Open `Jenkinsfile` and verify these values:

- `REGISTRY` should be your Docker Hub image path.
  - Example: `rohan2044/fortel-app`
- `IMAGE_TAG` is currently set to `${env.BUILD_ID}`.
- The pipeline uses Jenkins credential ID `dockerhub-creds`.

If you use a different credential ID, update the `withCredentials(...)` block accordingly.

---

## Step 4: Authenticate ngrok (for local Jenkins)

If Jenkins is running locally, GitHub cannot reach `http://localhost:9090` directly. Use `ngrok` to create a public tunnel.

### Install ngrok
- Download from https://ngrok.com/download
- Unzip the binary and add it to your PATH.

### Authenticate ngrok
1. Sign in at https://ngrok.com/
2. Copy your auth token from the dashboard.
3. Run:

```bash
ngrok config add-authtoken <YOUR_AUTH_TOKEN>
```

### Start the tunnel

```bash
ngrok http 9090
```

You will see output like:

```text
Forwarding                    http://abcd1234.ngrok.io -> http://localhost:9090
Forwarding                    https://abcd1234.ngrok.io -> http://localhost:9090
```

Use the HTTPS URL from the output.

---

## Step 5: Create the GitHub webhook

In GitHub:
1. Open the repository.
2. Go to **Settings** → **Webhooks**.
3. Click **Add webhook**.
4. Fill in:
   - Payload URL: `https://<your-ngrok-id>.ngrok.io/github-webhook/`
   - Content type: `application/json`
   - Secret: optional but recommended for verification.
   - Which events: select `Let me select individual events`, then `push` and `pull_request`.
5. Click **Add webhook**.

After adding, use **Recent Deliveries** to verify GitHub sends a `200` response.

---

## Step 6: Run the Jenkins pipeline

1. Make a small commit and push to GitHub.
2. GitHub should deliver a webhook to Jenkins.
3. Jenkins should start the pipeline automatically.
4. Verify the pipeline stages:
   - Checkout
   - Build
   - Scan
   - Test
   - Push

### What the pipeline does
- Builds a Docker image from `Dockerfile`.
- Scans the built image with Trivy for HIGH/CRITICAL vulnerabilities.
- Archives `trivy-report.json`.
- Pushes the image to Docker Hub.

---

## Step 7: Verify the image push

Check Docker Hub for the pushed image and tag:
- `https://hub.docker.com/r/rohan2044/fortel-app/tags`

Or run:

```bash
docker pull rohan2044/fortel-app:<TAG>
```

---

## Step 8: Optional Kubernetes deployment

If you want to deploy to Kubernetes, use the manifests in `k8s/`.

### Example commands

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/fortel-app -n default
```

### Notes
- Update the image name in `k8s/deployment.yaml` if you push a different tag.
- The deployment manifest includes health/readiness probe annotations and resource requests.
- You can also add a Jenkins deploy stage that uses the `kubeconfig` Jenkins secret.

---

## Troubleshooting

- If the webhook fails because GitHub cannot reach Jenkins, make sure ngrok is running and you use the HTTPS forwarding URL.
- If the pipeline fails in the `Scan` stage, check the archived `trivy-report.json`.
- If Docker push fails, verify `dockerhub-creds` and the `REGISTRY` format.
- If Git checkout fails, verify `github-id` credentials and repo access.

---

## Useful commands

### Local Docker build

```bash
docker build -t rohan2044/fortel-app:test .
```

### Local Docker run

```bash
docker run --rm -p 5000:5000 rohan2044/fortel-app:test
```

### Health checks

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
```

---

## Files of interest
- `Dockerfile` — multi-stage image build
- `.dockerignore` — excludes large model and generated files
- `Jenkinsfile` — Jenkins pipeline stages
- `k8s/deployment.yaml` — Kubernetes deployment manifest
- `k8s/service.yaml` — Kubernetes service manifest
- `README-CI-K8S.md` — shorter CI/K8s notes

If you want, I can also add a dedicated `JENKINS-SETUP.md` or expand the Kubernetes deployment section with a Jenkins deploy stage.
