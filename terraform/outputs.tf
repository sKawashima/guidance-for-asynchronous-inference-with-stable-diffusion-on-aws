output "ec2_instance_id" {
  description = "デプロイに使用するEC2インスタンスのID"
  value       = aws_instance.sd_instance.id
}

output "ec2_public_ip" {
  description = "EC2インスタンスのパブリックIPアドレス"
  value       = aws_instance.sd_instance.public_ip
}

output "key_name" {
  description = "EC2インスタンスに使用されているAWSキーペア名"
  value       = var.key_name
}

output "vpc_id" {
  description = "作成したVPCのID"
  value       = aws_vpc.sd_vpc.id
}

output "dashboard_url" {
  description = "CloudWatchダッシュボードのURL"
  value       = "https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#dashboards:name=${aws_cloudwatch_dashboard.sd_dashboard.dashboard_name}"
}

output "console_connect_url" {
  description = "EC2インスタンスへのAWS Management Consoleからの接続URL"
  value       = "https://ap-northeast-1.console.aws.amazon.com/ec2/home?region=ap-northeast-1#ConnectToInstance:instanceId=${aws_instance.sd_instance.id}"
}

output "next_steps" {
  description = "デプロイ後の次のステップ"
  value       = <<-EOT
    ========================================================================
    デプロイ環境の準備が完了しました！

    1. AWS Management Consoleからインスタンスに接続:
       ${self.console_connect_url}

    2. デプロイスクリプトを実行:
       cd /home/ec2-user/sd-project/deploy
       bash ./deploy.sh

    3. デプロイ完了後、Stable Diffusion Web UIにアクセス:
       - AWS管理コンソールでEKSクラスターを確認
       - 作成されたロードバランサー (xxx-webui) のDNS名を確認
       - そのDNS名をブラウザで開いてUIにアクセス

    注意: デプロイには30-60分程度かかることがあります。
    ========================================================================
  EOT
}