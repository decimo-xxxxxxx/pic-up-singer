FROM python:3.12.2

WORKDIR /app

# タイムゾーン設定
ENV TZ=Asia/Tokyo
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY . .

# ヘルスチェック用ポート開放
EXPOSE 8080

# 起動コマンド
CMD ["python", "core.py"]