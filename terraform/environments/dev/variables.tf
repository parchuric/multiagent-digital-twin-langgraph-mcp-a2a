# File: terraform/environments/dev/variables.tf

variable "tags" {
  description = "Tags to apply to resources in this environment."
  type        = map(string)
  default     = {}
}

variable "resource_group_name" {
  description = "Name of the resource group for the environment."
  type        = string
}

variable "location" {
  description = "Azure region for the environment."
  type        = string
}
