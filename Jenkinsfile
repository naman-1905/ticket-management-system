pipeline {

    agent any

    environment {
        FRONTEND_IMAGE      = "ticket-fe:latest"
        BACKEND_IMAGE       = "ticket-be:latest"
        COMPOSE_FILE        = "docker-compose.yml"
        DOCKER_NETWORK      = "naman-private-network"
        NEXT_PUBLIC_API_URL = "https://ticket-be.namanchaturvedi.com/api/v1"
        FRONTEND_URL        = "https://ticket.namanchaturvedi.com"
        BACKEND_URL         = "https://ticket-be.namanchaturvedi.com"
        DEPLOY_HOST         = "192.168.1.38"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Backend') {
            steps {
                sh '''
                    docker build \
                        -t ${BACKEND_IMAGE} \
                        ./backend
                '''
            }
        }

        stage('Build Frontend') {
            steps {
                sh '''
                    docker build \
                        --build-arg NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL}" \
                        -t ${FRONTEND_IMAGE} \
                        ./frontend
                '''
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'ticket-env',
                        variable: 'TICKET_ENV_FILE'
                    )
                ]) {
                    sh '''
                        set -e

                        cp "$TICKET_ENV_FILE" .env

                        echo "=== ENV keys ==="
                        sed 's/=.*$/=<REDACTED>/' .env

                        echo "=== Ensuring Docker network exists ==="
                        docker network inspect ${DOCKER_NETWORK} >/dev/null 2>&1 \
                            || docker network create ${DOCKER_NETWORK}

                        echo "=== Deploying to ${DEPLOY_HOST} ==="
                        echo "Frontend: ${FRONTEND_URL}"
                        echo "Backend:  ${BACKEND_URL}"

                        docker compose \
                            -f ${COMPOSE_FILE} \
                            up -d \
                            --force-recreate

                        rm -f .env
                    '''
                }
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    set -e

                    sleep 10

                    echo "=== Containers ==="
                    docker ps

                    echo "=== Backend status ==="
                    BACKEND_STATUS=$(docker inspect \
                        --format='{{.State.Status}}' \
                        ticket-be)

                    echo "$BACKEND_STATUS"

                    if [ "$BACKEND_STATUS" != "running" ]; then
                        echo "Backend is not running."
                        docker logs --tail 100 ticket-be
                        exit 1
                    fi

                    echo "=== Frontend status ==="
                    FRONTEND_STATUS=$(docker inspect \
                        --format='{{.State.Status}}' \
                        ticket-fe)

                    echo "$FRONTEND_STATUS"

                    if [ "$FRONTEND_STATUS" != "running" ]; then
                        echo "Frontend is not running."
                        docker logs --tail 100 ticket-fe
                        exit 1
                    fi

                    echo "=== Deployment verification passed ==="
                '''
            }
        }
    }

    post {

        always {
            sh '''
                rm -f .env
                docker image prune -f
            '''
        }

        success {
            echo 'Deployment successful.'
        }

        failure {
            echo 'Deployment failed.'
        }
    }
}