pipeline {

    agent any

    environment {
        FRONTEND_IMAGE = "ticket-frontend:latest"
        BACKEND_IMAGE  = "ticket-backend:latest"
        COMPOSE_FILE   = "docker-compose.yml"
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
                        --build-arg NEXT_PUBLIC_API_URL=https://ticket-api.namanchaturvedi.com/api/v1 \
                        -t ${FRONTEND_IMAGE} \
                        ./frontend
                '''
            }
        }

        stage('Stop Existing Containers') {
            steps {
                sh '''
                    docker compose -f ${COMPOSE_FILE} down
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker compose -f ${COMPOSE_FILE} up -d
                '''
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    sleep 5

                    docker ps

                    echo "Backend:"
                    docker inspect --format='{{.State.Status}}' ticket-backend

                    echo "Frontend:"
                    docker inspect --format='{{.State.Status}}' ticket-frontend

                    echo "Cloudflared:"
                    docker inspect --format='{{.State.Status}}' ticket-cloudflared
                '''
            }
        }
    }

    post {

        success {
            echo 'Deployment successful.'
        }

        failure {
            echo 'Deployment failed.'
        }

        always {
            sh '''
                docker image prune -f
            '''
        }
    }
}