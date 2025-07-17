variable "name" {
  description = "Name of the Redis Cache instance."
  type        = string
}

variable "location" {
  description = "Azure region for the Redis Cache."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for the Redis Cache."
  type        = string
}

variable "tags" {
  description = "Tags to apply to the Redis Cache."
  type        = map(string)
  default     = {}
}
