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

# ファイル名とURLのペアを配列に格納
declare -A FILES=(
    ["VanillaCord.jar"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/main/assets/VanillaCord.jar"
    ["start.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/config/start.sh"
    ["stop.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/config/stop.sh"
    ["eula.txt"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/config/eula.txt"
    ["server.properties"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/config/server.properties"
    ["TEST-25565.service"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/config/TEST-25565.service"
)

# ループで各ファイルをダウンロード
for FILENAME in "${!FILES[@]}"; do
    URL="${FILES[$FILENAME]}"
    # ファイルごとに保存先ディレクトリを振り分け
    if [[ "$FILENAME" == "VanillaCord.jar" ]]; then
        DEST_DIR="${MC_VANILLA_DIR}"
    else
        DEST_DIR="${MC_CONF_DIR}"
    fi

    if [ ! -f "${DEST_DIR}/${FILENAME}" ]; then
        echo "[INFO] ${DEST_DIR} に ${FILENAME} が見つかりませんでした。ダウンロードを開始します。" | tee -a "$LOG_FILE"
        sudo curl -o "${DEST_DIR}/${FILENAME}" "$URL"
        echo "[INFO] ${FILENAME} のダウンロードが完了しました。" | tee -a "$LOG_FILE"
    else
        echo "[INFO] ${FILENAME} は既に存在します。" | tee -a "$LOG_FILE"
    fi
done

echo "[INFO] Step 4: 完了しました。" | tee -a "$LOG_FILE"

# ==================================
# マイクラサーバー操作スクリプトのDL
# ==================================
echo "[INFO] Step 5: マイクラサーバーを操作するスクリプトをダウンロードします。" | tee -a "$LOG_FILE"

# ファイル名とURLのペアを配列に格納
declare -A FILES=(
    ["CREATE-SERVER.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/operation-script/CREATE-SERVER.sh"
    ["CREATE-SERVER-SUDO.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/operation-script/CREATE-SERVER-SUDO.sh"
    ["DELETE-SERVER-SUDO.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/operation-script/DELETE-SERVER-SUDO.sh"
    ["CONTROL-SERVER-SUDO.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/operation-script/CONTROL-SERVER-SUDO.sh"
    ["GIVE-OP.sh"]="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/operation-script/GIVE-OP.sh"
)

# ループで各ファイルをダウンロード
for FILENAME in "${!FILES[@]}"; do
    URL="${FILES[$FILENAME]}"
    # ファイルごとに保存先ディレクトリを振り分け
    DEST_DIR="${MC_SH_DIR}"

    if [ ! -f "${DEST_DIR}/${FILENAME}" ]; then
        echo "[INFO] ${DEST_DIR} に ${FILENAME} が見つかりませんでした。ダウンロードを開始します。" | tee -a "$LOG_FILE"
        sudo curl -o "${DEST_DIR}/${FILENAME}" "$URL"
        echo "[INFO] ${FILENAME} のダウンロードが完了しました。" | tee -a "$LOG_FILE"
    else
        echo "[INFO] ${FILENAME} は既に存在します。" | tee -a "$LOG_FILE"
    fi
done
echo "[INFO] Step 5: 完了しました。" | tee -a "$LOG_FILE"

# ==================================
# マイクラサーバー権限設定
# ==================================

echo "[INFO] Step 6: ${MC_DIR} 配下をすべて ${MC_USER} 所有にします。" | tee -a "$LOG_FILE"
sudo chown -R "${MC_USER}:${MC_USER}" "${MC_DIR}"
find "${MC_SH_DIR}" -name "*.sh" -exec sudo chmod 774 {} \;

echo "[INFO] Step 6: 権限と所有者の設定が完了しました。" | tee -a "$LOG_FILE"

# ==================================
# マイクラサーバーUFWの設定
# ==================================

echo "[INFO] Step 7: UFW（ファイアウォール）の設定を行います。" | tee -a "$LOG_FILE"

UFW_APP_URL="https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/setup-script/dc-mc-admin"
UFW_APP_DIR="/etc/ufw/applications.d"
UFW_APP_NAME="dc-mc-admin"

# UFWAPPファイルがあるか判定
if [ ! -f "${UFW_APP_DIR}/${UFW_APP_NAME}" ]; then
    echo "[INFO] ${UFW_APP_DIR} に ${UFW_APP_NAME} が見つかりませんでした。ダウンロードを開始します。" | tee -a "$LOG_FILE"
    sudo curl -o "/tmp/${UFW_APP_NAME}" "$UFW_APP_URL"
    sudo mv "/tmp/${UFW_APP_NAME}" "${UFW_APP_DIR}/${UFW_APP_NAME}"
    echo "[INFO] ${UFW_APP_NAME} のダウンロードと移動が完了しました。" | tee -a "$LOG_FILE"

    # ufw-appの適用
    echo "[INFO] UFWアプリケーションプロファイルを登録し、ルールを適用します。" | tee -a "$LOG_FILE"
    sudo ufw app update "${UFW_APP_NAME}" | tee -a "$LOG_FILE"
    sudo ufw allow "${UFW_APP_NAME}" | tee -a "$LOG_FILE"
    sudo ufw reload | tee -a "$LOG_FILE" | tee -a "$LOG_FILE"
    echo "[INFO] UFW設定が更新されました。" | tee -a "$LOG_FILE"

else
    echo "[INFO] ${UFW_APP_NAME} は既に存在します。" | tee -a "$LOG_FILE"
fi

echo "[INFO] すべてのセットアップが完了しました。" | tee -a "$LOG_FILE"