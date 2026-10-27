# Root Variables Definition

variable "location" {
  description = "The Azure Region to deploy resources into."
  type        = string
  default     = "eastus"
}

variable "resource_prefix" {
  description = "A prefix for all resource names to ensure uniqueness."
  type        = string
  default     = "dmsportal"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "prod"
}

variable "app_service_sku" {
  description = "App Service Plan pricing tier. B1 is recommended for cost-effective college evaluation."
  type        = string
  default     = "B1"
}

variable "container_name" {
  description = "Private container name for uploaded documents."
  type        = string
  default     = "secure-docs"
}

variable "secret_key" {
  description = "Flask secret key for session signing. Passed securely via CI/CD or tfvars."
  type        = string
  sensitive   = true
  default     = "change-me-in-production-strong-entropy-secret"
}

variable "tags" {
  description = "Common tags applied across all resources."
  type        = map(string)
  default = {
    Project   = "SecureDocumentPortal"
    ManagedBy = "Terraform"
    Course    = "DevOpsAcademicProject"
  }
}
