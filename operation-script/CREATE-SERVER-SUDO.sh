#!/bin/bash

# sudoなどrootユーザーで実行されているか判断する処理
if [ "`whoami`" != "root" ]; then
  echo "Please use root!"
  exit 1
fi

# 引数のエラーを判定
if [ "$#" -ne 4 ]; then
    echo "エラー：引数の数が正しくありません。" >&2
    echo "使用法：$0 <サーバー名> <サーバータイプ> <サーバーバージョン> <サーバーポート番号>" >&2
    exit 1
fi

# 引数から環境設定
SV_NAME="$1" # サーバー名
SV_TYPE="$2" # サーバータイプ
SV_VER="$3" # サーバーバージョン
SV_PORT="$4" # サーバーポート番号

# 変数
SCREEN_NAME="SV-${SV_PORT}"
SV_DIR_PATH="/minecraft/servers/SV-${SV_PORT}" # 作成するサーバー
CURRENT_DATETIME=$(date '+%Y-%m-%d_%H-%M-%S') # 実行時の日付

# 設定ファイル
SV_CONFIG_FILE_PATH="/minecraft/config"
SV_SERVICE_FILE_PATH="/etc/systemd/system"

# 雛形のserviceファイルをコピー
cp ${SV_CONFIG_FILE_PATH}/TEST-25565.service ${SV_SERVICE_FILE_PATH}/${SCREEN_NAME}.service
sed -i "s/TEST-25565/${SCREEN_NAME}/g" ${SV_SERVICE_FILE_PATH}/${SCREEN_NAME}.service
systemctl enable ${SCREEN_NAME}.service
systemctl start ${SCREEN_NAME}.service

# 起動できたか判断、５秒待ちましょうね
sleep 5s
if systemctl is-active --quiet ${SCREEN_NAME}.service; then
    # 問題なく稼働中
    exit 0
else
    # 起動に失敗
    exit 1
fi