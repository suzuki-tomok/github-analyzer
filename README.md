# github-analyzer

GitHubリポジトリをAIで分析し、開発者の評価スコアとレポートを生成するAPI

## 技術スタック

- FastAPI
- Google Gemini API
- SQLAlchemy
- GitHub OAuth + JWT
- httpx
- python-jose
- Docker
- pytest / ruff / GitHub Actions (CI)

## インフラ（AWS）

- ECS Fargate
- RDS (PostgreSQL)
- ALB
- ECR

## 必要環境

- Python 3.11+

## セットアップ(Windows11)
```bash
cd backend
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

## ライブラリ追加時
```bash
pip install ライブラリ名
pip freeze > requirements.txt
```

## GitHub OAuth認証フロー

1. 下記URLにブラウザでアクセス（CLIENT_IDは.envの値）
```
https://github.com/login/oauth/authorize?client_id=YOUR_CLIENT_ID&scope=read:user,repo
```
2. GitHubで「Authorize」を押す
3. リダイレクト先のURLから`?code=xxxxx`をコピー
4. `/auth/github/callback`にcodeをPOST
5. 返ってきた`access_token`（JWT）を使って認証


## マイグレーション

Alembicでデータベースのスキーマを管理しています。

### 初期セットアップ（済み）
```bash
# Alembicの初期化
pip install alembic
alembic init alembic

# alembic/env.py にモデルとDB接続を設定
# app/main.py の Base.metadata.create_all() を削除

# 初回マイグレーション生成・適用
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### モデル追加時
新しいモデルを作成したら `alembic/env.py` にimportを追加してください。
```python
# alembic/env.py
from app.models import User, Analysis, NewModel  # ← 追加
```

### 日常の使い方
```bash
# モデル変更後、マイグレーションファイルを自動生成
alembic revision --autogenerate -m "変更内容の説明"

# マイグレーションを適用
alembic upgrade head

# 現在の状態を確認
alembic current

# 1つ前に戻す
alembic downgrade -1

# マイグレーション履歴を確認
alembic history
```

### いつ実行するか

| 場面 | コマンド |
|------|---------|
| モデルにカラム追加・変更・削除した | `revision --autogenerate` → `upgrade head` |
| 新しいモデルを追加した | `env.py` にimport追加 → `revision --autogenerate` → `upgrade head` |
| 初回セットアップ時 | `upgrade head` |
| 本番デプロイ時 | `upgrade head` |
| 変更を取り消したい | `downgrade -1` |

## API

### 認証
| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | /auth/github/callback | GitHub OAuth（ログイン/新規登録） |
| GET | /auth/me | ユーザー情報取得（JWT必須） |

### 分析
| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | /analyses | 分析実行 |
| GET | /analyses | 履歴一覧 |
| GET | /analyses/{id} | 詳細取得 |
| PATCH | /analyses/{id} | メモ更新 |
| DELETE | /analyses/{id} | 削除 |

## 評価項目

| 項目 | 説明 |
|------|------|
| test | テストコードの有無・品質 |
| comment | コメントの適切さ |
| commit_size | 1コミットあたりの変更量 |
| commit_frequency | コミット頻度 |
| commit_message | コミットメッセージの質 |
| activity | 稼働の安定性 |

## Docker

### 起動
```bash
cd backend
docker-compose up --build
```

### 停止
```bash
Ctrl + C
```

または
```bash
docker-compose down
```

### アクセス
```
http://localhost:8001/docs
```

### ファイル構成

| ファイル | 役割 |
|----------|------|
| Dockerfile | イメージの作り方（レシピ） |
| docker-compose.yml | コンテナの起動設定 |
| .dockerignore | イメージに含めないファイル |

### 環境ごとのDB

| 環境 | DB |
|------|-----|
| ローカル開発 | SQLite（app.db） |
| Docker ローカル | SQLite（app.db） |
| AWS 本番 | RDS（PostgreSQL） |

## セキュリティに関する注意

GitHub Access Tokenは現在データベースに平文で保存しています。本番運用時はAWS Secrets Managerやカラムレベルの暗号化（Fernet等）による保護が必要です。

## TODO

- [x] プロジェクト構成
- [x] Gemini API連携
- [x] DB設計・SQLAlchemy
- [x] GitHub OAuth認証
- [x] JWT認証
- [x] /auth/me エンドポイント
- [x] 分析履歴CRUD
- [x] ログ設計（リクエスト/レスポンス/処理時間）
- [x] カスタムエラーハンドリング（ErrorCode）
- [x] pytest
- [x] CI（GitHub Actions + ruff）
- [x] Docker化
- [x] AWSデプロイ（ECS Fargate + RDS + ALB）
- [x] IaC（CloudFormation）
- [x] ER図
- [x] シーケンス図