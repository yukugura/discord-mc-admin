#!/bin/bash
set -e
# 引数から環境設定
SV_NAME="$1" # サーバー名
SV_TYPE="$2" # サーバータイプ
SV_VER="$3" # サーバーバージョン
SV_PORT="$4" # サーバーポート番号
DL_URL="$5" # ダウンロードURL

# 引数のエラーを判定
if [ "$#" -ne 5 ]; then
    echo "エラー：引数の数が正しくありません。" >&2
    echo "使用法：$0 <サーバー名> <サーバータイプ> <サーバーバージョン> <サーバーポート番号>" >&2
    exit 1
fi

# コマンドのフルパスを記載
JDK21_PATH="/usr/lib/jvm/java-21-openjdk-amd64/bin/java"
SCREEN_PATH="/usr/bin/screen"

XMX_MEM="1024M"
XMS_MEM="1024M"
SCREEN_NAME="SV-${SV_PORT}"
SV_DIR_PATH="/minecraft/servers/SV-${SV_PORT}" # 作成するサーバー
SV_ERROR_DIR_PATH="/minecraft/error"
CURRENT_DATETIME=$(date '+%Y-%m-%d_%H-%M-%S') # 実行時の日付

# 設定ファイル
SV_CONFIG_FILE_PATH="/minecraft/config"
SV_SOURCE_FILE_PATH="/minecraft/${SV_TYPE}-source"
VANILLACORD_PATH="${SV_SOURCE_FILE_PATH}/VanillaCord.jar"

echo "[DEBUG] サーバー名：$SV_NAME"
echo "[DEBUG] サーバータイプ：$SV_TYPE"
echo "[DEBUG] サーバーバージョン：$SV_VER"
echo "[DEBUG] サーバーポート：$SV_PORT"

if [ -d ${SV_DIR_PATH} ]; then
    # ディレクトリが存在する
    mv ${SV_DIR_PATH} ${SV_ERROR_DIR_PATH}/SV-${SV_PORT}.${CURRENT_DATETIME}
fi
# ディレクトリが存在しない = ディレクトリを新規で作成できる
mkdir ${SV_DIR_PATH}

# sv_typeによって処理を変更
if [ "${SV_TYPE}" == "vanilla" ]; then
    
    # server.propertiesをconfigディレクトリから対象ディレクトリにコピーする
    cp ${SV_CONFIG_FILE_PATH}/server.properties ${SV_DIR_PATH}/server.properties
    # server.propertiesのserver-portを対象の番号を変更
    sed -i "s/server-port=.*/server-port=${SV_PORT}/" ${SV_DIR_PATH}/server.properties

    # eula.txtを対象ディレクトリにコピーするしてtrueにする処理
    cp ${SV_CONFIG_FILE_PATH}/eula.txt ${SV_DIR_PATH}/eula.txt
    sed -i "s/eula=.*/eula=true/" ${SV_DIR_PATH}/eula.txt

    # serverのjarが存在しない場合作成する
    if [ ! -f "${SV_SOURCE_FILE_PATH}/out/${SV_VER}.jar" ]; then
        # ファイルが存在しない場合
        cd "${SV_SOURCE_FILE_PATH}"
        ${JDK21_PATH} -jar "${VANILLACORD_PATH}" ${SV_VER}
    fi

elif [ "${SV_TYPE}" == "paper" ]; then

    # server.propertiesをconfigディレクトリから対象ディレクトリにコピーする
    cp ${SV_CONFIG_FILE_PATH}/server.properties ${SV_DIR_PATH}/server.properties
    # server.propertiesのserver-portを対象の番号を変更
    sed -i "s/server-port=.*/server-port=${SV_PORT}/" ${SV_DIR_PATH}/server.properties

    # eula.txtを対象ディレクトリにコピーするしてtrueにする処理
    cp ${SV_CONFIG_FILE_PATH}/eula.txt ${SV_DIR_PATH}/eula.txt
    sed -i "s/eula=.*/eula=true/" ${SV_DIR_PATH}/eula.txt

    # spigot.ymlをconfigディレクトリから対象ディレクトリにコピーする
    cp ${SV_CONFIG_FILE_PATH}/spigot.yml ${SV_DIR_PATH}/spigot.yml
    # sed -i "s/bungeecord: false/bungeecord: true/" ${SV_DIR_PATH}/spigot.yml

    # serverのjarが存在しない場合作成する
    if [ ! -f "${SV_SOURCE_FILE_PATH}/out/${SV_VER}.jar" ]; then
        # ファイルが存在しない場合
        cd "${SV_SOURCE_FILE_PATH}/out"
        wget -O ${SV_VER}.jar ${DL_URL}
    fi
    
elif [ "${SV_TYPE}" == "spigot" ]; then
    exit 1
elif [ "${SV_TYPE}" == "forge" ]; then
    exit 1
elif [ "${SV_TYPE}" == "fabric" ]; then
    exit 1
else
    echo "エラー：不明なサーバータイプです。" >&2
    exit 1
fi

# serverのjarファイルを対象ディレクトリにコピーして権限付与
cp ${SV_SOURCE_FILE_PATH}/out/${SV_VER}.jar ${SV_DIR_PATH}/${SV_VER}.jar
chmod 754 ${SV_DIR_PATH}/${SV_VER}.jar

# start.shを作成＆内容書き込み＆権限付与
echo "#!/bin/bash" > ${SV_DIR_PATH}/start.sh
echo "${SCREEN_PATH} -AdmSU ${SCREEN_NAME} ${JDK21_PATH} -Xmx${XMX_MEM} -Xms${XMS_MEM} -jar ${SV_DIR_PATH}/${SV_VER}.jar nogui" >> ${SV_DIR_PATH}/start.sh
chmod 754 ${SV_DIR_PATH}/start.sh

# stop.shをコピー＆内容書き換え＆権限付与
cp ${SV_CONFIG_FILE_PATH}/stop.sh ${SV_DIR_PATH}/stop.sh
sed -i "s/SCREEN_NAME=.*/SCREEN_NAME=\"${SCREEN_NAME}\"/" ${SV_DIR_PATH}/stop.sh
chmod 754 ${SV_DIR_PATH}/stop.sh

exit 0