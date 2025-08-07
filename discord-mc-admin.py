from dotenv import load_dotenv
from discord.ext import commands
from ssh_utils import execute_remote_command
import os
import discord
import mysql.connector
import asyncio

# 環境変数読み込み
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")
ADMIN_KEY = os.getenv("ADMIN_KEY")
SV_MAX_PORT = os.getenv("SV_MAX_PORT")
SV_MIN_PORT = os.getenv("SV_MIN_PORT")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = os.getenv("SSH_PORT")
SSH_USER = os.getenv("SSH_USER")
SSH_PASS = os.getenv("SSH_PASS")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC"))

# Bot設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# global
creating_users = [] # 現在サーバー作成中のユーザーを格納
"""
# MySQLDB接続関数
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=int(DB_PORT)
        )
        if connection.is_connected():
            print("MySQLデータベースに接続しました。")
            return connection
    except mysql.connector.Error as e:
        print(f"MySQLデータベース接続エラー：{e}")
        return None
    
# MySQLDBへの接続を担保
async def ensure_db_connection():
    global db_connection, db_cursor
    if db_connection and db_connection.is_connected():
        return db_connection
    new_connection = get_db_connection()
    if new_connection:
        db_connection = new_connection
        print("[DEBUG] 新しくDB接続を確立しました。ensure_db_connection()")
        if db_cursor:
            try: db_cursor.close()
            except mysql.connector.Error as e: print(f"カーソルのクローズエラー：{e}")
        db_cursor = db_connection.cursor()
    else:
        print("DB接続エラー：get_db_connectionがNoneを返しました。")
        return None
    return db_connection
"""

