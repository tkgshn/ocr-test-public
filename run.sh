#!/bin/bash

# 改善提案シート文字起こしツール起動スクリプト

echo "🤖 改善提案シート文字起こしツール"
echo "================================"

# 仮想環境の確認
if [ ! -d "venv" ]; then
    echo "仮想環境が見つかりません。セットアップを実行します..."
    python3 -m venv venv
    echo "仮想環境を作成しました。"
fi

# 依存関係のインストール確認
if [ ! -f "venv/lib/python*/site-packages/streamlit/__init__.py" ]; then
    echo "依存関係をインストールします..."
    venv/bin/python -m pip install -r requirements.txt
fi

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo "⚠️  .envファイルが見つかりません。"
    echo "env_example.txtを参考に.envファイルを作成し、OpenAI APIキーを設定してください。"
    echo ""
    echo "例："
    echo "cp env_example.txt .env"
    echo "# .envファイルを編集してAPIキーを設定"
    echo ""
    read -p "続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🚀 アプリケーションを起動します..."
echo "ブラウザで http://localhost:8501 にアクセスしてください"
echo ""

# Streamlitアプリケーションの起動
venv/bin/python -m streamlit run app.py
