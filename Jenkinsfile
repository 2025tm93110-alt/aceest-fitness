// Jenkins BUILD stage: pulls latest code from GitHub and performs a clean build.
// Requires: Docker available on the agent (Python is NOT required on the agent).
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        IMAGE = "aceest-fitness"
        TAG   = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                // Fresh workspace => clean build every time
                deleteDir()
                checkout scm
            }
        }

        stage('Build Test Image') {
            steps {
                sh 'docker build --no-cache --target test -t ${IMAGE}:test-${TAG} .'
            }
        }

        stage('Lint & Unit Tests (in container)') {
            steps {
                sh 'docker run --rm ${IMAGE}:test-${TAG} sh -c "flake8 . && pytest"'
            }
        }

        stage('Build Runtime Image') {
            steps {
                sh 'docker build --target runtime -t ${IMAGE}:${TAG} .'
            }
        }

        stage('Smoke Test') {
            steps {
                // Probe from INSIDE the container: works whether Jenkins runs on the VM
                // directly or in its own container (published ports would not be reachable).
                sh '''
                    docker run -d --name aceest-smoke-${TAG} ${IMAGE}:${TAG}
                    for i in $(seq 1 15); do
                        if docker exec aceest-smoke-${TAG} python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:5000/health').read().decode())"; then
                            exit 0
                        fi
                        sleep 1
                    done
                    docker logs aceest-smoke-${TAG}
                    exit 1
                '''
            }
        }
    }

    post {
        always {
            sh 'docker rm -f aceest-smoke-${TAG} || true'
        }
        success { echo "BUILD SUCCESS: ${IMAGE}:${TAG}" }
        failure { echo "BUILD FAILED - check stage logs above" }
    }
}
