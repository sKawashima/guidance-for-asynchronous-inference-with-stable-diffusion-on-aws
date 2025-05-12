variable "ami_id" {
  description = "Amazon Linux 2 AMI ID (最新のAmazon Linux 2を使用)"
  type        = string
  default     = "ami-0de5311b2a443fb89" # 東京リージョンの最新Amazon Linux 2 AMI（2023年5月時点）
}

variable "ssh_public_key" {
  description = "SSH接続用の公開鍵"
  type        = string
  # サンプル公開鍵（実際のデプロイ時は自分の公開鍵に置き換えてください）
  default     = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD3F6tyPEFEzV0LX3X8BsXdMsQz1x2cEikKDEY0aIj41qgxMCP/iteneqXSIFZBp5vizPvaoIR3Um9xK7PGoW8giupGn+EPuxIA4cDM4vzOqOkiMPhz5XK0whEjkVzTo4+S0puvDZuwIsdiW9mxhJc7tgBNL0cYlWSYVkz4G/fslNfRPW5mYAM49f4fhtxPb5ok4Q2Lg9dPKVHO/Bgeu5woMc7RY0p1ej6D4CKFE6lymSDJpW0YHX/wqE9+cfEauh7xZcG0q9t2ta6F6fmX0agvpFyZo8aFbXeUBr7osSCJNgvavWbM/06niWrOvYX2xwWdhXmXSrbX8ZbabVohBK41 CHANGE_TO_YOUR_KEY"
}