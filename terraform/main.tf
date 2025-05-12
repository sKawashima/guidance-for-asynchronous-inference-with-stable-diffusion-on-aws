provider "aws" {
  region = "ap-northeast-1" # 東京リージョン
}

# VPC設定
resource "aws_vpc" "sd_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "sd-deploy-vpc"
  }
}

# パブリックサブネット
resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.sd_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "sd-deploy-public-subnet"
  }
}

# インターネットゲートウェイ
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.sd_vpc.id

  tags = {
    Name = "sd-deploy-igw"
  }
}

# ルートテーブル
resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.sd_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "sd-deploy-public-route-table"
  }
}

# ルートテーブルとサブネットの関連付け
resource "aws_route_table_association" "public_route_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_route_table.id
}

# セキュリティグループ
resource "aws_security_group" "sd_sg" {
  name        = "sd-deploy-sg"
  description = "Security group for SD deployment EC2"
  vpc_id      = aws_vpc.sd_vpc.id

  # SSH接続用
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  # HTTP接続用（デバッグやUIアクセス用）
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  # HTTPS接続用
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  # すべての送信トラフィックを許可
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sd-deploy-sg"
  }
}

# IAMロール
resource "aws_iam_role" "sd_role" {
  name = "sd-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# 管理者権限ポリシーをアタッチ
resource "aws_iam_role_policy_attachment" "admin_attach" {
  role       = aws_iam_role.sd_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# インスタンスプロファイル
resource "aws_iam_instance_profile" "sd_profile" {
  name = "sd-deploy-profile"
  role = aws_iam_role.sd_role.name
}

# SSHキーペア（実際のデプロイ時は既存のキーを使用する方が良い）
resource "aws_key_pair" "deployer" {
  key_name   = "sd-deployer-key"
  public_key = var.ssh_public_key # 変数から読み込み
}

# EC2インスタンス
resource "aws_instance" "sd_instance" {
  ami                    = var.ami_id # 変数から読み込み
  instance_type          = "t3.large" # 2vCPU, 8GBメモリ（デプロイ環境としては十分）
  key_name               = aws_key_pair.deployer.key_name
  subnet_id              = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.sd_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.sd_profile.name

  root_block_device {
    volume_size = 40 # デプロイに必要な最小容量
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y git
    
    # CloudWatch Agentのインストール
    yum install -y amazon-cloudwatch-agent
    
    # Docker インストール
    amazon-linux-extras install -y docker
    systemctl start docker
    systemctl enable docker
    usermod -a -G docker ec2-user
    
    # AWS CLI v2アップグレード
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install --update
    
    # プロジェクトのクローン
    su - ec2-user -c "git clone https://github.com/aws-solutions-library-samples/guidance-for-asynchronous-inference-with-stable-diffusion-on-aws.git /home/ec2-user/sd-project"
    
    # デプロイ準備完了メッセージ
    echo "EC2 instance setup completed. Connect via SSH and run deployment script." > /home/ec2-user/SETUP_COMPLETE.txt
  EOF

  tags = {
    Name = "sd-deployment-instance"
  }
}

# CloudWatch Dashboardと監視設定
resource "aws_cloudwatch_dashboard" "sd_dashboard" {
  dashboard_name = "SD-Deployment-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.sd_instance.id]
          ]
          period = 300
          stat   = "Average"
          region = "ap-northeast-1"
          title  = "CPU Utilization"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "NetworkIn", "InstanceId", aws_instance.sd_instance.id],
            ["AWS/EC2", "NetworkOut", "InstanceId", aws_instance.sd_instance.id]
          ]
          period = 300
          stat   = "Average"
          region = "ap-northeast-1"
          title  = "Network Traffic"
        }
      }
    ]
  })
}

# 出力変数
output "ec2_instance_id" {
  value = aws_instance.sd_instance.id
}

output "ec2_public_ip" {
  value = aws_instance.sd_instance.public_ip
}

output "ssh_command" {
  value = "ssh -i /path/to/your/private_key.pem ec2-user@${aws_instance.sd_instance.public_ip}"
}

output "deployment_instructions" {
  value = <<-EOT
    SSH接続後に以下のコマンドを実行してデプロイを開始:
    
    cd /home/ec2-user/sd-project/deploy
    bash ./deploy.sh
    
    デプロイが完了したら、AWS Management ConsoleでEKSクラスターの状態を確認し、
    作成されたロードバランサーのDNS名を確認してStable Diffusion Web UIにアクセスできます。
  EOT
}