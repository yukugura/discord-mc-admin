#!/bin/bash
set -e
# ===================================
# ユーザー向け初期セットアップスクリプト
# ===================================

# sudoなどrootユーザーで実行されているか判断する処理
if [ "`whoami`" != "root" ]; then
  echo "Please use root!"
  exit 1
fi

# ログファイル
LOG_FILE="/var/log/db-server-setup.log"

# ==================================
# パッケージの更新とインストール
# ==================================
echo "[INFO] Step 1: パッケージの更新とMySQLのインストールを開始します。" | tee -a "$LOG_FILE"
sudo apt-get update -y | tee -a "$LOG_FILE"
sudo apt-get install -y mariadb-server | tee -a "$LOG_FILE"
echo "[INFO] パッケージのインストールが完了しました。" | tee -a "$LOG_FILE"

# ==================================
# MySQLのセットアップ
# ==================================
echo "[INFO] Step 2: MySQLデータベースのセットアップを開始します。" | tee -a "$LOG_FILE"
# データベース接続情報
DB_USER="minecraft" # .envと同名に設定
DB_PASS="Xcpw3GTBRJQqjeb2" # 適切なパスワードに変更してください
DB_NAME="mc_admin_db" # .envと同名に設定

# SQLコマンド
SQL_COMMANDS=$(cat <<EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF
)

# MySQLにログインしてSQLを実行
sudo mysql -u root -e "$SQL_COMMANDS"

echo "[INFO] データベース '$DB_NAME' とユーザー '$DB_USER' を作成しました。" | tee -a "$LOG_FILE"

# ==================================
# テーブルの作成
# ==================================
echo "[INFO] Step 3: 必要なテーブルを作成します。" | tee -a "$LOG_FILE"

# GitHubのURLからSQLファイルをダウンロード
SQL_URL="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/create-table.sql"
SQL_FILE="/tmp/create-table.sql"

echo "[INFO] SQLファイルをダウンロード中..." | tee -a "$LOG_FILE"
sudo curl -o "$SQL_FILE" "$SQL_URL"

# ダウンロードしたSQLファイルを使ってテーブルを作成
if [ -f "$SQL_FILE" ]; then
    sudo mysql -u root -p"$DB_PASS" "$DB_NAME" < "$SQL_FILE"
    echo "[INFO] テーブルの作成と初期データの挿入が完了しました。" | tee -a "$LOG_FILE"
else
    echo "[ERROR] SQLファイルのダウンロードに失敗しました。" | tee -a "$LOG_FILE"
    exit 1
fi

# ==================================
# 外部からのDBアクセス設定
# ==================================
echo "[INFO] Step 4: 外部からのDBアクセス設定を行います。" | tee -a "$LOG_FILE"
read -p "[Q/A ] DBに外部からアクセスを許可しますか？ (y/N): " -n 1 -r REPLY
echo # 新しい行へ

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[INFO] 外部アクセスを許可するように設定します。" | tee -a "$LOG_FILE"
    # MySQLの設定ファイル (my.cnf) を編集
    sudo sed -i 's/^bind-address\s*=.*/bind-address = 0.0.0.0/' /etc/mysql/mariadb.conf.d/50-server.cnf
    
    # ユーザーの権限を更新
    SQL_EXTERNAL_ACCESS=$(cat <<EOF
USE $DB_NAME;
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';
FLUSH PRIVILEGES;
EOF
)
    sudo mysql -u root -e "$SQL_EXTERNAL_ACCESS"
    
    # MySQLサービスを再起動
    sudo systemctl restart mariadb
    echo "[INFO] 外部からのDBアクセスが有効になりました。" | tee -a "$LOG_FILE"
else
    echo "[INFO] 外部アクセスは無効のままです。" | tee -a "$LOG_FILE"
fi

echo "[INFO] セットアップが完了しました！" | tee -a "$LOG_FILE"
echo "[INFO] セットアップログを ${LOG_FILE} に格納しました。"
