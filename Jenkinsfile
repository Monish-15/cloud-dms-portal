// Jenkinsfile -- Secure Document Management Portal
// Declarative CI/CD Pipeline for Windows & Linux Agents

pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '15'))
        timeout(time: 45, unit: 'MINUTES')
        timestamps()
    }

    environment {
        PYTHON_BIN     = 'python'
        VENV_DIR       = '.venv'
        TERRAFORM_DIR  = 'terraform'
        APP_PREFIX     = 'dmsportal'
        AZURE_REGION   = 'eastasia'
        TF_AUTO_APPLY  = 'false'
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm
                bat 'git log --oneline -5'
            }
        }

        stage('Python Environment') {
            steps {
                echo 'Setting up Python virtual environment...'
                bat """
                    if not exist ${VENV_DIR} (
                        ${PYTHON_BIN} -m venv ${VENV_DIR}
                    )
                    call ${VENV_DIR}\\Scripts\\activate.bat
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt -r requirements-dev.txt
                """
            }
        }

        stage('Lint: Ruff') {
            steps {
                echo 'Running Ruff linter...'
                bat """
                    call ${VENV_DIR}\\Scripts\\activate.bat
                    ruff check app/ tests/ scripts/
                """
            }
            post {
                failure { echo 'Linting failed. Blocking deployment.' }
            }
        }

        stage('Tests: Pytest') {
            steps {
                echo 'Running pytest with coverage...'
                bat """
                    call ${VENV_DIR}\\Scripts\\activate.bat
                    if not exist reports mkdir reports
                    pytest --cov=app --cov-report=xml:reports/coverage.xml --cov-report=html:reports/htmlcov --junitxml=reports/junit.xml -v
                """
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                }
                failure { echo 'Tests failed. Blocking deployment.' }
            }
        }

        stage('Security: Bandit') {
            steps {
                echo 'Running Bandit security scanner...'
                bat """
                    call ${VENV_DIR}\\Scripts\\activate.bat
                    if not exist reports mkdir reports
                    bandit -r app/ -ll -f json -o reports/bandit-report.json || exit 0
                    bandit -r app/ -ll
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/bandit-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Terraform: Format & Validate') {
            steps {
                echo 'Validating Terraform configuration...'
                bat """
                    if exist bin\\terraform.exe (
                        bin\\terraform.exe -chdir=${TERRAFORM_DIR} fmt -check -recursive
                        bin\\terraform.exe -chdir=${TERRAFORM_DIR} init -backend=false
                        bin\\terraform.exe -chdir=${TERRAFORM_DIR} validate
                    ) else (
                        terraform -chdir=${TERRAFORM_DIR} fmt -check -recursive
                        terraform -chdir=${TERRAFORM_DIR} init -backend=false
                        terraform -chdir=${TERRAFORM_DIR} validate
                    )
                """
            }
            post {
                failure { echo 'Terraform validation failed. Blocking deployment.' }
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
                bat """
                    powershell -Command "d:\\Devops\\.venv\\Scripts\\python.exe -c \\"import os, zipfile; z = zipfile.ZipFile('deploy.zip', 'w', zipfile.ZIP_DEFLATED); z.write('run.py', 'run.py'); z.write('requirements.txt', 'requirements.txt'); [z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), '.').replace('\\\\\\\\', '/')) for p in ['app', 'scripts'] for r, d, files in os.walk(p) if '__pycache__' not in r for f in files]; print('Packaged')\\""
                    az webapp deploy --resource-group rg-dmsportal-prod --name app-dmsportal-ozrmq2 --src-path deploy.zip --type zip
                """
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
    }
}