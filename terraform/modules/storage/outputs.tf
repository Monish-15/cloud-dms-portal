output "storage_account_id" {
  description = "The ID of the Azure Storage Account."
  value       = azurerm_storage_account.storage.id
}

output "storage_account_name" {
  description = "The name of the Azure Storage Account."
  value       = azurerm_storage_account.storage.name
}

output "container_name" {
  description = "The name of the private blob container."
  value       = azurerm_storage_container.docs.name
}

output "primary_blob_endpoint" {
  description = "The primary blob endpoint URL."
  value       = azurerm_storage_account.storage.primary_blob_endpoint
}
