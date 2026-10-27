# Provider Configurations
provider "azurerm" {
  subscription_id = "8bcccc49-e540-4338-81c4-5477743451d4"

  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

provider "random" {}
