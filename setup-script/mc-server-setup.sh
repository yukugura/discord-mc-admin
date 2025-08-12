#!/bin/bash
set -e
# ==================================
# マイクラサーバー側初期セットアップ
# ==================================

# sudoなどrootユーザーで実行されているか判断する処理
if [ "`whoami`" != "root" ]; then
  echo "Please use root!"
  exit 1
fi

# ログファイル
LOG_FILE="/var/log/mc-server-setup.log"

# ==================================
# パッケージの更新とインストール
# ==================================
echo "[INFO] Step 1: パッケージの更新と Openjdk21 のインストールを開始します。" | tee -a "$LOG_FILE"
sudo apt-get update -y | tee -a "$LOG_FILE"
sudo apt-get install -y openjdk-21-jdk | tee -a "$LOG_FILE"
echo "[INFO] パッケージのインストールが完了しました。" | tee -a "$LOG_FILE"

# ==================================
# マイクラサーバー操作用ユーザーの作成
# ==================================
# 管理ユーザー名
MC_USER="minecraft"

echo "[INFO] Step 2: マイクラサーバー管理用ユーザーのセットアップを開始します。" | tee -a "$LOG_FILE"
# ユーザーが存在するかどうか判定
if id "${MC_USER}" &>/dev/null; then
    # ユーザーが存在する場合
    echo "[INFO] ユーザー ${MC_USER} は既に存在します。" | tee -a "$LOG_FILE"
else
    # ユーザー存在しない場合
    read -p "[Q/A ] ユーザー ${MC_USER} を作成しますか？ (y/N): " -n 1 -r REPLY
    echo # 新しい行へ

    if [[ ${REPLY} =~ ^[Yy]$ ]]; then
        # 作成する場合
        echo "[INFO] ユーザー ${MC_USER} を作成し、sudo権限を付与します。" | tee -a "$LOG_FILE"
        sudo useradd -m -s /bin/bash "${MC_USER}" | tee -a "$LOG_FILE"
        sudo usermod -aG sudo "${MC_USER}" | tee -a "$LOG_FILE"
        echo "[INFO] ユーザー ${MC_USER} のパスワードを設定します。" | tee -a "$LOG_FILE"
        sudo passwd "${MC_USER}" | tee -a "$LOG_FILE"
        echo "[INFO] ユーザー ${MC_USER} の作成が完了しました。" | tee -a "$LOG_FILE"
    else
        # 作成しない場合
        echo "[INFO] ユーザーの作成をキャンセルしました。" | tee -a "$LOG_FILE"
        read -p "[Q/A ] 代わりに、どの既存sudoユーザーを管理用に使用しますか？：" ADMIN_USER

        # 入力されたユーザーが存在するかどうか
        if id "${ADMIN_USER}" &>/dev/null; then
            echo "[INFO] 既存ユーザー ${ADMIN_USER} を使用して処理を進めます。" | tee -a "$LOG_FILE"
            MC_USER="${ADMIN_USER}" | tee -a "$LOG_FILE" # ユーザー名代入
        else
            echo "[ERROR] 指定されたユーザー ${ADMIN_USER} は存在しませんでした。\nスクリプトを終了します。" | tee -a "$LOG_FILE"
            exit 1
        fi
    fi
fi

# ==================================
# マイクラサーバーディレクトリを作成
# ==================================
echo "[INFO] Step 3: マイクラサーバーディレクトリを作成します。" | tee -a "$LOG_FILE"
MC_DIR="/minecraft"
MC_SV_DIR="${MC_DIR}/servers"
MC_SH_DIR="${MC_DIR}/scripts"
MC_CONF_DIR="${MC_DIR}/config"
MC_ERROR_DIR="${MC_DIR}/error"
MC_VANILLA_DIR="${MC_DIR}/vanilla-source"

# 対象ディレクトリが存在するかどうか
if [ ! -d "${MC_DIR}" ]; then
    # 存在しない場合
    echo "[INFO] ディレクトリ ${MC_DIR} を作成します。" | tee -a "$LOG_FILE"
    sudo mkdir -p "${MC_DIR}" "${MC_SV_DIR}" "${MC_SH_DIR}" "${MC_CONF_DIR}" "${MC_ERROR_DIR}" "${MC_VANILLA_DIR}"
    echo "[INFO] ディレクトリ構成が作成されました。" | tee -a "$LOG_FILE"
else
    # 存在する場合
    read -p "[Q/A ] ディレクトリ ${MC_DIR} 配下を既に作成済みですか (y/N): " -n 1 -r REPLY
    echo # 新しい行へ
    if [[ ! ${REPLY} =~ ^[Yy]$ ]]; then
        # ディレクトリが別に使われている場合（y以外が入力された場合）
        echo "[ERROR] 別の用途でディレクトリが使用されているため、処理を中断します。" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "[INFO] ディレクトリが作成済みのため、次の処理に移行します。" | tee -a "$LOG_FILE"
fi

# ==================================
# マイクラサーバー設定ファイルをDL
# ==================================
echo "[INFO] Step 4: マイクラサーバーで使用する各種設定ファイルをダウンロードします。" | tee -a "$LOG_FILE"
VANILLACORD_URL="https://raw.githubusercontent.com/yukugura/discord-mc-admin/main/assets/VanillaCord.jar"



if [ ! -f "${MC_VANILLA_DIR}/VanillaCord.jar" ]; then
    echo "[INFO] ${MC_VANILLA_DIR} に VanillaCord.jar が見つかりませんでした。ダウンロードを開始します。" | tee -a "$LOG_FILE"
    sudo curl -o "${MC_VANILLA_DIR}/VanillaCord.jar" "$VANILLACORD_URL"
    echo "[INFO] VanillaCord.jar のダウンロードが完了しました。" | tee -a "$LOG_FILE"
else
    echo "[INFO] VanillaCord.jar は既に存在します。" | tee -a "$LOG_FILE"
fi


