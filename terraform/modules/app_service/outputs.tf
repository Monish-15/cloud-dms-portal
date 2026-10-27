output "app_id" {
  description = "The ID of the Linux Web App."
  value       = azurerm_linux_web_app.app.id
}

output "app_name" {
  description = "The name of the Linux Web App."
  value       = azurerm_linux_web_app.app.name
}

output "default_hostname" {
  description = "The default hostname of the deployed Web App."
  value       = azurerm_linux_web_app.app.default_hostname
}

output "principal_id" {
  description = "The Principal ID of the system-assigned managed identity."
  value       = azurerm_linux_web_app.app.identity[0].principal_id
}
