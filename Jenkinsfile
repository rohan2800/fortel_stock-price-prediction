// Jenkins pipeline for building, scanning, pushing, and optionally deploying the Fortel Docker image.
// Webhook URL: https://<JENKINS_HOST>/github-webhook/
// Ensure you create Jenkins credentials for Docker Hub and kubeconfig if you want Kubernetes deployment.



pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(
            numToKeepStr: '20'
        ))
        timeout(time: 60, unit: 'MINUTES')
    }

    environment {
        IMAGE = 'rohan2044/fortel-app'
        KUBE_NAMESPACE = 'fortel'
        TRIVY_VERSION = '0.72.0'
        TMPDIR = '/var/lib/jenkins/tmp'
    }

    stages {

        // =========================================
        // 1. CHECKOUT SOURCE CODE
        // =========================================
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

                    echo "===== Git Status ====="
                    git status --short

                    echo "===== Build Information ====="
                    echo "Image: ${IMAGE}"
                    echo "Tag: ${IMAGE_TAG}"
                    echo "Workspace: ${WORKSPACE}"
                '''
            }
        }

        // =========================================
        // 2. BUILD DOCKER IMAGE
        // =========================================
        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    echo "===== Build Docker Image ====="

                    docker build \
                        --pull \
                        --tag "${IMAGE}:${IMAGE_TAG}" \
                        .

                    echo "===== Create Latest Tag ====="

                    docker tag \
                        "${IMAGE}:${IMAGE_TAG}" \
                        "${IMAGE}:latest"

                    echo "===== Verify Image Tags ====="

                    docker image inspect "${IMAGE}:${IMAGE_TAG}" >/dev/null
                    docker image inspect "${IMAGE}:latest" >/dev/null

                    docker images "${IMAGE}"
                '''
            }
        }

        // =========================================
        // 3. VALIDATE PYTHON APPLICATION
        // =========================================
        stage('Validate Application') {
            steps {
                sh '''
                    set -eu

                    echo "===== Python Syntax Validation ====="

                    docker run --rm \
                        --entrypoint python \
                        "${IMAGE}:${IMAGE_TAG}" \
                        -m compileall -q app.py forecast.py

                    echo "===== Docker Image Validation ====="

                    docker image inspect "${IMAGE}:${IMAGE_TAG}" \
                        --format 'Image ID: {{.Id}}'

                    echo "Application validation passed."
                '''
            }
        }

        // =========================================
        // 4. TRIVY SECURITY SCAN
        // =========================================
        stage('Trivy Security Scan') {
            steps {
                script {
                    int scanStatus = 0

                    try {
                        sh '''
                            set -eu

                            mkdir -p "${TMPDIR}"
                            chmod 700 "${TMPDIR}"

                            TRIVY_DIR="${TMPDIR}/trivy-jenkins-${BUILD_NUMBER}"
                            mkdir -p "${TRIVY_DIR}"
                            chmod 700 "${TRIVY_DIR}"

                            echo "===== Download Trivy ${TRIVY_VERSION} ====="

                            curl --fail --silent --show-error --location \
                                "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
                                --output "${TRIVY_DIR}/trivy.tar.gz"

                            tar -xzf "${TRIVY_DIR}/trivy.tar.gz" \
                                -C "${TRIVY_DIR}" trivy

                            chmod +x "${TRIVY_DIR}/trivy"

                            echo "===== Trivy Version ====="
                            "${TRIVY_DIR}/trivy" --version

                            echo "===== Scan Docker Image ====="

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
                        echo "Trivy scan reported failure or encountered an error: ${err}"
                    } finally {
                        archiveArtifacts(
                            artifacts: 'trivy-report.json',
                            allowEmptyArchive: true
                        )

                        sh '''
                            rm -rf "${TMPDIR}/trivy-jenkins-${BUILD_NUMBER}" \
                                || true
                        '''
                    }

                    if (scanStatus != 0) {
                        error(
                            'Trivy scan failed. Review the archived report and console output.'
                        )
                    }
                }
            }
        }

        // =========================================
        // 5. PUSH IMAGE TO DOCKER HUB
        // =========================================
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

                        echo "===== Verify Versioned Image ====="

                        docker image inspect "${IMAGE}:${IMAGE_TAG}" >/dev/null

                        echo "===== Ensure Latest Tag Exists ====="

                        docker tag \
                            "${IMAGE}:${IMAGE_TAG}" \
                            "${IMAGE}:latest"

                        echo "===== Push Versioned Image ====="

                        docker push "${IMAGE}:${IMAGE_TAG}"

                        echo "===== Push Latest Image ====="

                        docker push "${IMAGE}:latest"

                        echo "===== Docker Hub Push Completed ====="
                    '''
                }
            }
        }

        // =========================================
        // 6. DEPLOY TO KUBERNETES
        // =========================================
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

                        echo "===== Validate Cluster Access ====="
                        kubectl cluster-info
                        kubectl get nodes

                        echo "===== Apply Namespace ====="
                        kubectl apply -f k8s/namespace.yaml

                        echo "===== Apply Deployment and Service ====="
                        kubectl apply -f k8s/deployment.yaml
                        kubectl apply -f k8s/service.yaml

                        echo "===== Set Exact Versioned Image ====="
                        kubectl set image \
                            deployment/fortel-app \
                            fortel-app="${IMAGE}:${IMAGE_TAG}" \
                            --namespace="${KUBE_NAMESPACE}"

                        echo "===== Verify Deployment Image ====="
                        kubectl get deployment fortel-app \
                            --namespace="${KUBE_NAMESPACE}" \
                            -o jsonpath='{.spec.template.spec.containers[?(@.name=="fortel-app")].image}'

                        echo

                        echo "===== Wait for Rollout ====="

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
                                --tail=150 || true

                            exit 1
                        fi

                        echo "===== Final Deployment Status ====="

                        kubectl get deployment,pods,services \
                            --namespace="${KUBE_NAMESPACE}" -o wide

                        echo "===== Deployment Successful ====="
                    '''
                }
            }
        }
    }

    // =============================================
    // POST-BUILD ACTIONS
    // =============================================
    post {
        success {
            echo """
            =========================================
            FORTEL CI/CD PIPELINE SUCCESSFUL
            =========================================
            Build Number : ${env.BUILD_NUMBER}
            Docker Image : ${env.IMAGE}:${env.BUILD_NUMBER}
            Latest Image : ${env.IMAGE}:latest
            Namespace    : ${env.KUBE_NAMESPACE}
            =========================================
            """
        }

        failure {
            echo """
            =========================================
            FORTEL CI/CD PIPELINE FAILED
            =========================================
            Build Number : ${env.BUILD_NUMBER}
            Review the failed stage in the Jenkins
            console output before retrying.
            =========================================
            """
        }

        always {
            echo "Pipeline finished: ${currentBuild.currentResult}"
        }
    }
}
