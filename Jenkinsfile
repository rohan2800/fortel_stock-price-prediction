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
        TMPDIR = '/var/lib/jenkins/tmp'
    }

    stages {

        // 1. CHECKOUT
        stage('Checkout') {
            steps {
                checkout scm

                script {
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}"
                }

                sh '''
                    set -eu

                    echo "===== Git Commit ====="
                    git log -1 --oneline

                    echo "===== Build Information ====="
                    echo "Image: ${IMAGE}"
                    echo "Tag: ${IMAGE_TAG}"
                '''
            }
        }

        // 2. BUILD DOCKER IMAGE
        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    echo "===== Build Versioned Image ====="

                    docker build --pull \
                        -t "${IMAGE}:${IMAGE_TAG}" .

                    echo "===== Tag Image as Latest ====="

                    docker tag \
                        "${IMAGE}:${IMAGE_TAG}" \
                        "${IMAGE}:latest"

                    docker image inspect "${IMAGE}:${IMAGE_TAG}" >/dev/null
                    docker image inspect "${IMAGE}:latest" >/dev/null

                    docker images "${IMAGE}"
                '''
            }
        }

        // 3. PYTHON VALIDATION
        stage('Validate Application') {
            steps {
                sh '''
                    set -eu

                    echo "===== Validate Python Syntax ====="

                    docker run --rm \
                        --entrypoint python \
                        "${IMAGE}:${IMAGE_TAG}" \
                        -m compileall -q app.py forecast.py

                    echo "===== Validate Image ====="

                    docker image inspect "${IMAGE}:${IMAGE_TAG}" \
                        --format 'Image ID: {{.Id}}'

                    echo "Application validation passed."
                '''
            }
        }

        // 4. TRIVY SECURITY SCAN
        stage('Trivy Security Scan') {
            steps {
                script {
                    int scanStatus = 0

                    try {
                        sh '''
                            set -eu

                            mkdir -p "${TMPDIR}"
                            chmod 700 "${TMPDIR}"

                            TRIVY_DIR="${TMPDIR}/trivy-${BUILD_NUMBER}"
                            mkdir -p "${TRIVY_DIR}"
                            chmod 700 "${TRIVY_DIR}"

                            trap 'rm -rf "${TRIVY_DIR}"' EXIT

                            echo "===== Download Trivy ====="

                            curl --fail --silent --show-error --location \
                                "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
                                -o "${TRIVY_DIR}/trivy.tar.gz"

                            tar -xzf "${TRIVY_DIR}/trivy.tar.gz" \
                                -C "${TRIVY_DIR}" trivy

                            chmod +x "${TRIVY_DIR}/trivy"

                            echo "===== Trivy Version ====="
                            "${TRIVY_DIR}/trivy" --version

                            echo "===== Scan Image ====="

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
                        '''
                    } catch (err) {
                        scanStatus = 1
                        echo "Security scan failed: ${err}"
                    } finally {
                        archiveArtifacts(
                            artifacts: 'trivy-report.json',
                            allowEmptyArchive: true
                        )
                    }

                    if (scanStatus != 0) {
                        error('Trivy scan failed. Check the report and console logs.')
                    }
                }
            }
        }

        // 5. PUSH TO DOCKER HUB
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

                        echo "===== Docker Hub Login ====="

                        printf '%s' "$DOCKERHUB_PASSWORD" |
                            docker login \
                                --username "$DOCKERHUB_USERNAME" \
                                --password-stdin

                        trap 'docker logout >/dev/null 2>&1 || true' EXIT

                        echo "===== Push Versioned Image ====="
                        docker push "${IMAGE}:${IMAGE_TAG}"

                        echo "===== Push Latest Image ====="
                        docker push "${IMAGE}:latest"

                        echo "Docker Hub push completed."
                    '''
                }
            }
        }

        // 6. DEPLOY TO KUBERNETES
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

                        export KUBECONFIG="${KUBECONFIG_FILE}"

                        echo "===== Kubernetes Context ====="
                        kubectl config current-context

                        echo "===== Validate Cluster ====="
                        kubectl cluster-info
                        kubectl get nodes

                        echo "===== Apply Namespace ====="
                        kubectl apply -f k8s/namespace.yaml

                        echo "===== Apply Deployment and Service ====="
                        kubectl apply -f k8s/deployment.yaml
                        kubectl apply -f k8s/service.yaml

                        echo "===== Find Actual Container Name ====="

                        CONTAINER_NAME="$(
                            kubectl get deployment fortel-app \
                                -n "${KUBE_NAMESPACE}" \
                                -o jsonpath='{.spec.template.spec.containers[0].name}'
                        )"

                        if [ -z "${CONTAINER_NAME}" ]; then
                            echo "ERROR: No container found in deployment fortel-app."
                            exit 1
                        fi

                        echo "Container name: ${CONTAINER_NAME}"

                        echo "===== Update Versioned Image ====="

                        kubectl set image \
                            deployment/fortel-app \
                            "${CONTAINER_NAME}=${IMAGE}:${IMAGE_TAG}" \
                            -n "${KUBE_NAMESPACE}"

                        echo "===== Verify Configured Image ====="

                        ACTUAL_IMAGE="$(
                            kubectl get deployment fortel-app \
                                -n "${KUBE_NAMESPACE}" \
                                -o jsonpath='{.spec.template.spec.containers[0].image}'
                        )"

                        echo "Expected image: ${IMAGE}:${IMAGE_TAG}"
                        echo "Actual image:   ${ACTUAL_IMAGE}"

                        if [ "${ACTUAL_IMAGE}" != "${IMAGE}:${IMAGE_TAG}" ]; then
                            echo "ERROR: Deployment image does not match the build tag."
                            exit 1
                        fi

                        echo "===== Wait for Rollout ====="

                        if ! kubectl rollout status \
                            deployment/fortel-app \
                            -n "${KUBE_NAMESPACE}" \
                            --timeout=300s; then

                            echo "===== Deployment Diagnostics ====="

                            kubectl get deployments,pods,services \
                                -n "${KUBE_NAMESPACE}" -o wide || true

                            kubectl describe deployment fortel-app \
                                -n "${KUBE_NAMESPACE}" || true

                            kubectl get events \
                                -n "${KUBE_NAMESPACE}" \
                                --sort-by='.lastTimestamp' || true

                            kubectl logs deployment/fortel-app \
                                -n "${KUBE_NAMESPACE}" \
                                --all-containers=true \
                                --tail=150 || true

                            exit 1
                        fi

                        echo "===== Final Deployment Status ====="

                        kubectl get deployment,pods,services \
                            -n "${KUBE_NAMESPACE}" -o wide

                        echo "===== Deployment Successful ====="
                    '''
                }
            }
        }
    }

    post {
        success {
            echo """
            ========================================
            FORTEL CI/CD PIPELINE SUCCESSFUL
            ========================================
            Build Number : ${env.BUILD_NUMBER}
            Image        : ${env.IMAGE}:${env.BUILD_NUMBER}
            Namespace    : ${env.KUBE_NAMESPACE}
            ========================================
            """
        }

        failure {
            echo """
            ========================================
            FORTEL CI/CD PIPELINE FAILED
            ========================================
            Build Number : ${env.BUILD_NUMBER}
            Check the failed stage in the console.
            ========================================
            """
        }

        always {
            echo "Pipeline result: ${currentBuild.currentResult}"
        }
    }
}
