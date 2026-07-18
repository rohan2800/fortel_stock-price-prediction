This repository was updated with CI/CD and Kubernetes manifests by the assistant.

Files added:
- Dockerfile
- .dockerignore
- Jenkinsfile (Declarative pipeline, uses Jenkins credential id `dockerhub-creds` — update as needed)
- k8s/deployment.yaml
- k8s/service.yaml

Next steps:
1. In Jenkins, create credentials (username/password) with id `dockerhub-creds` or update Jenkinsfile accordingly.
2. Update the REGISTRY value in Jenkinsfile to point to your container registry (Docker Hub or GHCR).
3. Build the Jenkins pipeline to build and push the image.
4. Apply the k8s manifests to your cluster (update image tag to match the pushed image):
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml

If you want, I can also create a GitHub Actions workflow instead of Jenkins, or prepare a Helm chart for the Kubernetes deployment.
