"""
設定ファイル（st.secrets専用）
"""
import streamlit as st

# --- st.secretsからすべて取得する ---
# .envやos.getenvは一切使わない

# OpenAI API設定
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
OPENAI_MODEL_TEXT = "gpt-4o"

# Google Document AI設定
GOOGLE_CLOUD_PROJECT_ID = st.secrets["GOOGLE_CLOUD_PROJECT_ID"]
GOOGLE_CLOUD_LOCATION = st.secrets.get("GOOGLE_CLOUD_LOCATION", "us")
GOOGLE_CLOUD_PROCESSOR_ID = st.secrets["GOOGLE_CLOUD_PROCESSOR_ID"]
GOOGLE_APPLICATION_CREDENTIALS = st.secrets["GOOGLE_APPLICATION_CREDENTIALS"]
GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT = st.secrets.get("GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT", "us-documentai.googleapis.com")

# サービスアカウントJSONはst.secrets["google_service_account"]で管理
# 例: st.secrets["google_service_account"]

# ファイルアップロード設定
MAX_FILE_SIZE_MB = int(st.secrets.get("MAX_FILE_SIZE_MB", 10))
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt']

# OCR処理設定
TEMPERATURE_CORRECTION = float(st.secrets.get("TEMPERATURE_CORRECTION", 0.3))
TEMPERATURE_ORGANIZATION = float(st.secrets.get("TEMPERATURE_ORGANIZATION", 0.7))

# 並列処理設定
MAX_PARALLEL_REQUESTS = int(st.secrets.get("MAX_PARALLEL_REQUESTS", 10))

# --- 以下はプロンプトテンプレート（st.secretsで管理しなくてOK） ---
# OpenAI Vision機能は廃止されたため、OCRプロンプトは不要

CORRECTION_SYSTEM_PROMPT = """```xml
<instructions>
{ocr_result}のJSONデータの中に含まれる文字列の誤認識を修正してください。以下の手順に従って、適切な修正を行ってください。

1. JSONデータ内の文字列を解析し、文脈を考慮して誤認識された可能性のある文字を特定してください。
2. ありえない文字や意味が通らない単語が含まれている場合、前後の文脈を踏まえて適切な修正を行ってください。
3. 修正の際には参考資料を考慮し、正しい表記を確認してください。
4. 可能な限り自然な文章になるように修正し、意味が通るようにしてください。
5. 出力にはXMLタグを含めず、修正後のJSONのみを返してください。
</instructions>
```"""

ORGANIZATION_SYSTEM_PROMPT = """```xml
<instruction>
あなたのタスクは、提供されたデータを基に、地域の課題ごとに整理し、それぞれの立場（個人、地域、行政、その他）からの解決策や関わり方を明確にすることです。以下の手順に従ってください。

1. **データの統合と整理**
   - データには、各参加者の意見が含まれています。
   - これらの意見を統合し、類似する内容をまとめ、課題ごとに整理してください。
   - 可能な限り元のデータの意味や表現を変えずに補足しながら整理してください。
   - **重要: 文字数が増えてもよいので、元の内容・表現・細かいニュアンスを絶対に省略せず、すべて保持したまま課題ごとに整理してください。要約や省略は行わないでください。**

2. **課題ごとの分類**
   - 各課題について、以下のカテゴリに分類してください：
     - `problem`: 地域の課題
     - `personal`: 個人としてできること
     - `community`: 地域としてできること
     - `gov`: 行政の役割
     - `others`: その他（民間等）

3. **出力フォーマット**
   - 出力はJSON形式で提供してください。
   - 各課題を辞書形式で整理し、リストとして出力してください。
   - `gov` などの各カテゴリの内容は、短い文章のリストとして表現してください。
   - XMLタグは含めないでください。

</instruction>
```"""

MARKDOWN_SYSTEM_PROMPT = """```xml
<instructions>
以下の手順に従って、提供されたJSONデータをMarkdown形式に変換してください。

1. 入力されたJSONデータを解析し、各課題を識別する。
2. 各課題を `##` (h2) 見出しとしてMarkdownに変換する。
3. 課題ごとに「個人としてできること」「地域としてできること」「行政の役割」「その他」の視点を `###` (h3) 見出しとして整理する。
4. 各視点ごとの具体的な行動を箇条書き (`- `) でリスト化する。
5. 出力にはXMLタグを含めず、純粋なMarkdown形式で整形する。

以下のフォーマットに従って出力してください：

```
## 課題のタイトル

### 個人としてできること
- 具体的な行動

### 地域としてできること
- 具体的な行動

### 行政の役割
- 具体的な行動

### その他
- 具体的な行動
```

</instructions>
```"""
