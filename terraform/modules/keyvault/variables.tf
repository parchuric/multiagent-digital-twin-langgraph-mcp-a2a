variable "name" {
  description = "The name of the Key Vault."
  type        = string
}

variable "location" {
  description = "The Azure region for the Key Vault."
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}

variable "sku_name" {
  description = "The SKU name of the Key Vault. Defaults to 'standard'."
  type        = string
  default     = "standard"
}
