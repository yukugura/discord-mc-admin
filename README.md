# discord-mc-admin
discord内でマインクラフトサーバーを管理します

# リリース
すべてのリリースは以下の場所にあります。

・github：https://github.com/yukugura/discord-mc-admin/releases/

# 動作環境
### サーバー機

<details>  
    
- マイクラ鯖
    -    OS：Ubuntu 24.04.2 LTS
    -    CPU：16c
    -    RAM：16GB
    -    USER：minecraft
- Discordボット鯖
    -    OS：Ubuntu 24.04.2 LTS
    -    CPU：4c
    -    RAM：4GB
    -    USER：任意
- DB鯖
    -    OS：Ubuntu 24.04.2 LTS
    -    CPU：4c
    -    RAM：4GB
    -    USER：任意
</details>



### Pythonライブラリ
-   python-dotenv: 1.1.1
-   discord.py: 2.5.2
-   paramiko: 3.5.1
-   mysql-connector-python: 9.1.0

### 今回公開する「discord-mc-admin」でのサーバー構成例
-   プラン１：サーバーA（discordボット起動）、サーバーB（マイクラサーバー）、サーバーC（DBサーバー）、サーバーD（MCRPサーバー）
-   プラン２：サーバーA（discordボット起動）、サーバーB（マイクラサーバー・DBサーバー）、サーバーC（MCRPサーバー）
-   プラン３：サーバーA（discordボット起動・DBサーバー）、サーバーB（マイクラサーバー）、サーバーC（MCRPサーバー）
-   etc

プランすべてに共通してマイクラサーバーは、discordボットからSSHアクセスするための管理用ユーザーが必要です。  
※discordボット鯖とマイクラ鯖が別であれば好きな構成で問題ありません。  
初期だと「minecraft」ユーザーを使用して設定を行う為、マイクラサーバーとするPCに
「minecraft」ユーザーを予め作成しておく必要があります。接続には、公開鍵方式を使用してください。

# How to use

<details>
<summary>手順 １ [.envファイルの初期設定]</summary>
プロジェクトを実行するには、環境変数の設定が必要です。`.env.sample`ファイルをコピーし、`.env`という名前で保存してください。  

`DISCORD_BOT_TOKEN="TOKEN-HERE"`  
Discord-Developper-Portalから取得したBotのトークンを `TOKEN-HERE` に貼り付けてください。

`DOMAIN_NAME="example.com"`  
運用するドメインを指定してください。BOTの動作に直接関与するものではありませんが、サーバー作成後にBOTからユーザーへ返信されるメッセージにここで指定したドメインに生成したサーバーのサブドメインを合わせて通知するようになっています。

`ADMIN_KEY="password"`  
/admin コマンドを入力すると、ADMINキー入力モーダルが表示され、ここで設定した値と検証を行うようになっています。

`PREMIUM_KEY="password"`  
/premium コマンドを入力すると、PREMIUMキー入力モーダルが表示され、ここで設定した値と検証を行うようになっています。

`SV_MAX_PORT="25510"`  
`SV_MIN_PORT="25501"`
作成したサーバーが使用するポート番号の範囲になります。ここで指定する範囲にあるポート番号の数がBOT全体で立てることのできるサーバー数の最大値になっています。

`DB_HOST="192.168.xxx.xxx"`  
`DB_NAME="mc_admin_db"`  
`DB_PORT="3306"`  
`DB_USER="minecraft"`  
`DB_PASS="Xcpw3GTBRJQqjeb2"`  
ボットが利用するDBの接続先情報を記載します。ここ（DB_NAME, DB_PORT, DB_USER, DB_PASS）を変更した場合は、[db-server-setup.sh](https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/setup-script/db-server-setup.sh) の設定情報を変更する必要があります。

`SSH_HOST="192.168.xxx.xxx"`  
`SSH_PORT="22"`  
`SSH_USER="minecraft"`  
`SSH_PASS="password"`  
`SSH_KEY_PATH="/home/you/private-key"`  
実際にマインクラフトサーバーを稼働させるサーバーへSSH接続するための情報を記載します。  ここ（SSH_USER）を変更した場合は、[mc-server-setup.sh](https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/setup-script/mc-server-setup.sh) の設定情報を変更する必要があります。

