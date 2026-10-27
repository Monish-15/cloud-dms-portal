# App Service Module: Linux App Service with Managed Identity
resource "azurerm_service_plan" "plan" {
  name                = var.app_service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = merge(var.tags, {
    Component   = "Compute"
    Environment = var.environment
  })
}

resource "azurerm_linux_web_app" "app" {
  name                = var.app_name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.plan.id
  https_only          = true

  # System-Assigned Managed Identity for passwordless Entra ID authentication to Azure Storage
  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on           = var.sku_name == "F1" ? false : true
    ftps_state          = "Disabled"
    minimum_tls_version = "1.2"
    http2_enabled       = true

    application_stack {
      python_version = "3.11"
    }

    app_command_line = "gunicorn --bind=0.0.0.0:8000 --timeout 600 run:app"
  }

  app_settings = {
    "FLASK_ENV"                      = "production"
    "SECRET_KEY"                     = var.secret_key
    "STORAGE_BACKEND"                = "azure"
    "AZURE_STORAGE_ACCOUNT_NAME"     = var.storage_account_name
    "AZURE_STORAGE_CONTAINER_NAME"   = var.storage_container_name
    "AZURE_USE_MANAGED_IDENTITY"     = "true"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "PORT"                           = "8000"
  }

  tags = merge(var.tags, {
    Component   = "WebApplication"
    Environment = var.environment
  })
}