# DB操作をまとめたクラス
class db_manager:
    # インスタンス生成時に実行
    def __init__(self):
        # グローバル変数への依存をなくし、自身の属性として接続情報を保持
        self.host = DB_HOST
        self.database = DB_NAME
        self.user = DB_USER
        self.password = DB_PASS
        self.port = int(DB_PORT)
        self.connection = None # 接続は __init__ では行わない
        self.cursor = None
        self._is_connecting = False # 多重接続を防ぐためのフラグ

    # データベースにユーザーを登録する
    async def register_user(self, dc_user_id, dc_user_name):
        await self.connect()
        # ユーザー登録SQL
        query = "SELECT dc_user_name FROM users WHERE dc_user_id = %s"  
        result = await self._execute_query(query, (str(dc_user_id),), fetchall=True) # fechallが返却
        if not result:
            # ユーザーがいなかった場合は登録
            query = """INSERT INTO users (dc_user_id, dc_user_name, perm_name)
                    VALUES (%s, %s, 'default')
                    ON DUPLICATE KEY UPDATE  dc_user_name = VALUES(dc_user_name), perm_name = VALUES(perm_name);"""
            params = (str(dc_user_id), dc_user_name)
            if await self._execute_query(query, params, commit=True):
                # 登録成功
                print(f"[DEBUG]ユーザー {dc_user_name} を登録しました。")
                return True
            else:
                # 登録失敗
                print(f"[DEBUG]ユーザー {dc_user_name} の登録に失敗しました。")
                return False
        else:
            # ユーザーが存在する場合の処理
            if not result[0][0] == dc_user_name: # ユーザー名が異なる場合は更新
                query = "UPDATE users SET dc_user_name = %s WHERE dc_user_id = %s"
                params = (dc_user_name, str(dc_user_id))
                await self._execute_query(query, params, commit=True)
                print(f"[DEBUG]ユーザー {dc_user_name} の名前を更新しました。{result}")
            else:
                print(f"[DEBUG]ユーザー {dc_user_name} は同じ名前で既に登録されています。{result}")
            return None

    # サーバー作成可能か確認する
    async def can_create_server(self, user_id):
        # ユーザーの現在の作成済みサーバー数を取得
        current_sv_query = "SELECT COUNT(*) FROM servers WHERE dc_user_id = %s and status IN ('running', 'creating')"
        current_sv = await self._execute_query(current_sv_query, (str(user_id),), fetchone=True)
        # ユーザーの作成可能サーバー数を取得
        max_sv_query = "SELECT max_sv FROM users INNER JOIN perm_limits ON users.perm_name = perm_limits.perm_name WHERE users.dc_user_id = %s"
        max_sv = await self._execute_query(max_sv_query, (str(user_id),), fetchone=True)
        # 作成可能かの判断
        if current_sv[0] < max_sv[0]:
            return True # 作成可能
        else:
            return False # 作成不可

    # そのポートが空いているか、使用できるか確認する
    async def find_available_port(self, port_num):
        query = "SELECT sv_id FROM servers WHERE status IN ('running','creating','error') and sv_port = %s"
        result = await self._execute_query(query, (port_num,), fetchall=True)
        if result:
            # データがある（使用中である場合）
            return False
        else:
            # データがない（使用されていない場合）
            return True

    # 現在稼働中のサーバー数を取得する
    async def active_servers(self):
        query = "SELECT COUNT(*) FROM servers WHERE status IN ('running', 'creating')"
        result = await self._execute_query(query, fetchone=True)
        return result[0] if result[0] else 0

    # サーバー作成をserversテーブルに登録
    async def insert_creating_data(self, user_id, sv_name, sv_type, sv_ver, sv_port):
        creating_sv_query = """INSERT INTO servers(
                                dc_user_id,
                                sv_name,
                                sv_type,
                                sv_ver,
                                sv_port,
                                status
                            )VALUES (%s,%s,%s,%s,%s,%s)"""
        creating_sv_params = (user_id, sv_name, sv_type, sv_ver, sv_port, 'creating')
        return await self._execute_query(creating_sv_query, creating_sv_params, commit=True)
    
    # サーバーのステータスを更新する
    async def update_server_status(self, dc_user_id, sv_name, status):
        update_sv_query = """UPDATE servers SET status = %s 
                            WHERE dc_user_id = %s AND sv_name = %s"""
        update_sv_params = (status, dc_user_id, sv_name)
        return await self._execute_query(update_sv_query, update_sv_params, commit=True)

    # ユーザーの権限を取得する
    async def get_user_permissions(self, user_id):
        # ユーザーの権限を取得するSQL
        query = "SELECT perm_name FROM users WHERE dc_user_id = %s"
        result = await self._execute_query(query, (str(user_id),), fetchone=True)
        if result is not None:
            # ユーザーが存在する場合
            return result[0]
        else:
            # ユーザーが存在しない場合
            return None
    
    # ユーザーロールを変更する
    async def update_user_permission(self, user_id, perm):
        query = """UPDATE users
                    SET perm_name = %s
                    WHERE dc_user_id = %s"""
        params = (perm, user_id)
        return await self._execute_query(query, params, commit=True)

    # ユーザーの最大サーバー作成数を取得する
    async def can_create_max_servers(self, user_id):
        max_sv_query = "SELECT max_sv FROM users INNER JOIN perm_limits ON users.perm_name = perm_limits.perm_name WHERE users.dc_user_id = %s"
        max_sv = await self._execute_query(max_sv_query, (str(user_id),), fetchone=True)
        return max_sv[0]

    # 現在作成しているサーバーすべてを２次元で返す
    async def get_active_user_servers(self, user_id, admin=False):
        if not admin:
            # adminじゃない時
            active_query = "SELECT sv_name, sv_port FROM servers WHERE status = 'running' AND dc_user_id = %s"
            active_params = (user_id,)
        else:
            # adminの時
            active_query = "SELECT sv_name, sv_port FROM servers WHERE status = 'running'"
            active_params = None
        return await self._execute_query(active_query, active_params, fetchall=True)

    # ユーザーがAdminかどうかの判定
    async def check_is_admin(self, user_id):
        check_query = "SELECT perm_name FROM users WHERE dc_user_id = %s AND perm_name = 'admin'"
        check_params = (user_id,)
        if await self._execute_query(check_query, check_params, fetchall=True):
            # データがあればadmin確定
            return True
        else:
            # データがない、つまりadminではない
            return False

    # サーバー名とdc_user_idで重複がないか調べる
    async def check_server_name_duplicate(self, user_id, sv_name):
        check_query = "SELECT * FROM servers WHERE dc_user_id = %s AND sv_name = %s"
        check_params = (user_id, sv_name)
        if await db_manager_instance._execute_query(check_query, check_params, fetchall=True):
            # データが過去にある（重複あり）
            return False
        else:
            # データが過去にない（重複なし）
            return True
        
    # SQLを実行する際のヘルパーメソッド
    async def _execute_query(self, query, params=None, fetchone=False, fetchall=False, commit=False):
        # データベース接続の確立を保証する
        cursor = await self.connect()
        if not cursor:
            print("[DEBUG] db_manager（_execute_query）：クエリ実行前にDB接続失敗")
            return None if (fetchone or fetchall) else False

        # SQL実行部分
        try:
            cursor.execute(query, params if params else ())
            if commit:
                self.connection.commit()
                return True
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
        # 下は失敗時の処理
        except mysql.connector.Error as e:
            print(f"db_manager: SQL実行エラー: {e}")
            if self.connection and self.connection.is_connected():
                try:
                    self.connection.rollback()  # エラー時はロールバック
                except mysql.connector.Error as e:
                    print(f"db_manager: ロールバックエラー: {e}")
            return None if (fetchone or fetchall) else False

    # データベース接続を確立する
    async def connect(self):
        # 1. 既存の接続が有効かチェック
        if self.connection and self.connection.is_connected():
            # カーソルが閉じている場合は再作成
            if self.cursor is None:
                try:
                    self.cursor = self.connection.cursor()
                except Exception as e:
                    print(f"db_manager: 既存接続からのカーソル再作成エラー: {e}")
                    return None
            return self.cursor

        # 2. 既に接続処理中の場合は待機 (多重接続防止)
        if self._is_connecting:
            print("db_manager: 接続処理中のため待機します。")
            while self._is_connecting:
                await asyncio.sleep(0.1) # 短い時間待機
            # 待機後に接続が確立されていればそれを利用
            if self.connection and self.connection.is_connected():
                return self.cursor

        # 3. 新しい接続処理を開始するフラグを設定
        self._is_connecting = True

        try:
            # 4. MySQLへの実際の接続
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            if self.connection.is_connected():
                print("db_manager: MySQLデータベースに接続しました。")
                # 古いカーソルがあれば閉じて新しいカーソルを作成
                if self.cursor:
                    try: self.cursor.close()
                    except Exception as e: print(f"db_manager: 既存カーソルクローズエラー: {e}")
                self.cursor = self.connection.cursor()
                return self.cursor
            else:
                print("db_manager: MySQLデータベースへの接続に失敗しました。（db_manager.connect内）")
                return None
        except Exception as e:
            # 接続失敗時のエラーハンドリング
            print(f"db_manager: MySQLデータベース接続エラー: {e}")
            self.connection = None
            self.cursor = None
            return None
        finally:
            # 5. 接続処理終了フラグをリセット (成功・失敗に関わらず)
            self._is_connecting = False

    # データベースclose処理 (グローバル変数への依存をなくす)
    async def close(self):
        try:
            if self.cursor is not None:
                self.cursor.close()
                print("db_manager: カーソルを閉じました。")
            if self.connection and self.connection.is_connected():
                self.connection.close()
                print("db_manager: データベース接続を閉じました。")
        except Exception as e: # mysql.connector.Error の代わりに汎用Exception
            print(f"db_manager: DBクローズエラー：{e}")
        finally:
            self.cursor = None
            self.connection = None

