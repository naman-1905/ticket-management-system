pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        COMPOSE_PROJECT_NAME = 'ticket-management-system'
        SERVICE_NAME = 'api'
        CONTAINER_NAME = 'ticketing-backend'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Prepare Environment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'Ticket-Backend-Env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    sh '''
                        cp "$ENV_FILE" .env
                        chmod 600 .env
                    '''
                }
            }
        }

        stage('Validate Compose') {
            steps {
                sh '''
                    docker compose config --quiet
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    docker compose build ${SERVICE_NAME}
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker compose up -d \
                        --force-recreate \
                        ${SERVICE_NAME}
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    echo "Waiting for backend to start..."

                    ATTEMPT=1

                    while [ "$ATTEMPT" -le 12 ]; do
                        echo "Health check attempt $ATTEMPT/12"

                        if docker exec ${CONTAINER_NAME} \
                            python -c "import urllib.request; response = urllib.request.urlopen('http://127.0.0.1:8000/health/db', timeout=5); assert response.status == 200"; then

                            echo "Backend health check passed"
                            exit 0
                        fi

                        ATTEMPT=$((ATTEMPT + 1))
                        sleep 5
                    done

                    echo "Backend health check failed"

                    echo "=== Container status ==="
                    docker ps -a --filter "name=${CONTAINER_NAME}"

                    echo "=== Backend logs ==="
                    docker logs --tail 100 ${CONTAINER_NAME} || true

                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'Ticket Management Backend deployed successfully'
        }

        failure {
            echo 'Ticket Management Backend deployment failed'
        }

        always {
            sh '''
                rm -f .env
            '''
        }
    }
}