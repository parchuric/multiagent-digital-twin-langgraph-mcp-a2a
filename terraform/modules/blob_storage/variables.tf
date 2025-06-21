variable "name" {
  description = "The name of the storage account."
  type        = string
}

variable "location" {
  description = "The Azure region to deploy the storage account."
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
}
