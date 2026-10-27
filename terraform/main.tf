# Root Terraform Orchestration
# Deploys Resource Group, Storage Module, App Service Module, and Entra ID RBAC Assignments

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.resource_prefix}-${var.environment}"
  location = var.location

  tags = merge(var.tags, {
    Environment = var.environment
  })
}

# 1. Storage Infrastructure Module
module "storage" {
  source               = "./modules/storage"
  resource_group_name  = azurerm_resource_group.rg.name
  location             = azurerm_resource_group.rg.location
  storage_account_name = "st${var.resource_prefix}${random_string.suffix.result}"
  container_name       = var.container_name
  environment          = var.environment
  tags                 = var.tags
}

# 2. Web Application Infrastructure Module
module "app_service" {
  source                 = "./modules/app_service"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  app_service_plan_name  = "asp-${var.resource_prefix}-${var.environment}"
  app_name               = "app-${var.resource_prefix}-${random_string.suffix.result}"
  sku_name               = var.app_service_sku
  storage_account_name   = module.storage.storage_account_name
  storage_container_name = module.storage.container_name
  secret_key             = var.secret_key
  environment            = var.environment
  tags                   = var.tags
}

# 3. Least-Privilege Azure RBAC Assignments: Managed Identity -> Storage
# Role: Storage Blob Data Contributor (Allows read/write to private blobs without access keys)
resource "azurerm_role_assignment" "app_blob_contributor" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.app_service.principal_id
}

# Role: Storage Table Data Contributor (Allows read/write to metadata/audit tables)
resource "azurerm_role_assignment" "app_table_contributor" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = module.app_service.principal_id
}
