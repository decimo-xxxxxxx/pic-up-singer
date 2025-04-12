FROM python:3.11-slim

WORKDIR /app

# タイムゾーン設定
ENV TZ=Asia/Tokyo
RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY . .

# ヘルスチェック用エンドポイント
EXPOSE 8080

CMD ["python", "main.py"]