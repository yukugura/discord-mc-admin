#!/bin/bash

# 引数のエラーを判定
if [ "$#" -ne 2 ]; then
    echo "エラー：引数の数が正しくありません。" >&2
    echo "使用法：$0 <サーバーポート番号> <MCID>" >&2
    exit 1
fi

# 環境設定
SV_PORT="$1"
MCID="$2"
SCREEN_NAME="SV-${SV_PORT}"

# サービスが稼働しているか確認
if systemctl is-active --quiet "${SCREEN_NAME}.service"; then
    # サービスが稼働している場合
    screen -S ${SCREEN_NAME} -X stuff "op ${MCID}\n"
    exit 0
else
    # サービスが稼働していない場合
    echo "サービス ${SCREEN_NAME}.service が稼働していません。"
    exit 1
fi