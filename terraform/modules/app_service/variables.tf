variable "resource_group_name" {
  description = "Name of the resource group."
  type        = string
}

variable "location" {
  description = "Azure region where the App Service will be provisioned."
  type        = string
}

variable "app_service_plan_name" {
  description = "Name of the App Service Plan."
  type        = string
}

variable "app_name" {
  description = "Name of the Linux Web App."
  type        = string
}

variable "sku_name" {
  description = "The SKU for the plan (B1 recommended for student evaluation)."
  type        = string
  default     = "B1"
}

variable "storage_account_name" {
  description = "Name of the storage account for App Settings."
  type        = string
}

variable "storage_container_name" {
  description = "Name of the private blob container."
  type        = string
  default     = "secure-docs"
}

variable "secret_key" {
  description = "Application secret key."
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "tags" {
  description = "Tags applied to all app service resources."
  type        = map(string)
  default     = {}
}
