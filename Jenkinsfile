// Jenkins pipeline for building, scanning, pushing, and optionally deploying the Fortel Docker image.
// Webhook URL: https://<JENKINS_HOST>/github-webhook/
// Ensure you create Jenkins credentials for Docker Hub and kubeconfig if you want Kubernetes deployment.


pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 60, unit: 'MINUTES')
    }

    environment {
        IMAGE = 'rohan2044/fortel-app'
        IMAGE_TAG = "${BUILD_NUMBER}"
        KUBE_NAMESPACE = 'fortel'
        TRIVY_VERSION = '0.72.0'
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm

                sh '''
                    set -eu
                    echo "Current commit:"
                    git rev-parse --short HEAD

                    echo "Repository status:"
                    git status --short
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building the Fortel application image...'

                sh '''
                    set -eu

                    docker build \
                        --pull \
                        -t "${IMAGE}:${IMAGE_TAG}" \
                        -t "${IMAGE}:latest" \
                        .
                '''

                echo 'Docker image build completed.'
            }
        }

        stage('Test') {
            steps {
                echo 'Checking Python source syntax...'

                sh '''
                    set -eu

                    docker run --rm \
                        --entrypoint python \
                        "${IMAGE}:${IMAGE_TAG}" \
                        -m compileall -q app.py forecast.py

                    docker image inspect "${IMAGE}:${IMAGE_TAG}" \
                        >/dev/null

                    echo "Python syntax and Docker image checks passed."
                '''
            }
        }

        stage('Security Scan - Trivy') {
            steps {
                echo 'Scanning the image for fixable HIGH and CRITICAL vulnerabilities...'

                sh '''
                    set -eu

                    TRIVY_DIR="/tmp/trivy-${BUILD_TAG}"
                    mkdir -p "$TRIVY_DIR"

                    curl -fsSL \
                        "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
                        -o "$TRIVY_DIR/trivy.tar.gz"

                    tar -xzf "$TRIVY_DIR/trivy.tar.gz" \
                        -C "$TRIVY_DIR" trivy

                    chmod +x "$TRIVY_DIR/trivy"

                    "$TRIVY_DIR/trivy" image \
                        --cache-dir "$WORKSPACE/.trivy-cache" \
                        --timeout 20m \
                        --scanners vuln \
                        --severity HIGH,CRITICAL \
                        --ignore-unfixed \
                        --format json \
                        --output trivy-report.json \
                        --exit-code 1 \
                        --no-progress \
                        "${IMAGE}:${IMAGE_TAG}"
                '''
            }

            post {
                always {
                    archiveArtifacts(
                        artifacts: 'trivy-report.json',
                        allowEmptyArchive: true
                    )
                }
            }
        }

        stage('Push to Docker Hub') {
            steps {
                echo 'Authenticating with Docker Hub and pushing images...'

                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        set -eu

                        trap 'docker logout >/dev/null 2>&1 || true' EXIT

                        printf '%s' "$DOCKER_PASS" |
                            docker login \
                                --username "$DOCKER_USER" \
                                --password-stdin

                        docker push "${IMAGE}:${IMAGE_TAG}"
                        docker push "${IMAGE}:latest"

                        echo "Both image tags were pushed successfully."
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo 'Deploying the image to the Fortel Kubernetes namespace...'

                withCredentials([
                    file(
                        credentialsId: 'kubeconfig',
                        variable: 'KUBECONFIG_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        export KUBECONFIG="$KUBECONFIG_FILE"

                        echo "Checking Kubernetes connectivity..."
                        kubectl cluster-info
                        kubectl get nodes

                        echo "Applying the namespace..."
                        kubectl apply -f k8s/namespace.yaml

                        echo "Preparing the deployment manifest..."
                        sed -E \
                            "s#(^[[:space:]]*image:[[:space:]]*).+#\\1docker.io/${IMAGE}:${IMAGE_TAG}#" \
                            k8s/deployment.yaml \
                            > "$WORKSPACE/deployment-ci.yaml"

                        echo "Applying Kubernetes resources..."
                        kubectl apply -f "$WORKSPACE/deployment-ci.yaml"
                        kubectl apply -f k8s/service.yaml

                        echo "Waiting for the deployment rollout..."
                        if ! kubectl rollout status \
                            deployment/fortel-app \
                            -n "$KUBE_NAMESPACE" \
                            --timeout=300s; then

                            echo "Deployment rollout failed. Collecting diagnostics..."

                            kubectl get pods \
                                -n "$KUBE_NAMESPACE" -o wide || true

                            kubectl describe deployment/fortel-app \
                                -n "$KUBE_NAMESPACE" || true

                            kubectl get events \
                                -n "$KUBE_NAMESPACE" \
                                --sort-by=.lastTimestamp || true

                            exit 1
                        fi

                        echo "Deployment completed successfully."

                        kubectl get deployment,service \
                            -n "$KUBE_NAMESPACE"

                        kubectl get pods \
                            -n "$KUBE_NAMESPACE" -o wide
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Fortel pipeline completed successfully.'
            echo 'Docker image was scanned, pushed, and deployed.'
        }

        failure {
            echo 'FAILURE: The pipeline failed. Check the failed stage logs.'
        }

        always {
            echo 'Pipeline execution finished.'
        }
    }
}
