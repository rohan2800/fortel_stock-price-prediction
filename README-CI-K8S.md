This repository was updated with CI/CD and Kubernetes manifests by the assistant.

Files added:
- Dockerfile
- .dockerignore
- Jenkinsfile (Declarative pipeline, uses Jenkins credential id `dockerhub-creds` — update as needed)
- k8s/deployment.yaml
- k8s/service.yaml

Jenkins setup overview:
1. Create Jenkins credentials:
   - `dockerhub-creds`: type "Username with password" for Docker Hub login.
   - `github-id`: GitHub token credential used for repository checkout if needed.
   - `kubeconfig`: secret file containing your kubeconfig if you add Kubernetes deployment steps.
2. Update the `REGISTRY` value in `Jenkinsfile` to point to your Docker image registry.
   - Example for Docker Hub: `rohan2044/fortel-app`
   - Example for GitHub Container Registry: `ghcr.io/<owner>/fortel-app`
3. Configure a Jenkins job:
   - Use a Pipeline job or a Multibranch Pipeline and point it at this repository.
   - Ensure the `Jenkinsfile` from this repo is used.
   - For a Pipeline job, enable "GitHub hook trigger for GITScm polling".
4. Add a GitHub webhook:
   - Payload URL: `https://<JENKINS_HOST>/github-webhook/`
   - Content type: `application/json`
   - Events: `push` and `pull_request`
   - Secret: optional, but recommended for verification.
5. Pipeline behavior:
   - The current `Jenkinsfile` builds the Docker image, scans it with Trivy, archives the scan report, and then pushes the image.
   - If you want Kubernetes deployment, update `k8s/deployment.yaml` image references or use `kubectl set image` from Jenkins.
   - The Jenkinsfile can also deploy to Kubernetes automatically if the `kubeconfig` secret is available.
   - The Kubernetes manifests use a dedicated namespace named `fortel` instead of the default namespace.
6. Test the integration:
   - Push a commit to GitHub and verify Jenkins is triggered by the webhook.
   - Confirm the pipeline stages complete and the image is pushed successfully.

If you want, I can also create a dedicated Jenkins setup README with more details, or add a GitHub Actions workflow instead of Jenkins.
