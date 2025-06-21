provider "azurerm" {
  features {}
  use_cli = true
  subscription_id = "757741e5-1190-400e-bc79-73ad919655ab"
}

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0"
    }
  }
}
