pipeline {

    agent any

    environment {
    FRONTEND_IMAGE = "ticket-fe:latest"
    BACKEND_IMAGE  = "ticket-be:latest"
    COMPOSE_FILE   = "docker-compose.yml"
    NEXT_PUBLIC_API_URL="https://ticket-be.namanchaturvedi.com/api/v1"
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
                    cp "$TICKET_ENV_FILE" .env

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
                    sleep 5

                    docker ps

                    echo "Backend:"
                    docker inspect \
                        --format='{{.State.Status}}' \
                        ticket-be

                    echo "Frontend:"
                    docker inspect \
                        --format='{{.State.Status}}' \
                        ticket-fe
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

