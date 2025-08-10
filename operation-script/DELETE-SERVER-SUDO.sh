#!/bin/bash

# sudoなどrootユーザーで実行されているか判断する処理
if [ "`whoami`" != "root" ]; then
  echo "Please use root!"
  exit 1
fi

# 引数のエラーを判定
if [ "$#" -ne 1 ]; then
    echo "エラー：引数の数が正しくありません。" >&2
    echo "使用法：$0 <サーバーポート番号>" >&2
    exit 1
fi

# 環境変数を設定
SV_PORT="$1" # ポート番号を取得
SCREEN_NAME="SV-${SV_PORT}"
SV_DIR_PATH="/minecraft/servers/${SCREEN_NAME}"
SV_SERVICE_FILE_PATH="/etc/systemd/system"

# ディレクトリがあるかどうか判定
if [ -d ${SV_DIR_PATH} ]; then
  # サービスファイルが存在するか確認
  if ! systemctl cat "${SCREEN_NAME}.service" &>/dev/null; then
    # 存在しない場合
    echo "[ERROR] サービスファイルが見つかりませんでした。処理を終了します。"
    exit 1
  fi
  # ディレクトリもサービスも存在する場合
  if ! systemctl stop "${SCREEN_NAME}.service"; then
    echo "[ERROR] サービス ${SCREEN_NAME}.serivce の停止に失敗しました。処理を終了します。"
    exit 1
  fi
  # サービスが停止するまで待機
  while systemctl is-active "${SCREEN_NAME}.service" >/dev/null 2>&1; do
    echo "[INFO] サービス ${SCREEN_NAME}.service がまだ稼働中です。１秒待機します・・・"
    sleep 1s
  done
  # サービスの無効化を実行
  if ! systemctl disable "${SCREEN_NAME}.service"; then
    echo "[ERROR] サービス ${SCREEN_NAME}.service の無効化に失敗しました。"
    exit 1
  fi
  # サービスが停止したあと、ディレクトリの処理
  if ! rm -rf "${SV_DIR_PATH}"; then
    echo "[ERROR] サーバーディレクトリ ${SCREEN_NAME} の削除に失敗しました。"
    exit 1
  fi
  # サービスファイルを削除する処理
  if ! rm -rf "${SV_SERVICE_FILE_PATH}/${SCREEN_NAME}.service";then
    echo "[ERROR] サービスファイル ${SCREEN_NAME}.service の削除に失敗しました。"
    exit 1
  fi
  echo "[INFO] 削除処理がすべて完了しました。"
  exit 0
else
  # ない時点で処理を終了
  echo "[ERROR] 対象ディレクトリが見つかりませんでした。処理を終了します。"
  exit 1
fi