# ベースイメージ
FROM python:3.11

# 作業ディレクトリ設定
WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# タイムゾーン設定
RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

# 起動コマンド
CMD ["python", "src/main.py"]