# サーバー作成確認のViewクラス
class CreateServerView(discord.ui.View):
    def __init__(self, original_discord_id, timeout=TIMEOUT_SEC):
        super().__init__(timeout=timeout)
        self.original_user_id = original_discord_id

    # 引数の順序を (self, interaction, button) に変更
    @discord.ui.button(label="はい", style=discord.ButtonStyle.danger)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button): # はい押下時のコールバック
        # 本人か確認する処理
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_message("",view=VersionSelectView(interaction),ephemeral=True)
    
    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button): # いいえ押下時のコールバック
        # 本人か確認する処理
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        global creating_users
        if self.original_user_id in creating_users: # 作成中から元の状態に戻す
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id)
        await interaction.response.send_message("処理をキャンセルしました。",ephemeral=True)
        self.stop()
        return
    
    # タイムアウト時の処理
    async def on_timeout(self):
        # 排他変数から削除
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id) # 作成中から元の状態に戻す
        self.stop()
        return await super().on_timeout()

# サーバーバージョンを選択するViewクラス
class VersionSelectView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=TIMEOUT_SEC)
        self.original_user_id = interaction.user.id
        self.interaction = interaction

    @discord.ui.select(
        placeholder="サーバーバージョンを選択してください",
        options=[
            discord.SelectOption(label="1.21.8 最新", value="1.21.8"),
            discord.SelectOption(label="1.21.7", value="1.21.7"),
            discord.SelectOption(label="1.21.6", value="1.21.6"),
            discord.SelectOption(label="1.21.5", value="1.21.5"),
            discord.SelectOption(label="1.21.4", value="1.21.4"),
            discord.SelectOption(label="1.21.3", value="1.21.3"),
            discord.SelectOption(label="1.21.2", value="1.21.2"),
            discord.SelectOption(label="1.21.1", value="1.21.1")
        ]
    )
    # プルダウン選択後の処理
    async def version_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_version = select.values[0]
        self.stop()
        await interaction.response.send_message(f"",view=TypeSelectView(self.selected_version, interaction), ephemeral=True)
    
    # タイムアウト時の処理
    async def on_timeout(self):
        # 排他変数から削除
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id) # 作成中から元の状態に戻す
        return await super().on_timeout()

