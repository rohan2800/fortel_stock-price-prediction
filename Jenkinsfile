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
        KUBE_NAMESPACE = 'fortel'
        TRIVY_VERSION = '0.72.0'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm

                sh '''
                    set -eu

                    echo "===== Git Information ====="
                    git log -1 --oneline
                    git status --short
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    IMAGE_TAG="${BUILD_NUMBER}"

                    echo "===== Building Docker Image ====="
                    echo "Image: ${IMAGE}:${IMAGE_TAG}"

                    docker build --pull \
                        -t "${IMAGE}:${IMAGE_TAG}" \
                        -t "${IMAGE}:latest" \
                        .
                '''
            }
        }

        stage('Validate Application Image') {
            steps {
                sh '''
                    set -eu

                    IMAGE_TAG="${BUILD_NUMBER}"

                    echo "===== Validating Python Syntax ====="

                    docker run --rm \
                        --entrypoint python \
                        "${IMAGE}:${IMAGE_TAG}" \
                        -m compileall -q app.py forecast.py

                    echo "===== Checking Image Metadata ====="

                    docker image inspect \
                        "${IMAGE}:${IMAGE_TAG}" \
                        --format 'Image ID: {{.Id}}'

                    echo "Application image validation passed."
                '''
            }
        }

        stage('Security Scan - Trivy') {
            steps {
                sh '''
                    set -eu

                    # Use the larger Jenkins filesystem instead of /tmp.
                    export TMPDIR=/var/lib/jenkins/tmp

                    IMAGE_TAG="${BUILD_NUMBER}"
                    TRIVY_DIR="${TMPDIR}/trivy-jenkins-${BUILD_NUMBER}"

                    mkdir -p "${TRIVY_DIR}"

                    echo "===== Trivy Security Scan ====="
                    echo "Temporary directory: ${TMPDIR}"
                    echo "Image: ${IMAGE}:${IMAGE_TAG}"

                    # Download a pinned Trivy release.
                    curl -fsSL \
                        "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
                        -o "${TRIVY_DIR}/trivy.tar.gz"

                    tar -xzf "${TRIVY_DIR}/trivy.tar.gz" \
                        -C "${TRIVY_DIR}" trivy

                    chmod +x "${TRIVY_DIR}/trivy"

                    # Save a JSON report even if the scan finds vulnerabilities.
                    set +e
                    "${TRIVY_DIR}/trivy" image \
                        --cache-dir "${WORKSPACE}/.trivy-cache" \
                        --timeout 20m \
                        --scanners vuln \
                        --severity HIGH,CRITICAL \
                        --ignore-unfixed \
                        --format json \
                        --output "${WORKSPACE}/trivy-report.json" \
                        --exit-code 1 \
                        --no-progress \
                        "${IMAGE}:${IMAGE_TAG}"
                    SCAN_EXIT_CODE=$?
                    set -e

                    if [ -f "${WORKSPACE}/trivy-report.json" ]; then
                        echo "Trivy JSON report generated."
                    else
                        echo "ERROR: Trivy did not generate a report."
                        exit 2
                    fi

                    if [ "${SCAN_EXIT_CODE}" -ne 0 ]; then
                        echo "ERROR: Trivy scan failed or detected HIGH/CRITICAL vulnerabilities."
                        exit "${SCAN_EXIT_CODE}"
                    fi

                    echo "Trivy scan passed."
                '''
            }
            post {
                always {
                    archiveArtifacts(
                        artifacts: 'trivy-report.json',
                        allowEmptyArchive: true,
                        fingerprint: true
                    )

                    sh '''
                        rm -rf "/var/lib/jenkins/tmp/trivy-jenkins-${BUILD_NUMBER}" || true
                    '''
                }
            }
        }

        stage('Push Image to Docker Hub') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKERHUB_USERNAME',
                        passwordVariable: 'DOCKERHUB_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu

                        IMAGE_TAG="${BUILD_NUMBER}"

                        echo "===== Docker Hub Login ====="

                        trap 'docker logout || true' EXIT

                        printf '%s' "${DOCKERHUB_PASSWORD}" |
                            docker login \
                                --username "${DOCKERHUB_USERNAME}" \
                                --password-stdin

                        echo "===== Pushing Versioned Image ====="
                        docker push "${IMAGE}:${IMAGE_TAG}"

                        echo "===== Pushing Latest Image ====="
                        docker push "${IMAGE}:latest"

                        echo "Docker image push completed."
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'kubeconfig',
                        variable: 'KUBECONFIG_FILE'
                    )
                ]) {
                    sh '''
                        set -eu

                        IMAGE_TAG="${BUILD_NUMBER}"
                        export KUBECONFIG="${KUBECONFIG_FILE}"

                        echo "===== Kubernetes Context ====="
                        kubectl config current-context
                        kubectl cluster-info

                        echo "===== Apply Namespace ====="
                        kubectl apply -f k8s/namespace.yaml

                        echo "===== Update Deployment Image ====="
                        kubectl set image \
                            deployment/fortel-app \
                            fortel-app="${IMAGE}:${IMAGE_TAG}" \
                            --namespace="${KUBE_NAMESPACE}"

                        echo "===== Apply Kubernetes Manifests ====="
                        kubectl apply \
                            -f k8s/deployment.yaml \
                            -f k8s/service.yaml \
                            --namespace="${KUBE_NAMESPACE}"

                        echo "===== Wait for Deployment Rollout ====="

                        if ! kubectl rollout status \
                            deployment/fortel-app \
                            --namespace="${KUBE_NAMESPACE}" \
                            --timeout=300s; then

                            echo "===== Deployment Diagnostics ====="

                            kubectl get deployments,pods,services \
                                --namespace="${KUBE_NAMESPACE}" -o wide || true

                            kubectl describe deployment fortel-app \
                                --namespace="${KUBE_NAMESPACE}" || true

                            kubectl get events \
                                --namespace="${KUBE_NAMESPACE}" \
                                --sort-by='.lastTimestamp' || true

                            kubectl logs \
                                deployment/fortel-app \
                                --namespace="${KUBE_NAMESPACE}" \
                                --all-containers=true \
                                --tail=100 || true

                            exit 1
                        fi

                        echo "===== Final Kubernetes Status ====="

                        kubectl get deployments,pods,services \
                            --namespace="${KUBE_NAMESPACE}" -o wide

                        echo "Kubernetes deployment completed."
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Build, validation, security scan, image push, and Kubernetes deployment completed.'
        }

        failure {
            echo 'FAILURE: Pipeline failed. Review the stage logs and archived Trivy report.'
        }

        always {
            echo 'Pipeline execution finished.'
        }
    }
}
