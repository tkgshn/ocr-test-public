# 改善提案シート OCR システム

Google Document AI を使用した改善提案シートの文字起こしシステムです。

## 機能

### Phase 1: 単一セクション OCR 検証 ✅

- **基本的な OCR 機能**: Google Document AI による高精度な文字認識
- **座標データ付きハイライト表示**: OCR 結果の視覚的確認
- **WebUI でのテキスト修正**: インタラクティブな修正インターフェース
- **ファイル形式対応**: 画像（JPG, PNG）・PDF

### Phase 2: 複数セクション処理 🚧

- **セクション自動分割・構造化**: 改善提案シートの複数セクションを自動検出
- **複数セクション対応**: 各セクションの個別処理と統合
- **セクション間関係性分析**: セクション間の関連性を分析

### Phase 3: 完全 PDF 処理システム 📋

- **完全 PDF 処理**: 複数ページ PDF の一括処理
- **バッチ処理機能**: 大量ファイルの効率的処理
- **高度な分析機能**: 統計分析とレポート生成

## セットアップ

### 1. 環境準備

```bash
# リポジトリをクローン
git clone <repository-url>
cd OCR_test

# 仮想環境を作成・有効化
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを作成し、以下の設定を行ってください：

```bash
# OpenAI API設定（文字修正と要約機能のみ使用）
OPENAI_API_KEY=your_openai_api_key_here

# Google Document AI設定
GOOGLE_CLOUD_PROJECT_ID=your_google_cloud_project_id
GOOGLE_CLOUD_LOCATION=us
GOOGLE_CLOUD_PROCESSOR_ID=your_processor_id

# Google Cloud認証設定（以下のいずれかを使用）
# 方法1: サービスアカウントキーファイルのパス
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

# 方法2: Application Default Credentials (ADC) を使用する場合
# gcloud auth application-default login を実行してください
# この場合、GOOGLE_APPLICATION_CREDENTIALSは不要です

# Document AI API エンドポイント（地域に応じて設定）
# us: us-documentai.googleapis.com
# eu: eu-documentai.googleapis.com
GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT=us-documentai.googleapis.com
```

### 3. Google Document AI の設定

#### 3.1 Google Cloud プロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成または既存のプロジェクトを選択
3. Document AI API を有効化
4. 課金を有効化

#### 3.2 Document AI プロセッサーの作成

1. Google Cloud Console で「Document AI」を検索
2. 「プロセッサー」→「プロセッサーを作成」
3. 「Enterprise Document OCR」を選択
4. プロセッサー名を入力し、地域を選択
5. 作成されたプロセッサー ID をメモ

#### 3.3 認証の設定

**方法 1: サービスアカウントキー（推奨）**

1. Google Cloud Console で「IAM と管理」→「サービスアカウント」
2. 「サービスアカウントを作成」
3. 以下の役割を付与：
   - `Document AI API User`
   - `Service Account Token Creator`
4. 「キー」タブで「新しいキーを作成」→「JSON」
5. ダウンロードした JSON ファイルのパスを`GOOGLE_APPLICATION_CREDENTIALS`に設定

**方法 2: Application Default Credentials (ADC)**

```bash
# Google Cloud CLIをインストール後
gcloud auth application-default login
```

### 4. アプリケーションの起動

```bash
# Streamlitアプリを起動
streamlit run app.py
```

ブラウザで `http://localhost:8501` にアクセスしてください。

## 使用方法

### 基本的な使用方法

1. **ファイルアップロード**: 改善提案シートの画像または PDF をアップロード
2. **OCR 処理**: Google Document AI で自動的に処理
3. **結果確認**: ハイライト表示で座標情報を確認
4. **テキスト修正**: 必要に応じて WebUI でテキストを修正
5. **データ出力**: JSON、Markdown 形式でデータをエクスポート

### 複数セクション処理（Phase 2）

1. **セクション分割**: 改善提案シートを自動的にセクションに分割
2. **個別処理**: 各セクション（課題、提案、対象など）を個別に処理
3. **統合結果**: 全セクションの結果を統合して表示

## API 仕様

### OCRProcessor

```python
from ocr_processor import OCRProcessor

# 初期化
processor = OCRProcessor()

# 単一画像処理
result = processor.process_single_image(image_file)

# 複数画像処理
results = processor.process_multiple_images(image_files)
```

### SectionAnalyzer

```python
from section_analyzer import SectionAnalyzer

# セクション分析
analyzer = SectionAnalyzer()
sections = analyzer.analyze_sections(image)
```

### MultiSectionProcessor

```python
from multi_section_processor import MultiSectionProcessor

# 複数セクション処理
processor = MultiSectionProcessor()
result = processor.process_document(image_file)
```

## トラブルシューティング

### Google Document AI 関連

**エラー: "Failed to setup Document AI"**

- Google Cloud プロジェクト ID が正しく設定されているか確認
- Document AI API が有効化されているか確認
- 認証情報が正しく設定されているか確認

**エラー: "Service account file not found"**

- `GOOGLE_APPLICATION_CREDENTIALS`のパスが正しいか確認
- サービスアカウントキーファイルが存在するか確認

**エラー: "Permission denied"**

- サービスアカウントに適切な権限が付与されているか確認
- プロジェクトで課金が有効化されているか確認

### OpenAI 関連（文字修正・要約機能）

**エラー: "OpenAI API key not found"**

- `.env`ファイルに`OPENAI_API_KEY`が設定されているか確認
- API キーが有効か確認
- 注意: OpenAI APIはOCR処理ではなく、文字修正と要約機能のみに使用されます

## 開発情報

### プロジェクト構造

```
OCR_test/
├── app.py                      # メインアプリケーション
├── config.py                   # 設定ファイル
├── ocr_processor.py           # OCR処理クラス
├── ocr_visualizer.py          # OCR結果可視化
├── section_analyzer.py        # セクション分析
├── multi_section_processor.py # 複数セクション処理
├── text_corrector.py          # テキスト修正
├── data_organizer.py          # データ整理
├── markdown_formatter.py      # Markdown変換
├── requirements.txt           # 依存関係
├── env_example.txt           # 環境変数例
└── README.md                 # このファイル
```

### 技術スタック

- **フロントエンド**: Streamlit
- **OCR**: Google Document AI
- **文字修正・要約**: OpenAI GPT-4
- **画像処理**: OpenCV, PIL
- **データ処理**: Pandas, NumPy
- **認証**: Google Auth

### 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHub の Issues ページで報告してください。
