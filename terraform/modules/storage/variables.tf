variable "resource_group_name" {
  description = "Name of the resource group."
  type        = string
}

variable "location" {
  description = "Azure region where the storage resources will be provisioned."
  type        = string
}

variable "storage_account_name" {
  description = "Globally unique name for the Azure Storage Account (3-24 lowercase alphanumeric characters)."
  type        = string
}

variable "container_name" {
  description = "Name of the private Blob Storage container."
  type        = string
  default     = "secure-docs"
}

variable "environment" {
  description = "Deployment environment name (e.g., dev, prod)."
  type        = string
  default     = "prod"
}

variable "tags" {
  description = "Tags applied to all storage resources."
  type        = map(string)
  default     = {}
}
