# github-analyzer

## テスト

### 技術スタック

- pytest
- pytest-asyncio
- pytest-cov
- httpx（TestClient用）
- ruff（静的解析・フォーマット）

### セットアップ
```bash
cd backend
pip install -r requirements-dev.txt
```

### 実行方法
```bash
cd backend

# 全テスト
pytest -v

# カバレッジ付き
pytest --cov=app --cov-report=term-missing

# HTMLで表示
pytest --cov=app --cov-report=html
# backend/htmlcov/index.htmlをブラウザで開く

# 特定ファイル
pytest tests/routers/test_auth.py -v
pytest tests/routers/test_analyses.py -v
```

### 静的解析（ruff）
```bash
cd backend

# Lintチェック
ruff check app/

# 自動修正
ruff check app/ --fix

# フォーマット
ruff format app/

# フォーマットチェック（変更しない）
ruff format app/ --check
```

### テストポリシー

#### 1. エンドポイント × ステータスコード

各APIエンドポイントに対して、返りうるHTTPステータスコードを網羅する。

| ステータス | 意味 |
|-----------|------|
| 200 | 正常系 |
| 401 | 認証エラー（トークンなし/不正/期限切れ） |
| 404 | リソースなし（存在しないID/他人のデータ） |
| 422 | バリデーションエラー（不正な入力） |

#### 2. 境界値テスト

Pydanticスキーマの制約に対して、境界値をテストする。

| 項目 | 制約 | OKケース | NGケース |
|------|------|----------|----------|
| limit | 1〜30 | 1, 30 | 31 |
| memo | max 1000文字 | 1000文字 | 1001文字 |

#### 3. 認可テスト

「自分のデータしか触れない」ことを確認する。

- test_userが作成したデータに対して
- other_userでアクセス → 404

#### 4. 外部APIモック

GitHub API、Gemini APIは本物を叩かない。

- `unittest.mock.patch` で差し替え
- 自分のコードのロジックだけをテスト

#### 5. DB状態確認

データ変更系のAPIでは、実際にDBの状態が変わっていることを確認する。

- DELETE後にレコードが消えているか