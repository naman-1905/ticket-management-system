pipeline {
    agent any

    parameters {
        choice(name: 'PIPELINE_TARGET', choices: ['frontend', 'backend', 'both'], description: 'Choose which application to build and deploy')
    }

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
            when { expression { params.PIPELINE_TARGET != 'frontend' } }
            steps {
                sh '''
                    docker compose config --quiet
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    if [ "${PIPELINE_TARGET}" = "frontend" ]; then
                        docker compose build frontend
                    elif [ "${PIPELINE_TARGET}" = "backend" ]; then
                        docker compose build api
                    else
                        docker compose build api frontend
                    fi
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    if [ "${PIPELINE_TARGET}" = "frontend" ]; then
                        docker compose up -d --force-recreate frontend
                    elif [ "${PIPELINE_TARGET}" = "backend" ]; then
                        docker compose run --rm api alembic upgrade head
                        docker compose up -d --force-recreate api
                    else
                        docker compose run --rm api alembic upgrade head
                        docker compose up -d --force-recreate api frontend
                    fi
                '''
            }
        }

        stage('Health Check') {
            when { expression { params.PIPELINE_TARGET != 'frontend' } }
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
                    echo "Ticket Management ${params.PIPELINE_TARGET} deployed successfully"
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
