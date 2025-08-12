# discord-mc-admin
discord内でマインクラフトサーバーを管理します

# リリース
すべてのリリースは以下の場所にあります。

・github：https://github.com/yukugura/discord-mc-admin/releases/

# How to use

## 手順 １ [.envファイルの初期設定]
プロジェクトを実行するには、環境変数の設定が必要です。
`.env.sample`ファイルをコピーし、`.env`という名前で保存してください。

`DISCORD_BOT_TOKEN="TOKEN-HERE"`

Discord-Developper-Portalから取得したBotのトークンを `TOKEN-HERE` に貼り付けてください。

`DOMAIN_NAME="example.com"`

運用するドメインを指定してください。BOTの動作に直接関与するものではありませんが、サーバー作成後にBOTからユーザーへ返信されるメッセージにここで指定したドメインに生成したサーバーのサブドメインを合わせて通知するようになっています。

`ADMIN_KEY="password"`

/admin コマンドを入力すると、ADMINキー入力モーダルが表示され、ここで設定した値と検証を行うようになっています。

`PREMIUM_KEY="password"`

/premium コマンドを入力すると、PREMIUMキー入力モーダルが表示され、ここで設定した値と検証を行うようになっています。

# ポートを変更する場合、セットアップスクリプトの中の設定も変更する必要があります。
SV_MAX_PORT="25510"
SV_MIN_PORT="25501"
# DB接続用設定（NAME、PORT、USER、PASSを変更する場合、セットアップスクリプトの中の設定も変更する必要があります。）
DB_HOST="192.168.xxx.xxx"
DB_NAME="mc_admin_db"
DB_PORT="3306"
DB_USER="minecraft" 
DB_PASS="Xcpw3GTBRJQqjeb2"
# マイクラサーバーSSH接続用設定
SSH_HOST="192.168.xxx.xxx"
SSH_PORT="22"
SSH_USER="minecraft"
SSH_PASS="password"
SSH_KEY_PATH="/home/you/private-key"
# 各コマンドのタイムアウト時間（秒）
TIMEOUT_SEC="120"






### 外部ソフトウェアの利用について

このプロジェクトは、プロキシ機能を提供するために以下の外部ソフトウェアを利用しています。
-   **BungeeCord**:
    -   **開発元**: SpigotMC
    -   **ライセンス**: GNU General Public License, Version 3 (GPL-3.0)
    -   **ライセンス全文**: [https://github.com/SpigotMC/BungeeCord/blob/master/LICENSE.txt](https://github.com/SpigotMC/BungeeCord/blob/master/LICENSE.txt)
    -   **著作権**: © 2013-2023 SpigotMC

-   **Minecraft Server Software**:
    -   **開発元**: Mojang Studios
    -   **ライセンス**: Minecraft End User License Agreement (EULA)
    -   **ライセンス全文**: [https://www.minecraft.net/eula](https://www.minecraft.net/eula)
    -   **著作権**: © 2009-2023 Mojang AB

-   **VanillaCord.jar**:
    -   **開発元**: [https://github.com/ME1312/VanillaCord](https://github.com/ME1312/VanillaCord)
    -   **ライセンス**: Mozilla Public License, Version 2.0 (MPL-2.0)
    -   **ライセンス全文**: [MPL-2.0.txtへのリンク](https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/assets/MPL-2.0.txt)
    -   **著作権**: © 2021-2023 ME1312
