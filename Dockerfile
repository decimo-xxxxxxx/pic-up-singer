FROM python:3.11-slim

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY . .

# ヘルスチェック用ポート開放
EXPOSE 8080

# 起動コマンド
CMD ["python", "core.py"]