`TIMEOUT_SEC="120"`  
/create や /delete などのユーザーが使用するコマンドのタイムアウト時間を一括で設定します。    
</details> 



<details>
<summary>手順 ２ [データベース・サーバーのセットアップ]</summary>  
    
DBサーバーを構築するセットアップスクリプト db-server-setup.sh を wget 等でリポジトリからダウンロードします。  
```
wget https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/setup-script/db-server-setup.sh
```
ダウンロードしたスクリプトの設定情報を変更する場合はこの段階で編集します。
chmod で実行権限を付与します。
```
chmod +x db-server-setup.sh
```
スクリプトの実行には、sudo をつけ root ユーザーで実行します。
```
sudo ./db-server-setup.sh
```
スクリプトの途中で外部からDBサーバーにアクセスするかどうかを問われます。DiscordボットとDBサーバーが別の場合、外部アクセスの設定が必要になります。「y」を入力して処理を進めてください。  
`[Q/A ] DBに外部からアクセスを許可しますか？ (y/N): `  
</details>



<details>
<summary>手順 ３ [マインクラフト・サーバーのセットアップ]</summary>
    
実際にマインクラフトサーバーが稼働するサーバーのセットアップスクリプト mc-server-setup.sh を wget 等でリポジトリからダウンロードします。  
```
wget https://raw.githubusercontent.com/yukugura/discord-mc-admin/refs/heads/main/setup-script/mc-server-setup.sh
```
ダウンロードしたスクリプトの設定情報を変更する場合はこの段階で編集します。
chmod で実行権限を付与します。
```
chmod +x mc-server-setup.sh
```
スクリプトの実行には、sudo をつけ root ユーザーで実行します。
```
sudo ./mc-server-setup.sh
```
スクリプトの途中で minecraftユーザーが実行している環境に居ない場合、作成するか別の管理ユーザーを指定するかを聞かれます。  
`[Q/A ] ユーザー ${MC_USER} を作成しますか？ (y/N): `  

もし別のユーザーを管理用ユーザーとして指定する場合、.envファイルに設定したSSH情報の各種設定項目を変更する必要があります。  
`[Q/A ] 代わりに、どの既存sudoユーザーを管理用に使用しますか？：`
</details>



<details>
<summary>手順 ４ [ボット・サーバーのセットアップ]</summary>

Pythonインストール後、ライブラリをインストールします。仮想環境での運用をおすすめします。  
```
pip install python-dotenv
```  
```
pip install discord.py
```  
```
pip install paramiko
```  
```
pip install mysql-connector-python
```  

その後、 discord-mc-admin.py を実行してください。
</details>



<details>
<summary>手順 ５ [RP・サーバーのセットアップ]</summary>

サブドメインでのアクセスを想定しているため、RPサーバーを構築します。
今回は、無難に [BungeeCord](https://github.com/SpigotMC/BungeeCord/) を使用しました。
※ここでは、使用方法は説明しません。
サブドメインアクセス用に**DNS設定**を予め済ませておいてください。  

config.ymlの forced_hosts: に追記します。
```
  forced_hosts:
    sv01.example.com: sv01
    sv02.example.com: sv02
    sv03.example.com: sv03
    sv04.example.com: sv04
    sv05.example.com: sv05
    sv06.example.com: sv06
    sv07.example.com: sv07
    sv08.example.com: sv08
    sv09.example.com: sv09
    sv10.example.com: sv10
```

次に、サーバーを追加します。同じく config.yml の servers セクションを編集します。  
マイクラサーバーのIPが「192.168.100.202」だった場合以下のように記述します。
```
servers:
  sv01:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25501
    restricted: false
  sv02:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25502
    restricted: false
  sv03:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25503
    restricted: false
  sv04:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25504
    restricted: false
  sv05:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25505
    restricted: false
  sv06:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25506
    restricted: false
  sv07:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25507
    restricted: false
  sv08:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25508
    restricted: false
  sv09:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25509
    restricted: false
  sv10:
    motd: Discord-Minecraft-Admin
    address: 192.168.100.202:25510
    restricted: false
```
</details>



## 外部ソフトウェアの利用について

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
