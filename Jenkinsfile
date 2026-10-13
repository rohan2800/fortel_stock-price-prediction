// Jenkins pipeline for building, scanning, pushing, and optionally deploying the Fortel Docker image.
// Webhook URL: https://<JENKINS_HOST>/github-webhook/
// Ensure you create Jenkins credentials for Docker Hub and kubeconfig if you want Kubernetes deployment.

pipeline {
  agent any
  environment {
    // Replace with your registry and credentials id in Jenkins
    // `dockerhub-creds` should be a Jenkins credential of type "Username with password".
    REGISTRY = "rohan2044/fortel-app"
    // Unique per build, so every deploy has a new image tag and Kubernetes actually rolls out the change.
    IMAGE_TAG = "${env.BUILD_NUMBER}"
    TRIVY_VERSION = "0.72.0"
    KUBE_CONFIG_CREDENTIAL_ID = 'kubeconfig'
    KUBE_NAMESPACE = 'fortel'
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Build') {
      steps {
        sh '''
            set -e
            docker build -t ${REGISTRY}:${IMAGE_TAG} -t ${REGISTRY}:latest .
        '''
      }
    }
    stage('Scan') {
      steps {
        sh '''
          mkdir -p /tmp/trivy
          curl -sfL https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz -o /tmp/trivy/trivy.tar.gz
          tar xzf /tmp/trivy/trivy.tar.gz -C /tmp/trivy
          chmod +x /tmp/trivy/trivy
          # Full JSON report for archiving (never fails the build on its own)
          /tmp/trivy/trivy image --severity HIGH,CRITICAL --format json --output trivy-report.json --no-progress ${REGISTRY}:${IMAGE_TAG} || true
          # Gate: fail the build on fixable HIGH/CRITICAL vulnerabilities
          /tmp/trivy/trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --no-progress ${REGISTRY}:${IMAGE_TAG}
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
        }
      }
    }
    stage('Test') {
      steps {
        echo 'No automated tests configured. Add unit tests and run them here.'
      }
    }
    stage('Push') {
      steps {
        script {
          // Requires Jenkins credentials id 'dockerhub-creds' (username/password)
          withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKERHUB_USER', passwordVariable: 'DOCKERHUB_PASS')]) {
            sh 'echo $DOCKERHUB_PASS | docker login -u $DOCKERHUB_USER --password-stdin'
            sh "docker push ${REGISTRY}:${IMAGE_TAG}"
            sh "docker push ${REGISTRY}:latest"
          }
        }
      }
    }
    stage('Deploy') {
      steps {
        script {
          // Requires Jenkins secret file credential 'kubeconfig'
          withCredentials([file(credentialsId: env.KUBE_CONFIG_CREDENTIAL_ID, variable: 'KUBECONFIG_FILE')]) {
            sh '''
              set -e
              export KUBECONFIG="$KUBECONFIG_FILE"
              # Point the manifest at this build's versioned image so `apply` triggers a rollout
              sed -i "s|image: .*fortel-app:.*|image: docker.io/${REGISTRY}:${IMAGE_TAG}|" k8s/deployment.yaml
              kubectl apply -f k8s/namespace.yaml
              kubectl apply -f k8s/deployment.yaml -n ${KUBE_NAMESPACE}
              kubectl apply -f k8s/service.yaml -n ${KUBE_NAMESPACE}
              kubectl rollout status deployment/fortel-app -n ${KUBE_NAMESPACE} --timeout=300s
            '''
          }
        }
      }
    }
  }
  post {
    always {
      cleanWs()
    }
  }
}