# サーバータイプを選択するViewクラス
class TypeSelectView(discord.ui.View):
    def __init__(self,selected_version ,interaction: discord.Interaction):
        super().__init__(timeout=TIMEOUT_SEC)
        self.original_user_id = interaction.user.id
        self.selected_version = selected_version

    @discord.ui.select(
        placeholder="サーバーの種類を選択してください",
        options=[
            discord.SelectOption(label="Vanilla", value="vanilla"),
            discord.SelectOption(label="Forge", value="forge"),
            discord.SelectOption(label="Spigot", value="spigot"),
            discord.SelectOption(label="Paper", value="paper"),
        ]
    )
    # プルダウンメニュー選択後の処理
    async def type_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_type = select.values[0]
        self.stop()
        await interaction.response.send_modal(ServerNameModal(interaction.user.id, self.selected_type, self.selected_version))

    # タイムアウト時の処理
    async def on_timeout(self):
        global creating_users
        # 排他変数から削除
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id) # 作成中から元の状態に戻す
        return await super().on_timeout()

# サーバー名を入力するモーダルクラス
class ServerNameModal(discord.ui.Modal):
    def __init__(self, original_user_id: int, selected_type: str = None, selected_version: str = None):
        super().__init__(title="サーバー名入力", timeout=TIMEOUT_SEC)  # タイムアウトを180秒に設定
        self.original_user_id = original_user_id
        self.selected_type = selected_type
        self.selected_version = selected_version
        
        # サーバー名入力フィールド
        self.server_name_input = discord.ui.TextInput(
            label="サーバー名を入力してください",
            placeholder="例: MyMinecraftServer",
            required=True,
            max_length=64,  # 最大文字数を64に設定
            custom_id="server_name_input"
        )
        self.add_item(self.server_name_input)
    # 送信後の処理
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"サーバー作成処理が進行中です。しばらくお待ちください・・・",ephemeral=True)
        try:
            #サーバー名に重複がないか確認
            if not await db_manager_instance.check_server_name_duplicate(interaction.user.id, self.server_name_input.value):
                await interaction.followup.send(f"サーバー名が**重複**しています。過去に使用したサーバー名は、利用できません。もう一度はじめからやり直してください。",ephemeral=True)
                return 

            # 空きポートを探す処理
            available_port = None
            for port in range(int(SV_MIN_PORT), int(SV_MAX_PORT) + 1):
                if await db_manager_instance.find_available_port(port):
                    # 空きポートが見つかった
                    available_port = port
                    break

            # 一つも空きポートがなかったかどうかを判定
            if available_port is None:
                await interaction.followup.send("利用可能なポートが見つかりませんでした。処理を中断します。",ephemeral=True)
                return
            
            # 空きポートが見つかったので status 'creating' で予約
            await db_manager_instance.insert_creating_data(interaction.user.id, self.server_name_input.value, self.selected_type, self.selected_version, available_port)

            # SSHしてスクリプトを実行
            if await self._execute_create_server(available_port):
                # 成功した場合
                await db_manager_instance.update_server_status(interaction.user.id, self.server_name_input.value, 'running')
                await interaction.followup.send(f"サーバー名：`{self.server_name_input.value}` タイプ：`{self.selected_type}` バージョン：`{self.selected_version}`でサーバーの作成に成功しました。\n接続用サーバーアドレス`sv{str(available_port)[-2:]}.{DOMAIN_NAME}`",ephemeral=True)
            else:
                # 失敗した場合
                await db_manager_instance.update_server_status(interaction.user.id, self.server_name_input.value, 'error')
                await interaction.followup.send(f"サーバーの作成に失敗しました。",ephemeral=True)

        finally:
            # 排他変数から削除
            if self.original_user_id in creating_users:
                print("[DEBUG] 排他変数から削除しました。")
                creating_users.remove(self.original_user_id) # 作成中から元の状態に戻す
        return
    
    # SSH接続してサーバー作成スクリプトを実行する関数
    async def _execute_create_server(self, sv_port):
        sv_name = self.server_name_input.value
        sv_type = self.selected_type
        sv_ver = self.selected_version

        # 実行したいコマンドを格納
        cmd1 = f"/minecraft/scripts/CREATE-SERVER.sh \"{sv_name}\" \"{sv_type}\" \"{sv_ver}\" \"{sv_port}\""
        cmd2 = f"sudo /minecraft/scripts/CREATE-SERVER-SUDO.sh \"{sv_name}\" \"{sv_type}\" \"{sv_ver}\" \"{sv_port}\""

        # 実行
        success1, _ = await execute_remote_command(SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH, SSH_PASS, cmd1)
        if not success1:
            return False
        
        # 実行
        success2, _ = await execute_remote_command(SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH, SSH_PASS, cmd2)
        if not success2:
            return False
        
        # 問題なく実行できた場合は、Trueを返却
        return True
    
    # タイムアウト時の処理
    async def on_timeout(self):
        global creating_users
        # 排他変数から削除
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id) # 作成中から元の状態に戻す
        return await super().on_timeout()

