# Storage Module: Private Blob Container and Storage Tables
resource "azurerm_storage_account" "storage" {
  name                             = var.storage_account_name
  resource_group_name              = var.resource_group_name
  location                         = var.location
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  account_kind                     = "StorageV2"
  min_tls_version                  = "TLS1_2"
  enable_https_traffic_only        = true
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 14
    }
  }

  tags = merge(var.tags, {
    Component   = "Storage"
    Environment = var.environment
  })
}

# Private Blob Container (No anonymous read/write access)
resource "azurerm_storage_container" "docs" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# Table Storage for Document Metadata
resource "azurerm_storage_table" "metadata" {
  name                 = "documentmetadata"
  storage_account_name = azurerm_storage_account.storage.name
}

# Table Storage for Audit Records
resource "azurerm_storage_table" "audit" {
  name                 = "auditevents"
  storage_account_name = azurerm_storage_account.storage.name
}
