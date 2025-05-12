# Stable Diffusion デプロイ用Terraform設定

このTerraformコードは、AWSのStable Diffusionデプロイ用の最小限の環境を構築します。

## 構築されるリソース

- VPC、サブネット、インターネットゲートウェイ、ルートテーブル
- セキュリティグループ（SSH、HTTP、HTTPS）
- 管理者権限を持つIAMロール
- デプロイ用のEC2インスタンス（t3.large、40GBディスク）
- CloudWatch監視ダッシュボード

## 使用方法

### 前提条件

- Terraformがインストールされていること（v1.0以上）
- AWS CLIがインストールおよび設定されていること
- SSHキーペアが用意されていること

### デプロイ手順

1. **既存のSSHキーの指定**

`variables.tf`ファイルを編集し、`key_name`変数に既存のAWSキーペア名を設定します：

```hcl
variable "key_name" {
  default = "your-existing-key-name" # AWSコンソールで確認できる既存のキーペア名
}
```

2. **Terraformの初期化と実行**

```bash
# 現在のディレクトリにクローンした場合
cd terraform

# Terraformの初期化
terraform init

# プランの確認
terraform plan

# インフラストラクチャのデプロイ
terraform apply
```

3. **デプロイ完了後**

Terraformの実行が完了すると、出力に以下の情報が表示されます：
- EC2インスタンスのパブリックIP
- AWS Management Consoleからの接続URL
- デプロイ手順

4. **AWS Management ConsoleからのEC2接続とデプロイ**

Terraformの実行完了後に表示される`console_connect_url`を使用して、AWSコンソールから直接EC2インスタンスに接続できます。

または、EC2コンソールで以下の手順で接続することも可能です：
1. EC2ダッシュボードで該当のインスタンスを選択
2. 「接続」ボタンをクリック
3. 「EC2 Instance Connect」タブを選択
4. 「接続」ボタンをクリックしてブラウザベースのターミナルを開く

接続後、以下のコマンドを実行してデプロイを開始します：
```bash
cd /home/ec2-user/sd-project/deploy
bash ./deploy.sh
```

## リソースの削除

使用が終わったら、以下のコマンドで全てのリソースを削除できます：

```bash
terraform destroy
```

## 重要な注意事項

- このデプロイはEC2インスタンス上でStable Diffusionをデプロイするための環境を準備するものです
- 実際のEKSクラスタやリソースは、EC2上で`deploy.sh`スクリプトを実行することで作成されます
- デプロイには30-60分程度かかる場合があります
- デプロイ完了後も、GPUインスタンス、EKSクラスタ、ロードバランサーなどのリソースに対する料金が発生します
- デプロイが完了したら、AWSコンソールのCloudFormationスタックから`sdoneksStack`（または指定した名前）を確認することでリソースを確認できます