# サーバー削除ウィザードに進むかどうかのViewクラス
class DeleteAgreeView(discord.ui.View):
    def __init__(self, original_discord_id, servers):
        super().__init__(timeout=TIMEOUT_SEC)
        self.original_user_id = original_discord_id
        self.servers = servers

    # はいを押されたときのコールバック
    @discord.ui.button(label="次へ", style=discord.ButtonStyle.danger)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button): # はい押下時のコールバック
        # 本人か確認する処理
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_message("",view=DeleteServerView(self.servers),ephemeral=True)
    
    # キャンセル押されたときのコールバック
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button): # いいえ押下時のコールバック
        # 本人か確認する処理
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        await interaction.response.send_message("処理をキャンセルしました。",ephemeral=True)
        self.stop()

# 削除するサーバーを選択するViewクラス
class DeleteServerView(discord.ui.View):
    def __init__(self, servers):
        super().__init__(timeout=TIMEOUT_SEC)
        # リストを動的に作成
        select_options = [discord.SelectOption(label=s[0], value=s[0]) for s in servers]
        self.servers = servers

        # selectオブジェクトを初期化
        select = discord.ui.Select(
            placeholder="一度削除すると二度とデータは戻りません。",
            options = select_options
        )
        # コールバック関数を指定
        select.callback = self.delete_server_callback
        # Viewにselectオブジェクトを追加
        self.add_item(select)

    # プルダウンで削除する鯖を選択後
    async def delete_server_callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_modal(DeleteConfirmModal(interaction.data["values"][0], self.servers))

