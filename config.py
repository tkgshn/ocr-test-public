"""
設定ファイル
"""
import os
from dotenv import load_dotenv

# 環境変数を読み込み（.envファイルがある場合のみ）
if os.path.exists('.env'):
    load_dotenv()

# Streamlit secretsを使用する場合の処理
try:
    import streamlit as st
    # st.secretsが利用可能な場合
    if hasattr(st, 'secrets'):
        # OpenAI API設定（文字修正と要約のみ使用）
        OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        
        # Google Document AI設定
        GOOGLE_CLOUD_PROJECT_ID = st.secrets.get("GOOGLE_CLOUD_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT_ID"))
        GOOGLE_CLOUD_LOCATION = st.secrets.get("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "us"))
        GOOGLE_CLOUD_PROCESSOR_ID = st.secrets.get("GOOGLE_CLOUD_PROCESSOR_ID", os.getenv("GOOGLE_CLOUD_PROCESSOR_ID"))
        GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT = st.secrets.get("GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT", os.getenv("GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT", "us-documentai.googleapis.com"))
    else:
        # st.secretsが利用できない場合は環境変数から読み込み
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        GOOGLE_CLOUD_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        GOOGLE_CLOUD_PROCESSOR_ID = os.getenv("GOOGLE_CLOUD_PROCESSOR_ID")
        GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT = os.getenv("GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT", "us-documentai.googleapis.com")
except ImportError:
    # Streamlitがインストールされていない場合は環境変数から読み込み
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_CLOUD_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
    GOOGLE_CLOUD_PROCESSOR_ID = os.getenv("GOOGLE_CLOUD_PROCESSOR_ID")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT = os.getenv("GOOGLE_CLOUD_DOCUMENTAI_ENDPOINT", "us-documentai.googleapis.com")

OPENAI_MODEL_TEXT = "gpt-4o"
# Vision機能は廃止

# ファイルアップロード設定
MAX_FILE_SIZE_MB = 10
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
ALLOWED_DOCUMENT_EXTENSIONS = ['.txt', '.pdf', '.docx', '.md']

# OCR処理設定
TEMPERATURE_CORRECTION = 0.3
TEMPERATURE_ORGANIZATION = 0.7

# 並列処理設定
MAX_PARALLEL_REQUESTS = 10

# プロンプトテンプレート
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
