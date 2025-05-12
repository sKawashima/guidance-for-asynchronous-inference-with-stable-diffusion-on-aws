variable "ami_id" {
  description = "Amazon Linux 2 AMI ID (最新のAmazon Linux 2を使用)"
  type        = string
  default     = "ami-0de5311b2a443fb89" # 東京リージョンの最新Amazon Linux 2 AMI（2023年5月時点）
}

variable "key_name" {
  description = "EC2インスタンスに使用する既存のSSHキーペア名"
  type        = string
  default     = "my-existing-key" # ここを既存のキーペア名に変更してください
}