# サーバー名を入力するモーダルクラス
class DeleteConfirmModal(discord.ui.Modal):
    def __init__(self, original_sv_name, servers:list):
        super().__init__(title="削除するサーバー名を入力", timeout=TIMEOUT_SEC)
        self.sv_name = original_sv_name
        self.sv_port = [s[1] for s in servers if s[0] == original_sv_name][0]
        self.servers = servers # 念の為、いらないかも
        print(f"[DEBUG] {self.sv_port}")
        
        # サーバー名入力フィールド
        self.delete_server_name_input = discord.ui.TextInput(
            label="一度削除すると二度とデータは戻りません。",
            placeholder="例: MyMinecraftServer",
            required=True,
            max_length=64,  # 最大文字数を64に設定
            custom_id="delete_server_name_input"
        )
        self.add_item(self.delete_server_name_input)

    # 送信後の処理
    async def on_submit(self, interaction: discord.Interaction):
        # 入力間違いを判定
        if self.delete_server_name_input.value == self.sv_name:
            # 入力内容に間違いがなく削除を実行する場合
            await interaction.response.defer(ephemeral=True) # 処理に時間がかかるため一旦defer
            await interaction.followup.send(f"削除処理を実行中です。しばらくお待ちください・・・",ephemeral=True)
            # スクリプトの実行が成功するか判断するif文
            if await self._execute_delete_server():
                # 成功した場合
                await db_manager_instance.update_server_status(interaction.user.id, self.sv_name, 'deleting')
                await interaction.followup.send(f"サーバー名：`{self.sv_name}`の削除が完了しました。",ephemeral=True)
                return 
            else:
                # 失敗した場合
                await db_manager_instance.update_server_status(interaction.user.id, self.sv_name, 'error')
                await interaction.followup.send(f"サーバー名：`{self.sv_name}`の削除に失敗しました。管理者にお問い合わせください。",ephemeral=True)
                return
        # 入力内容が違う場合
        else:
            await interaction.response.send_message(f"入力内容に間違いがあるため、削除処理を中止します。\nもう一度はじめからやり直してください。", ephemeral=True)
            return 

    # SSH接続してサーバー作成スクリプトを実行する関数
    async def _execute_delete_server(self):
        # 実行したいコマンドを格納
        cmd1 = f"sudo /minecraft/scripts/DELETE-SERVER-SUDO.sh \"{self.sv_port}\""
        # 実行
        success1, _ = await execute_remote_command(SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH, SSH_PASS, cmd1)
        if not success1:
            return False
        # 問題なく実行できた場合は、Trueを返却
        return True

# Adminロールに変更するためのキー入力Viewクラス
class ChangeRoleAdminView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=TIMEOUT_SEC)
        self.original_user_id = user_id

    # はい（続行処理）
    @discord.ui.button(label="はい", style=discord.ButtonStyle.danger)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button): # はい押下時のコールバック
        # 本人か確認する処理
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_modal(ChangeRoleAdminModal())
    
    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button): # いいえ押下時のコールバック
        # 本人か確認する処理
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        await interaction.response.send_message("処理をキャンセルしました。",ephemeral=True)
        self.stop()
        return

