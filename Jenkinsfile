// Jenkins pipeline for building, scanning, and pushing the Fortel Docker image.
// To trigger builds automatically, configure a GitHub webhook to Jenkins at:
//   https://<JENKINS_HOST>/github-webhook/
// Then enable "GitHub hook trigger for GITScm polling" in the Jenkins job.

pipeline {
  agent any
  environment {
    // Replace with your registry and credentials id in Jenkins
    // `dockerhub-creds` should be a Jenkins credential of type "Username with password".
    REGISTRY = "rohan2044/fortel-app"
    IMAGE_TAG = "${env.BUILD_ID}"
    TRIVY_VERSION = "0.72.0"
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
  }
  post {
    always {
      cleanWs()
    }
  }
}
