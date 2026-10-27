# Root Outputs Definition (Non-sensitive endpoints and resource identifiers)

output "resource_group_name" {
  description = "Name of the provisioned Azure Resource Group."
  value       = azurerm_resource_group.rg.name
}

output "storage_account_name" {
  description = "Name of the Azure Storage Account."
  value       = module.storage.storage_account_name
}

output "blob_container_name" {
  description = "Name of the private document blob container."
  value       = module.storage.container_name
}

output "app_service_name" {
  description = "Name of the Linux Web App instance."
  value       = module.app_service.app_name
}

output "app_service_url" {
  description = "Public HTTPS application endpoint."
  value       = "https://${module.app_service.default_hostname}"
}

output "managed_identity_principal_id" {
  description = "Principal ID of the App Service system-assigned managed identity."
  value       = module.app_service.principal_id
}
