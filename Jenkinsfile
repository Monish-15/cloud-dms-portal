// Jenkinsfile -- Secure Document Management Portal
// Declarative CI/CD Pipeline for GitHub -> Jenkins -> Azure App Service
// IMPORTANT: This pipeline requires the following Jenkins credentials:
//   AZURE_CLIENT_ID       : Jenkins service principal App ID
//   AZURE_CLIENT_SECRET   : Jenkins service principal secret (Secret Text)
//   AZURE_TENANT_ID       : Azure AD tenant ID
//   AZURE_SUBSCRIPTION_ID : Target subscription ID
//   FLASK_SECRET_KEY      : Application secret key (Secret Text)
// The application Managed Identity is separate and configured by Terraform.

pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '15'))
        timeout(time: 45, unit: 'MINUTES')
        timestamps()
    }

    environment {
        PYTHON_BIN     = 'python3'
        VENV_DIR       = '.venv'
        TERRAFORM_DIR  = 'terraform'
        APP_PREFIX     = 'dmsportal'
        AZURE_REGION   = 'eastus'
        TF_AUTO_APPLY  = 'false'
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm
                sh 'git log --oneline -5'
            }
        }

        stage('Python Environment') {
            steps {
                echo 'Creating Python virtual environment...'
                sh """
                    ${PYTHON_BIN} -m venv ${VENV_DIR}
                    ${VENV_DIR}/bin/pip install --upgrade pip
                    ${VENV_DIR}/bin/pip install -r requirements.txt -r requirements-dev.txt
                """
            }
        }

        stage('Lint: Ruff') {
            steps {
                echo 'Running Ruff linter...'
                sh "${VENV_DIR}/bin/ruff check app/ tests/ scripts/"
            }
            post {
                failure { echo 'Linting failed. Blocking deployment.' }
            }
        }

        stage('Tests: Pytest') {
            steps {
                echo 'Running pytest with coverage...'
                sh """
                    mkdir -p reports
                    ${VENV_DIR}/bin/pytest \
                        --cov=app \
                        --cov-report=xml:reports/coverage.xml \
                        --cov-report=html:reports/htmlcov \
                        --junitxml=reports/junit.xml \
                        -v
                """
            }
            post {
                always {
                    junit 'reports/junit.xml'
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports/htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
                failure { echo 'Tests failed. Blocking deployment.' }
            }
        }

        stage('Security: Bandit') {
            steps {
                echo 'Running Bandit security scanner...'
                sh """
                    mkdir -p reports
                    ${VENV_DIR}/bin/bandit -r app/ -ll -f json -o reports/bandit-report.json || true
                    ${VENV_DIR}/bin/bandit -r app/ -ll
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/bandit-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building Docker image...'
                sh """
                    docker build -t secure-doc-portal:${BUILD_NUMBER} -t secure-doc-portal:latest .
                    docker images secure-doc-portal
                """
            }
        }

        stage('Terraform: Format') {
            steps {
                echo 'Checking Terraform formatting...'
                sh "terraform -chdir=${TERRAFORM_DIR} fmt -check -recursive"
            }
            post {
                failure { echo 'Terraform fmt check failed. Run: terraform fmt -recursive' }
            }
        }

        stage('Terraform: Validate') {
            steps {
                echo 'Validating Terraform configuration...'
                sh """
                    terraform -chdir=${TERRAFORM_DIR} init -backend=false
                    terraform -chdir=${TERRAFORM_DIR} validate
                """
            }
            post {
                failure { echo 'Terraform validation failed. Blocking deployment.' }
            }
        }

        stage('Terraform: Plan') {
            when { branch 'main' }
            steps {
                echo 'Running Terraform plan (preview only)...'
                withCredentials([
                    string(credentialsId: 'AZURE_CLIENT_ID',       variable: 'ARM_CLIENT_ID'),
                    string(credentialsId: 'AZURE_CLIENT_SECRET',    variable: 'ARM_CLIENT_SECRET'),
                    string(credentialsId: 'AZURE_TENANT_ID',        variable: 'ARM_TENANT_ID'),
                    string(credentialsId: 'AZURE_SUBSCRIPTION_ID',  variable: 'ARM_SUBSCRIPTION_ID'),
                    string(credentialsId: 'FLASK_SECRET_KEY',       variable: 'TF_VAR_secret_key')
                ]) {
                    sh """
                        terraform -chdir=${TERRAFORM_DIR} init
                        terraform -chdir=${TERRAFORM_DIR} plan \
                            -var="resource_prefix=${APP_PREFIX}" \
                            -var="location=${AZURE_REGION}" \
                            -out=tfplan.binary
                    """
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'terraform/tfplan.binary', allowEmptyArchive: true
                }
            }
        }

        stage('Terraform: Apply (Approval Required)') {
            when {
                allOf {
                    branch 'main'
                    environment name: 'TF_AUTO_APPLY', value: 'true'
                }
            }
            steps {
                input message: 'APPROVAL REQUIRED: Apply Terraform plan to Azure? This creates cloud resources and may incur billing.',
                      ok: 'Approve and Apply'
                echo 'Applying Terraform infrastructure...'
                withCredentials([
                    string(credentialsId: 'AZURE_CLIENT_ID',       variable: 'ARM_CLIENT_ID'),
                    string(credentialsId: 'AZURE_CLIENT_SECRET',    variable: 'ARM_CLIENT_SECRET'),
                    string(credentialsId: 'AZURE_TENANT_ID',        variable: 'ARM_TENANT_ID'),
                    string(credentialsId: 'AZURE_SUBSCRIPTION_ID',  variable: 'ARM_SUBSCRIPTION_ID'),
                    string(credentialsId: 'FLASK_SECRET_KEY',       variable: 'TF_VAR_secret_key')
                ]) {
                    sh "terraform -chdir=${TERRAFORM_DIR} apply tfplan.binary"
                    sh "terraform -chdir=${TERRAFORM_DIR} output"
                }
            }
        }

        stage('Deploy: Azure App Service') {
            when {
                allOf {
                    branch 'main'
                    environment name: 'TF_AUTO_APPLY', value: 'true'
                }
            }
            steps {
                echo 'Deploying to Azure App Service...'
                withCredentials([
                    string(credentialsId: 'AZURE_CLIENT_ID',       variable: 'AZURE_CLIENT_ID'),
                    string(credentialsId: 'AZURE_CLIENT_SECRET',    variable: 'AZURE_CLIENT_SECRET'),
                    string(credentialsId: 'AZURE_TENANT_ID',        variable: 'AZURE_TENANT_ID'),
                    string(credentialsId: 'AZURE_SUBSCRIPTION_ID',  variable: 'AZURE_SUBSCRIPTION_ID')
                ]) {
                    sh """
                        az login --service-principal \
                            --username \$AZURE_CLIENT_ID \
                            --password \$AZURE_CLIENT_SECRET \
                            --tenant \$AZURE_TENANT_ID
                        az account set --subscription \$AZURE_SUBSCRIPTION_ID
                        zip -r deployment.zip app/ scripts/ run.py requirements.txt pyproject.toml
                        APP_NAME=\$(terraform -chdir=${TERRAFORM_DIR} output -raw app_service_name)
                        RG_NAME=\$(terraform -chdir=${TERRAFORM_DIR} output -raw resource_group_name)
                        az webapp deploy \
                            --resource-group \$RG_NAME \
                            --name \$APP_NAME \
                            --src-path deployment.zip \
                            --type zip
                        az logout
                    """
                }
            }
        }

        stage('Smoke Tests: Live') {
            when {
                allOf {
                    branch 'main'
                    environment name: 'TF_AUTO_APPLY', value: 'true'
                }
            }
            steps {
                echo 'Running post-deployment smoke tests...'
                withCredentials([
                    string(credentialsId: 'AZURE_CLIENT_ID',       variable: 'ARM_CLIENT_ID'),
                    string(credentialsId: 'AZURE_CLIENT_SECRET',    variable: 'ARM_CLIENT_SECRET'),
                    string(credentialsId: 'AZURE_TENANT_ID',        variable: 'ARM_TENANT_ID'),
                    string(credentialsId: 'AZURE_SUBSCRIPTION_ID',  variable: 'ARM_SUBSCRIPTION_ID')
                ]) {
                    sh """
                        APP_URL=\$(terraform -chdir=${TERRAFORM_DIR} output -raw app_service_url)
                        echo "Testing endpoint: \$APP_URL"
                        HTTP_CODE=\$(curl -sk -o /dev/null -w '%{http_code}' \$APP_URL/login)
                        echo "Login HTTP status: \$HTTP_CODE"
                        [ "\$HTTP_CODE" -eq 200 ] || (echo 'FAILED: login page not responding' && exit 1)
                        DASH_CODE=\$(curl -sk -o /dev/null -w '%{http_code}' \$APP_URL/dashboard)
                        echo "Dashboard unauthenticated status: \$DASH_CODE"
                        [ "\$DASH_CODE" -eq 302 ] || [ "\$DASH_CODE" -eq 200 ] || (echo 'FAILED: unexpected response' && exit 1)
                        echo 'All smoke tests passed.'
                    """
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
        }
        success {
            echo 'Pipeline SUCCEEDED. All stages completed successfully.'
        }
        failure {
            echo 'Pipeline FAILED. Review failing stage logs before redeployment.'
        }
        cleanup {
            cleanWs()
        }
    }
}