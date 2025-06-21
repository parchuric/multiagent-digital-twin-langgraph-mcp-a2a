variable "vnet_name" {
  description = "VNet name"
  type        = string
}

variable "address_space" {
  description = "VNet address space"
  type        = list(string)
}

variable "subnet_name" {
  description = "Subnet name"
  type        = string
}

variable "subnet_prefixes" {
  description = "Subnet prefixes"
  type        = list(string)
}

variable "nsg_name" {
  description = "NSG name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}
