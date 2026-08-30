pipeline {

    agent any

    environment {
        FRONTEND_IMAGE = "ticket-fe:latest"
        BACKEND_IMAGE  = "ticket-be:latest"
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
                withCredentials([
                    string(
                        credentialsId: 'ticket-env',
                        variable: 'TICKET_ENV'
                    )
                ]) {
                    sh '''
                        NEXT_PUBLIC_API_URL=$(printf '%s\\n' "$TICKET_ENV" | \
                            sed -n 's/^NEXT_PUBLIC_API_URL=//p')

                        docker build \
                            --build-arg NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" \
                            -t ${FRONTEND_IMAGE} \
                            ./frontend
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'ticket-env',
                        variable: 'TICKET_ENV'
                    )
                ]) {
                    sh '''
                        printf '%s\\n' "$TICKET_ENV" > .env

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
            rm -f .env
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