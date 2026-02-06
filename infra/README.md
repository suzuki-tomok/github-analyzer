# CloudFormation デプロイ手順

github-analyzer の AWS リソースを CloudFormation で一括管理する。

---

## 前提条件

| ツール | 確認コマンド |
|--------|------------|
| AWS CLI | `aws --version` |
| Docker | `docker --version` |
| AWS認証情報 | `aws sts get-caller-identity` |

---

## Step 1: ECRリポジトリ作成 & イメージpush

ECR はスタック外で管理する（イメージが先に存在する必要があるため）。

### リポジトリ作成（初回のみ）

```bash
aws ecr create-repository --repository-name github-analyzer --region ap-northeast-1
```

### イメージpush

```bash
# アカウント調査
aws sts get-caller-identity --query "Account" --output text

# ECRログイン
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin \
  <アカウントID>.dkr.ecr.ap-northeast-1.amazonaws.com

# ビルド & push
cd backend
docker build -t github-analyzer .
docker tag github-analyzer:latest \
  <アカウントID>.dkr.ecr.ap-northeast-1.amazonaws.com/github-analyzer:latest
docker push \
  <アカウントID>.dkr.ecr.ap-northeast-1.amazonaws.com/github-analyzer:latest
```

---

## Step 2: スタック作成（起動）

> ⚠️ cloudformation.yaml のコメントに日本語（全角文字）が含まれていると
> `file://` で読み込めない。`file://` でエラーが出る場合は英語コメント版を使用すること。

```bash
aws cloudformation create-stack \
  --stack-name github-analyzer \
  --template-body file://../infra/cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=DBMasterPassword,ParameterValue=<DBパスワード> \
    ParameterKey=GeminiApiKey,ParameterValue=<Gemini APIキー> \
    ParameterKey=GeminiModel,ParameterValue=<Gemini Model> \
    ParameterKey=GitHubClientId,ParameterValue=<GitHub Client ID> \
    ParameterKey=GitHubClientSecret,ParameterValue=<GitHub Client Secret> \
    ParameterKey=JwtSecretKey,ParameterValue=<JWT秘密鍵> \
    ParameterKey=ImageUri,ParameterValue=<アカウントID>.dkr.ecr.ap-northeast-1.amazonaws.com/github-analyzer:latest
```

作成状況の確認:

```bash
aws cloudformation describe-stacks \
  --stack-name github-analyzer \
  --query "Stacks[0].StackStatus"
```

`CREATE_COMPLETE` になれば完了（10〜15分）。

### URL確認

```bash
aws cloudformation describe-stacks \
  --stack-name github-analyzer \
  --query "Stacks[0].Outputs"
```

---

## Step 3: GitHub OAuth設定
```
GitHub → Settings → Developer settings → OAuth Apps → 対象アプリ
```

| 項目 | 値 |
|------|-----|
| Homepage URL | `http://<ALBのDNS名>` |
| Authorization callback URL | `http://<ALBのDNS名>/auth/github/callback` |

ALBのDNS名は Step 2 の Outputs で確認できる。

```
Step 1: ブラウザで以下にアクセス
https://github.com/login/oauth/authorize?client_id=Ov23li7OfGHhIqG0vuAZ&scope=read:user,repo
Step 2: GitHubで「Authorize」を押す
Step 3: リダイレクトされたURLからcodeをコピー
http://github-analyzer-alb-899831337.ap-northeast-1.elb.amazonaws.com/auth/github/callback?code=ここの文字列
```

---

## Step 4: 動作確認

| URL | 期待する結果 |
|-----|-------------|
| `http://<ALBのDNS名>` | `{"message":"github-analyzer API"}` |
| `http://<ALBのDNS名>/docs` | Swagger UI |

---

## スタック削除

```bash
aws cloudformation delete-stack --stack-name github-analyzer
```

全リソースが削除され、課金は $0 になる（スナップショットも残らない）。

削除状況の確認:

```bash
aws cloudformation describe-stacks --stack-name github-analyzer --query "Stacks[0].StackStatus"
```

`DELETE_COMPLETE`（またはスタックが見つからない）になれば完了。

> ※ ECR リポジトリはスタック外のため手動で削除が必要:
> ```bash
> aws ecr delete-repository --repository-name github-analyzer --force
> ```