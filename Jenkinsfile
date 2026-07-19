// Jenkins pipeline for building, scanning, pushing, and optionally deploying the Fortel Docker image.
// Webhook URL: https://<JENKINS_HOST>/github-webhook/
// Ensure you create Jenkins credentials for Docker Hub and kubeconfig if you want Kubernetes deployment.

pipeline {
  agent any
  environment {
    // Replace with your registry and credentials id in Jenkins
    // `dockerhub-creds` should be a Jenkins credential of type "Username with password".
    REGISTRY = "rohan2044/fortel-app"
    IMAGE_TAG = "${env.BUILD_ID}"
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
        script {
          def dockerImage = docker.build("${REGISTRY}:${IMAGE_TAG}")
        }
      }
    }
    stage('Scan') {
      steps {
        script {
          sh '''
            mkdir -p /tmp/trivy
            curl -sfL https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz -o /tmp/trivy/trivy.tar.gz
            tar xzf /tmp/trivy/trivy.tar.gz -C /tmp/trivy
            chmod +x /tmp/trivy/trivy
            /tmp/trivy/trivy image --severity HIGH,CRITICAL --format json --output trivy-report.json --no-progress ${REGISTRY}:${IMAGE_TAG} || true
            /tmp/trivy/trivy image --severity HIGH,CRITICAL --no-progress ${REGISTRY}:${IMAGE_TAG} || true
          '''
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
              export KUBECONFIG="$KUBECONFIG_FILE"
              kubectl apply -f k8s/namespace.yaml
              kubectl apply -f k8s/deployment.yaml -n ${KUBE_NAMESPACE}
              kubectl apply -f k8s/service.yaml -n ${KUBE_NAMESPACE}
              kubectl set image deployment/fortel-app fortel=${REGISTRY}:${IMAGE_TAG} -n ${KUBE_NAMESPACE} --record
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
