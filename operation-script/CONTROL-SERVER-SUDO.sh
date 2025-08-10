#!/bin/bash

# sudoなどrootユーザーで実行されているか判断する処理
if [ "`whoami`" != "root" ]; then
  echo "Please use root!"
  exit 1
fi

# 引数のエラーを判定
if [ "$#" -ne 2 ]; then
    echo "エラー：引数の数が正しくありません。" >&2
    echo "使用法：$0 <サーバーポート番号> <操作名称>" >&2
    exit 1
fi

# 環境変数を設定
SV_PORT="$1" # ポート番号を取得
SV_CONTROL="$2" # 操作名称を取得
SCREEN_NAME="SV-${SV_PORT}"
SV_DIR_PATH="/minecraft/servers/${SCREEN_NAME}"

# サービスファイルが存在するか確認
  if ! systemctl cat "${SCREEN_NAME}.service" &>/dev/null; then
    # 存在しない場合
    echo "[ERROR] サービスファイルが見つかりませんでした。処理を終了します。"
    exit 1
  fi

# 処理内容を判定
if [ ${SV_CONTROL} == 'start' ]; then # 起動処理
    if ! systemctl start "${SCREEN_NAME}.service"; then
        echo "[ERROR] サービス ${SCREEN_NAME}.serivce の開始に失敗しました。処理を終了します。"
        exit 1
    fi
    echo "[INFO] ${SCREEN_NAME}サービスを 起動 しました。"
    exit 0

elif [ ${SV_CONTROL} == 'restart' ]; then # 再起動処理
    if ! systemctl restart "${SCREEN_NAME}.service"; then
        echo "[ERROR] サービス ${SCREEN_NAME}.serivce の再起動に失敗しました。処理を終了します。"
        exit 1
    fi
    echo "[INFO] ${SCREEN_NAME}サービスを 再起動 しました。"
    exit 0

elif [ ${SV_CONTROL} == 'stop' ]; then # 停止処理
    if ! systemctl stop "${SCREEN_NAME}.service"; then
        echo "[ERROR] サービス ${SCREEN_NAME}.serivce の停止に失敗しました。処理を終了します。"
        exit 1
    fi
    echo "[INFO] ${SCREEN_NAME}サービスを 停止 しました。"
    exit 0

else
    echo "[ERROR] 処理内容が不明です。処理を終了します。"
    exit 1
fi