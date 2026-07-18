pipeline {
  agent any
  environment {
    // Replace with your registry and credentials id in Jenkins
    REGISTRY = "rohan2044/fortel-app"
    IMAGE_TAG = "${env.BUILD_ID}"
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Build') {
      steps {
        script {
          dockerImage = docker.build("${REGISTRY}:${IMAGE_TAG}")
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
