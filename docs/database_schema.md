# データベーススキーマ定義

このドキュメントは、本プロジェクトで使用されるMongoDBのデータベーススキーマを定義します。
データはAirtableから移行され、`src/agri_ai/utils/airtable_client.py`内の`AirtableToMongoMigrator`クラスで定義されたロジックに基づいて変換されます。

## コレクション一覧

- **圃場データ (field_data)**: 圃場の基本情報を管理します。
- **作物マスター (crop_master)**: 作物のマスターデータを管理します。
- **作付計画 (planting_plan)**: 作物の作付計画を管理します。
- **Crop Task Template**: 作物ごとのタスクテンプレートを管理します。
- **作業タスク (work_task)**: 日々の作業タスクを管理します。
- **資材マスター (material_master)**: 農薬や肥料などの資材マスターデータを管理します。
- **資材使用ログ (material_usage_log)**: 資材の使用履歴を記録します。
- **作業者マスター (worker_master)**: 作業者のマスターデータを管理します。
- **ナレッジベース (knowledge_base)**: 農業に関する知識やノウハウを蓄積します。
- **収穫ログ (harvest_log)**: 収穫実績を記録します。
- **日報ログ (daily_log)**: 日々の作業報告を記録します。

---

## スキーマ詳細

### 1. 圃場データ (`field_data`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `圃場ID` | String | 独自の圃場ID |
| `エリア` | String | 圃場が属するエリア |
| `圃場名` | String | 圃場の名前 |
| `面積(ha)` | Number | 圃場の面積（ヘクタール） |
| `作付詳細` | Array | 関連する作付計画のIDの配列 |
| `大豆播種管理 2` | ??? | (用途不明) |
| `migrated_at` | ISODate | データ移行日時 |

### 2. 作物マスター (`crop_master`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `作物名` | String | 作物の名前 |
| `分類` | String | 作物の分類 |
| `作付計画` | Array | 関連する作付計画のIDの配列 |
| `Crop Task Template`| Array | 関連するタスクテンプレートのIDの配列 |
| `created_time` | ISODate | Airtableでの作成日時 |
| `table_source` | String | 元のAirtableテーブル名 |
| `migrated_at` | ISODate | データ移行日時 |

### 3. 作付計画 (`planting_plan`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `播種回次` | String | 播種の回次 |
| `品種名` | String | 作物の品種名 |
| `播種予定日` | Date | 播種の予定日 |
| `播種実施日` | Date | 播種の実施日 |
| `播種量/枚数` | Number | 播種量または枚数 |
| `定植予定日` | Date | 定植の予定日 |
| `作つけ面積 (ha)` | Number | 作付け面積（ヘクタール） |
| `元肥計画 (肥料名 kg/10a)` | String | 元肥の計画 |
| `収穫予定` | Date | 収穫の予定日 |
| `圃場データ` | Array | 関連する圃場データのIDの配列 |
| `圃場名 (from 圃場データ)` | Array | 関連する圃場名 |
| `作物マスター` | Array | 関連する作物マスターのIDの配列 |
| `ID` | String | 独自のID |
| `資材使用量` | ??? | (用途不明) |
| `面積(ha) (from 圃場データ)` | Array | 関連する圃場の面積 |
| `作業タスク 3` | ??? | (用途不明) |
| `migrated_at` | ISODate | データ移行日時 |

### 4. Crop Task Template

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `タスク名` | String | テンプレートのタスク名 |
| `基準日` | String | 予定日計算の基準となる日 |
| `オフセット(日)` | Number | 基準日からのオフセット日数 |
| `作物マスター` | Array | 関連する作物マスターのIDの配列 |
| `migrated_at` | ISODate | データ移行日時 |

### 5. 作業タスク (`work_task`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `タスク名` | String | タスクの内容 |
| `関連する作付計画`| Array | 関連する作付計画のIDの配列 |
| `ステータス` | String | タスクの進捗状況 (例: 未着手, 進行中, 完了) |
| `予定日` | Date | タスクの予定日 |
| `メモ` | String | タスクに関するメモ |
| `圃場名 (from 圃場データ) (from 関連する作付計画)` | Array | 関連する圃場名 |
| `migrated_at` | ISODate | データ移行日時 |

### 6. 資材マスター (`material_master`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `資材名` | String | 資材の名前 |
| `資材分類` | String | 資材の分類 (例: 農薬, 肥料) |
| `migrated_at` | ISODate | データ移行日時 |

### 7. 資材使用ログ (`material_usage_log`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `使用日` | Date | 資材を使用した日 |
| `資材名` | Array | 使用した資材のIDの配列 |
| `圃場名` | Array | 使用した圃場のIDの配列 |
| `作物名` | Array | 対象となった作物のIDの配列 |
| `使用量` | Number | 資材の使用量 |
| `単位` | String | 使用量の単位 (例: kg, L) |
| `単価` | Number | 資材の単価 |
| `使用金額` | Number | 使用金額 |
| `作業者` | Array | 作業者のIDの配列 |
| `作業内容` | String | 具体的な作業内容 |
| `メモ` | String | 関連メモ |
| `migrated_at` | ISODate | データ移行日時 |

### 8. 作業者マスター (`worker_master`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `作業者名` | String | 作業者の名前 |
| `役割` | String | 役割 (例: 管理者, 一般) |
| `所属` | String | 所属部署など |
| `電話番号` | String | 電話番号 |
| `メール` | String | メールアドレス |
| `資格・免許` | String | 保有資格や免許 |
| `メモ` | String | 関連メモ |
| `migrated_at` | ISODate | データ移行日時 |

### 9. ナレッジベース (`knowledge_base`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `タイトル` | String | ナレッジのタイトル |
| `カテゴリ` | String | ナレッジのカテゴリ |
| `詳細` | String | ナレッジの詳細内容 |
| `登録日` | Date | 登録日 |
| `migrated_at` | ISODate | データ移行日時 |

### 10. 収穫ログ (`harvest_log`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `収穫日` | Date | 収穫した日 |
| `作物名` | Array | 収穫した作物のIDの配列 |
| `圃場名` | Array | 収穫した圃場のIDの配列 |
| `サイズ` | String | サイズ (例: S, M, L) |
| `単価(円/個)` | Number | 単価 |
| `売上` | Number | 売上金額 |
| `メモ` | String | 関連メモ |
| `migrated_at` | ISODate | データ移行日時 |

### 11. 日報ログ (`daily_log`)

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `_id` | ObjectId | MongoDBのドキュメントID |
| `airtable_id` | String | AirtableのレコードID |
| `name` | String | レポート名 |
| `報告日` | Date | 報告日 |
| `報告者` | String | 報告者名 |
| `報告内容` | String | 報告内容 |
| `日付` | Date | (報告日と同じ) |
| `作業者` | String | (報告者と同じ) |
| `作業内容` | String | (報告内容と同じ) |
| `created_time` | ISODate | Airtableでの作成日時 |
| `table_source` | String | 元のAirtableテーブル名 |
| `migrated_at` | ISODate | データ移行日時 |