# Adminロールに変更するためのキー入力モーダル
class ChangeRoleAdminModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Adminパスワード入力フォーム", timeout=TIMEOUT_SEC)
        
        # パスフレーズ入力フォーム
        self.admin_key_input = discord.ui.TextInput(
            label="Admin認証キーを入力してください",
            placeholder="例：password",
            required=True,
            max_length=64, # 最大文字数
            custom_id="admin_key_input"
        )
        self.add_item(self.admin_key_input)

    # 送信後の処理
    async def on_submit(self, interaction: discord.Interaction):
        if self.admin_key_input.value == ADMIN_KEY:
            # 同じだった場合（認証成功）
            if await db_manager_instance.update_user_permission(interaction.user.id, 'admin'): # adminに変更
                max_sv_ct = await db_manager_instance.can_create_max_servers(interaction.user.id) # 最大サーバー作成数を取得
                await interaction.response.send_message(f"ユーザー`{interaction.user.name}`のパーミッションを`admin`に更新しました。\n現在の最大サーバー作成数は、`{max_sv_ct}`です。",ephemeral=True)
                return await super().on_submit(interaction)
        # 違った場合（認証失敗）
        await interaction.response.send_message(f"キーの認証に失敗しました。処理を中断します。",ephemeral=True)
        return await super().on_submit(interaction)

# Bot起動時処理
@bot.event
async def on_ready():
    global db_manager_instance # グローバル変数 db_manager_instance を変更するために必要
    print(f"{bot.user}がオンラインになりました！")
    
    # db_managerのインスタンスをここで一度だけ作成
    db_manager_instance = db_manager()
    
    # db_managerインスタンスのconnectメソッドを呼び出し、初期接続を確立
    initial_cursor = await db_manager_instance.connect()
    if initial_cursor:
        print("DB初期接続が確立されました。")
    else:
        print("DB接続に失敗しました。ボットを終了します。")
        await bot.close()

# Bot終了時処理 (変更あり: db_manager_instance の close メソッドを呼び出す)
@bot.event
async def on_disconnect():
    global db_manager_instance
    if db_manager_instance:
        await db_manager_instance.close()
        print("db_manager: データベース接続を閉じました。")

# コマンド関数定義
@bot.command(name=DOMAIN_NAME)
async def create_mc_sv(ctx: commands.Context):
    await db_manager_instance.register_user(ctx.author.id, ctx.author.name) # ctx.author.name を str(ctx.author) に変更
    # 現在稼働サーバー数を取得（上限にぶち当たってないかどうかの判断）
    active_servers = await db_manager_instance.active_servers()
    if active_servers < (int(SV_MAX_PORT) - int(SV_MIN_PORT) + 1):
        # サーバーの数に空きがある場合
        if await db_manager_instance.can_create_server(ctx.author.id) and (ctx.author.id not in creating_users): # ユーザーの作成資格の確認と排他変数にidがないか確認
            # 作成可能の場合
            creating_users.append(ctx.author.id)
            await ctx.send(f"**{DOMAIN_NAME}**でサーバーを作成しますか？",view=CreateServerView(ctx.author.id))
        else:
            # 作成不可の場合
            await ctx.send(f"`{ctx.author.name}`：サーバー作成上限に達しているか、現在作成中のサーバーが存在するため処理を中断します。")
    else:
        # 稼働できるサーバーの数に空きがない場合
        await ctx.send(f"稼働出来るサーバー数に空きがありません。")

# 現在立てているサーバーを削除するコマンド
@bot.command()
async def delete(ctx: commands.Context):
    servers = await db_manager_instance.get_active_user_servers(ctx.author.id)
    if not servers:
        # サーバーがない場合
        await ctx.send(f"現在稼働中のサーバーが見つかりませんでした。")
        return
    
    # 稼働中サーバーが見つかった場合
    await ctx.send(f"稼働中のサーバーが見つかりました。サーバー削除ウィザードに進みますか？", view=DeleteAgreeView(ctx.author.id, servers))

# Adminロールにする処理
@bot.command()
async def admin(ctx: commands.Context):
    await db_manager_instance.register_user(ctx.author.id, ctx.author.name) # ユーザーがない場合に登録
    max_sv_ct = await db_manager_instance.can_create_max_servers(ctx.author.id) # 最大サーバー作成数を取得
    await ctx.send(f"現在の最大サーバー作成数は、`{max_sv_ct}`です。\nAdminキーを入力することでロールの変更し、最大サーバー作成数を変更することが可能です。\nキー入力を行いますか？",view=ChangeRoleAdminView(ctx.author.id),ephemeral=True)

# Bot実行
bot.run(BOT_TOKEN)