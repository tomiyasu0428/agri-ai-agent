# 農業AIエージェント

LangChainとMongoDBを活用したAI農業管理システム。農業従事者の作物管理、タスクスケジューリング、農業意思決定を支援します。

## 特徴

- **AIタスク管理**: AI駆動のタスクスケジューリングと完了追跡
- **圃場ステータス監視**: リアルタイムな圃場状況評価とレポート
- **資材推奨**: 作物タイプと圃場履歴に基づく資材選択
- **データ統合**: 既存の農業データとのシームレスなAirtable統合
- **自然言語インターフェース**: 自然言語クエリでのシステム操作

## 技術スタック

- **AIフレームワーク**: LangChain（AIエージェント統合）
- **データベース**: MongoDB Atlas（スケーラブルなデータストレージ）
- **データ統合**: Airtable API（既存データ移行）
- **言語**: Python 3.8+
- **主要ライブラリ**: PyMongo, Motor, Pydantic, Python-dotenv

## インストール

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/tomiyasu0428/agri-ai-agent.git
   cd agri-ai-agent
   ```

2. **仮想環境を作成**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **依存関係をインストール**
   ```bash
   pip install -r requirements.txt
   ```

4. **環境設定**
   ```bash
   cp .env.template .env
   # .envファイルを編集して設定を追加
   ```

## 設定

`.env`ファイルを作成し、以下の変数を設定してください：

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB Atlas
MONGODB_URI=your_mongodb_connection_string
MONGODB_DATABASE=agri_ai_db

# Airtable
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_airtable_base_id

# 開発設定
DEBUG=True
LOG_LEVEL=INFO
```

## 使用方法

### データ移行

AirtableからMongoDBへの既存データ移行：

```bash
python scripts/remigrate_corrected_data.py
```

### エージェントの実行

```python
from src.agri_ai.core.agent import AgriAIAgent
from src.agri_ai.core.database import MongoDBClient

# データベース接続の初期化
mongo_client = MongoDBClient()
await mongo_client.connect()

# エージェントの作成と実行
agent = AgriAIAgent(mongo_client)
response = await agent.run("田中さんの今日のタスクは何ですか？")
print(response)
```

### 利用可能なツール

- **get_today_tasks**: 特定の作業者の今日の農業タスクを取得
- **complete_task**: 農業タスクを完了としてマーク
- **get_field_status**: 特定の圃場の現在の状況と情報を取得
- **recommend_pesticide**: 作物と条件に基づく適切な資材推奨

## プロジェクト構造

```
agri-ai-agent/
├── src/
│   └── agri_ai/
│       ├── core/
│       │   ├── agent.py          # メインAIエージェント
│       │   └── database.py       # データベース操作
│       ├── tools/
│       │   └── agricultural_tools.py  # LangChainツール
│       └── utils/
│           ├── config.py         # 設定管理
│           └── airtable_client.py # Airtable統合
├── docs/
│   ├── api_design.md            # API設計ドキュメント
│   ├── database_schema.md       # データベーススキーマ
│   ├── タスクリスト.md           # タスクリスト
│   └── data-migration-blog.md   # データ移行プロジェクト解説
├── scripts/
│   ├── check_field_mapping.py   # フィールドマッピング分析
│   └── remigrate_corrected_data.py # データ再移行
├── tests/
├── requirements.txt
└── README.md
```

## 開発

### テストの実行

```bash
python -m pytest tests/
```

### コード品質

```bash
# コードフォーマット
black src/

# 型チェック
mypy src/

# リンティング
flake8 src/
```

## データベース

### 移行済みデータ（427件）
- **圃場データ**: 36件（圃場ID, エリア, 圃場名, 面積(ha), 作付詳細）
- **作業タスク**: 283件（タスク名, ステータス, 予定日, メモ）
- **資材マスター**: 36件（資材名, 資材分類）
- **資材使用ログ**: 5件（使用日, 資材名, 圃場名, 使用量）
- **その他**: 67件（作付計画, 収穫ログ, ナレッジベース等）

## ドキュメント

- [API設計](docs/api_design.md)
- [データベーススキーマ](docs/database_schema.md)
- [タスクリスト](docs/タスクリスト.md)
- [データ移行プロジェクト解説](docs/data-migration-blog.md)

## 貢献方法

1. リポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## サポート

質問やサポートについては、GitHubでissueを開くか、開発チームまでお問い合わせください。

---

**持続可能な農業のために❤️を込めて開発**
