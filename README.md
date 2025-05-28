# 改善提案シート文字起こしツール

住民会議で回収された改善提案シートの手書き文字を OCR で読み取り、地域の課題ごとに整理して Markdown 形式で出力するローカルツールです。

## 機能

- 📸 **画像 OCR 処理**: OpenAI GPT-4 Vision を使用した手書き文字認識
- 🔧 **文字認識修正**: 誤認識の自動修正
- 📊 **課題分類**: 地域課題ごとの自動整理
- 📝 **Markdown 出力**: 見やすい形式での結果出力
- 🌐 **Web インターフェース**: Streamlit による直感的な操作

## 必要な環境

- Python 3.8 以上
- OpenAI API キー

## インストール

1. **リポジトリのクローン**

   ```bash
   git clone <repository-url>
   cd OCR_test
   ```

2. **依存関係のインストール**

   ```bash
   pip install -r requirements.txt
   ```

3. **環境変数の設定**

   ```bash
   # .envファイルを作成
   cp env_example.txt .env

   # .envファイルを編集してOpenAI APIキーを設定
   OPENAI_API_KEY=your_actual_api_key_here
   ```

## 使用方法

1. **アプリケーションの起動**

   ```bash
   streamlit run app.py
   ```

2. **ブラウザでアクセス**

   - 自動的にブラウザが開きます（通常は http://localhost:8501）

3. **ファイルのアップロード**

   - **改善提案シート**: 手書きの画像ファイル（必須）
   - **議事録**: 参考資料のテキストファイル（オプション）
   - **投影資料**: 参考資料のテキストファイル（オプション）

4. **処理の実行**

   - 「🚀 処理開始」ボタンをクリック
   - 処理状況がリアルタイムで表示されます

5. **結果の確認とダウンロード**
   - 処理結果が Markdown 形式で表示されます
   - 「📥 Markdown ファイルをダウンロード」でファイル保存

## 対応ファイル形式

### 画像ファイル（改善提案シート）

- JPG, JPEG, PNG, GIF, WEBP, SVG
- 最大ファイルサイズ: 10MB

### テキストファイル（参考資料）

- TXT, MD
- 最大ファイルサイズ: 10MB

## 処理フロー

```
画像アップロード
    ↓
OCR処理（GPT-4 Vision）
    ↓
文字認識修正（GPT-4）
    ↓
課題ドリブン整理（GPT-4）
    ↓
Markdown形式変換
    ↓
結果出力・ダウンロード
```

## 出力形式

処理結果は以下の構造で Markdown 形式で出力されます：

```markdown
## 課題のタイトル

### 個人としてできること

- 具体的な行動 1
- 具体的な行動 2

### 地域としてできること

- 具体的な行動 1
- 具体的な行動 2

### 行政の役割

- 具体的な行動 1
- 具体的な行動 2

### その他

- 具体的な行動 1
- 具体的な行動 2
```

## 設定

### config.py での設定項目

- **API モデル**: 使用する OpenAI モデルの指定
- **温度パラメータ**: AI 応答の創造性レベル
- **ファイルサイズ制限**: アップロード可能なファイルサイズ
- **並列処理数**: 同時処理可能な画像数

### 主な設定値

```python
OPENAI_MODEL_VISION = "gpt-4o"      # Vision用モデル
OPENAI_MODEL_TEXT = "gpt-4o"        # テキスト処理用モデル
MAX_FILE_SIZE_MB = 10               # 最大ファイルサイズ
TEMPERATURE_OCR = 0.2               # OCR処理の温度
TEMPERATURE_CORRECTION = 0.3        # 修正処理の温度
TEMPERATURE_ORGANIZATION = 0.7      # 整理処理の温度
```

## トラブルシューティング

### よくある問題

1. **API キーエラー**

   - `.env`ファイルに OpenAI API キーが正しく設定されているか確認
   - API キーに十分なクレジットがあるか確認

2. **画像認識エラー**

   - 画像が鮮明で読み取り可能か確認
   - ファイルサイズが制限内か確認
   - 対応形式の画像ファイルか確認

3. **処理が遅い**
   - OpenAI API のレート制限により処理が遅くなる場合があります
   - 画像数を減らして試してください

### ログの確認

詳細な処理状況は「🔍 詳細情報」セクションで確認できます：

- OCR 結果の生データ
- 修正処理の結果
- データ整理の結果
- 検証結果

## 開発者向け情報

### ファイル構成

```
OCR_test/
├── app.py                  # Streamlitメインアプリ
├── config.py              # 設定ファイル
├── ocr_processor.py       # OCR処理クラス
├── text_corrector.py      # 文字修正クラス
├── data_organizer.py      # データ整理クラス
├── markdown_formatter.py  # Markdown出力クラス
├── requirements.txt       # 依存関係
├── design_doc.md         # 設計ドキュメント
└── README.md             # このファイル
```

### クラス構成

- **OCRProcessor**: 画像からのテキスト抽出
- **TextCorrector**: OCR 結果の誤認識修正
- **DataOrganizer**: 課題ドリブンでのデータ整理
- **MarkdownFormatter**: 最終結果の Markdown 変換

### カスタマイズ

プロンプトテンプレートは`config.py`で定義されており、用途に応じて調整可能です。

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHub の Issues ページでお知らせください。
