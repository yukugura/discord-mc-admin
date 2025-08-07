from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands # app_commandsをインポート
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
intents.message_content = True # この行はスラッシュコマンドでは不要ですが、あっても問題ありません。
bot = commands.Bot(command_prefix="!", intents=intents)

# global
creating_users = [] # 現在サーバー作成中のユーザーを格納

# DB操作をまとめたクラス
class db_manager:
    def __init__(self):
        self.host = DB_HOST
        self.database = DB_NAME
        self.user = DB_USER
        self.password = DB_PASS
        self.port = int(DB_PORT)
        self.connection = None
        self.cursor = None
        self._is_connecting = False

    async def register_user(self, dc_user_id, dc_user_name):
        await self.connect()
        query = "SELECT dc_user_name FROM users WHERE dc_user_id = %s"  
        result = await self._execute_query(query, (str(dc_user_id),), fetchall=True)
        if not result:
            query = """INSERT INTO users (dc_user_id, dc_user_name, perm_name)
                    VALUES (%s, %s, 'default')
                    ON DUPLICATE KEY UPDATE  dc_user_name = VALUES(dc_user_name), perm_name = VALUES(perm_name);"""
            params = (str(dc_user_id), dc_user_name)
            if await self._execute_query(query, params, commit=True):
                print(f"[DEBUG]ユーザー {dc_user_name} を登録しました。")
                return True
            else:
                print(f"[DEBUG]ユーザー {dc_user_name} の登録に失敗しました。")
                return False
        else:
            if not result[0][0] == dc_user_name:
                query = "UPDATE users SET dc_user_name = %s WHERE dc_user_id = %s"
                params = (dc_user_name, str(dc_user_id))
                await self._execute_query(query, params, commit=True)
                print(f"[DEBUG]ユーザー {dc_user_name} の名前を更新しました。{result}")
            else:
                print(f"[DEBUG]ユーザー {dc_user_name} は同じ名前で既に登録されています。{result}")
            return None

    async def can_create_server(self, user_id):
        current_sv_query = "SELECT COUNT(*) FROM servers WHERE dc_user_id = %s and status IN ('running', 'creating')"
        current_sv = await self._execute_query(current_sv_query, (str(user_id),), fetchone=True)
        max_sv_query = "SELECT max_sv FROM users INNER JOIN perm_limits ON users.perm_name = perm_limits.perm_name WHERE users.dc_user_id = %s"
        max_sv = await self._execute_query(max_sv_query, (str(user_id),), fetchone=True)
        if current_sv and max_sv and current_sv[0] < max_sv[0]:
            return True
        else:
            return False

    async def find_available_port(self, port_num):
        query = "SELECT sv_id FROM servers WHERE status IN ('running','creating','error') and sv_port = %s"
        result = await self._execute_query(query, (port_num,), fetchall=True)
        if result:
            return False
        else:
            return True

    async def active_servers(self):
        query = "SELECT COUNT(*) FROM servers WHERE status IN ('running', 'creating')"
        result = await self._execute_query(query, fetchone=True)
        return result[0] if result else 0

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
    
    async def update_server_status(self, dc_user_id, sv_name, status):
        update_sv_query = """UPDATE servers SET status = %s 
                            WHERE dc_user_id = %s AND sv_name = %s"""
        update_sv_params = (status, dc_user_id, sv_name)
        return await self._execute_query(update_sv_query, update_sv_params, commit=True)

    async def get_user_permissions(self, user_id):
        query = "SELECT perm_name FROM users WHERE dc_user_id = %s"
        result = await self._execute_query(query, (str(user_id),), fetchone=True)
        if result is not None:
            return result[0]
        else:
            return None
    
    async def update_user_permission(self, user_id, perm):
        query = """UPDATE users
                    SET perm_name = %s
                    WHERE dc_user_id = %s"""
        params = (perm, user_id)
        return await self._execute_query(query, params, commit=True)

    async def can_create_max_servers(self, user_id):
        max_sv_query = "SELECT max_sv FROM users INNER JOIN perm_limits ON users.perm_name = perm_limits.perm_name WHERE users.dc_user_id = %s"
        max_sv = await self._execute_query(max_sv_query, (str(user_id),), fetchone=True)
        return max_sv[0]

    async def get_active_user_servers(self, user_id, admin=False):
        if not admin:
            active_query = "SELECT sv_name, sv_port FROM servers WHERE status = 'running' AND dc_user_id = %s"
            active_params = (user_id,)
        else:
            active_query = "SELECT sv_name, sv_port FROM servers WHERE status = 'running'"
            active_params = None
        return await self._execute_query(active_query, active_params, fetchall=True)

    async def check_is_admin(self, user_id):
        check_query = "SELECT perm_name FROM users WHERE dc_user_id = %s AND perm_name = 'admin'"
        check_params = (user_id,)
        if await self._execute_query(check_query, check_params, fetchall=True):
            return True
        else:
            return False

    async def check_server_name_duplicate(self, user_id, sv_name):
        check_query = "SELECT * FROM servers WHERE dc_user_id = %s AND sv_name = %s"
        check_params = (user_id, sv_name)
        if await self._execute_query(check_query, check_params, fetchall=True):
            return False
        else:
            return True
        
    async def _execute_query(self, query, params=None, fetchone=False, fetchall=False, commit=False):
        cursor = await self.connect()
        if not cursor:
            print("[DEBUG] db_manager（_execute_query）：クエリ実行前にDB接続失敗")
            return None if (fetchone or fetchall) else False
        try:
            cursor.execute(query, params if params else ())
            if commit:
                self.connection.commit()
                return True
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"db_manager: SQL実行エラー: {e}")
            if self.connection and self.connection.is_connected():
                try:
                    self.connection.rollback()
                except mysql.connector.Error as e:
                    print(f"db_manager: ロールバックエラー: {e}")
            return None if (fetchone or fetchall) else False

    async def connect(self):
        if self.connection and self.connection.is_connected():
            if self.cursor is None:
                try:
                    self.cursor = self.connection.cursor()
                except Exception as e:
                    print(f"db_manager: 既存接続からのカーソル再作成エラー: {e}")
                    return None
            return self.cursor
        if self._is_connecting:
            print("db_manager: 接続処理中のため待機します。")
            while self._is_connecting:
                await asyncio.sleep(0.1)
            if self.connection and self.connection.is_connected():
                return self.cursor
        self._is_connecting = True
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            if self.connection.is_connected():
                print("db_manager: MySQLデータベースに接続しました。")
                if self.cursor:
                    try: self.cursor.close()
                    except Exception as e: print(f"db_manager: 既存カーソルクローズエラー: {e}")
                self.cursor = self.connection.cursor()
                return self.cursor
            else:
                print("db_manager: MySQLデータベースへの接続に失敗しました。（db_manager.connect内）")
                return None
        except Exception as e:
            print(f"db_manager: MySQLデータベース接続エラー: {e}")
            self.connection = None
            self.cursor = None
            return None
        finally:
            self._is_connecting = False

    async def close(self):
        try:
            if self.cursor is not None:
                self.cursor.close()
                print("db_manager: カーソルを閉じました。")
            if self.connection and self.connection.is_connected():
                self.connection.close()
                print("db_manager: データベース接続を閉じました。")
        except Exception as e:
            print(f"db_manager: DBクローズエラー：{e}")
        finally:
            self.cursor = None
            self.connection = None

# --- View と Modal クラスは変更なし ---
class CreateServerView(discord.ui.View):
    def __init__(self, original_discord_id, timeout=TIMEOUT_SEC):
        super().__init__(timeout=timeout)
        self.original_user_id = original_discord_id

    @discord.ui.button(label="はい", style=discord.ButtonStyle.danger)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_message("",view=VersionSelectView(interaction),ephemeral=True)
    
    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id)
        await interaction.response.send_message("処理をキャンセルしました。",ephemeral=True)
        self.stop()
        return
    
    async def on_timeout(self):
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id)
        self.stop()
        return await super().on_timeout()

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
    async def version_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_version = select.values[0]
        self.stop()
        await interaction.response.send_message(f"",view=TypeSelectView(self.selected_version, interaction), ephemeral=True)
    
    async def on_timeout(self):
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id)
        return await super().on_timeout()

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
    async def type_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_type = select.values[0]
        self.stop()
        await interaction.response.send_modal(ServerNameModal(interaction.user.id, self.selected_type, self.selected_version))

    async def on_timeout(self):
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id)
        return await super().on_timeout()

class ServerNameModal(discord.ui.Modal):
    def __init__(self, original_user_id: int, selected_type: str = None, selected_version: str = None):
        super().__init__(title="サーバー名入力", timeout=TIMEOUT_SEC)
        self.original_user_id = original_user_id
        self.selected_type = selected_type
        self.selected_version = selected_version
        
        self.server_name_input = discord.ui.TextInput(
            label="サーバー名を入力してください",
            placeholder="例: MyMinecraftServer",
            required=True,
            max_length=64,
            custom_id="server_name_input"
        )
        self.add_item(self.server_name_input)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"サーバー作成処理が進行中です。しばらくお待ちください・・・",ephemeral=True)
        try:
            if not await db_manager_instance.check_server_name_duplicate(interaction.user.id, self.server_name_input.value):
                await interaction.followup.send(f"サーバー名が**重複**しています。過去に使用したサーバー名は、利用できません。もう一度はじめからやり直してください。",ephemeral=True)
                return 
            available_port = None
            for port in range(int(SV_MIN_PORT), int(SV_MAX_PORT) + 1):
                if await db_manager_instance.find_available_port(port):
                    available_port = port
                    break
            if available_port is None:
                await interaction.followup.send("利用可能なポートが見つかりませんでした。処理を中断します。",ephemeral=True)
                return
            await db_manager_instance.insert_creating_data(interaction.user.id, self.server_name_input.value, self.selected_type, self.selected_version, available_port)
            if await self._execute_create_server(available_port):
                await db_manager_instance.update_server_status(interaction.user.id, self.server_name_input.value, 'running')
                await interaction.followup.send(f"サーバー名：`{self.server_name_input.value}` タイプ：`{self.selected_type}` バージョン：`{self.selected_version}`でサーバーの作成に成功しました。\n接続用サーバーアドレス`sv{str(available_port)[-2:]}.{DOMAIN_NAME}`",ephemeral=True)
            else:
                await db_manager_instance.update_server_status(interaction.user.id, self.server_name_input.value, 'error')
                await interaction.followup.send(f"サーバーの作成に失敗しました。",ephemeral=True)
        finally:
            if self.original_user_id in creating_users:
                print("[DEBUG] 排他変数から削除しました。")
                creating_users.remove(self.original_user_id)
        return
    
    async def _execute_create_server(self, sv_port):
        sv_name = self.server_name_input.value
        sv_type = self.selected_type
        sv_ver = self.selected_version
        cmd1 = f"/minecraft/scripts/CREATE-SERVER.sh \"{sv_name}\" \"{sv_type}\" \"{sv_ver}\" \"{sv_port}\""
        cmd2 = f"sudo /minecraft/scripts/CREATE-SERVER-SUDO.sh \"{sv_name}\" \"{sv_type}\" \"{sv_ver}\" \"{sv_port}\""
        success1, _ = await execute_remote_command(SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH, SSH_PASS, cmd1)
        if not success1:
            return False
        success2, _ = await execute_remote_command(SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH, SSH_PASS, cmd2)
        if not success2:
            return False
        return True
    
    async def on_timeout(self):
        global creating_users
        if self.original_user_id in creating_users:
            print("[DEBUG] 排他変数から削除しました。")
            creating_users.remove(self.original_user_id)
        return await super().on_timeout()

class DeleteAgreeView(discord.ui.View):
    def __init__(self, original_discord_id, servers):
        super().__init__(timeout=TIMEOUT_SEC)
        self.original_user_id = original_discord_id
        self.servers = servers

    @discord.ui.button(label="次へ", style=discord.ButtonStyle.danger)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_message("",view=DeleteServerView(self.servers),ephemeral=True)
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        await interaction.response.send_message("処理をキャンセルしました。",ephemeral=True)
        self.stop()

class DeleteServerView(discord.ui.View):
    def __init__(self, servers):
        super().__init__(timeout=TIMEOUT_SEC)
        select_options = [discord.SelectOption(label=s[0], value=s[0]) for s in servers]
        self.servers = servers

        select = discord.ui.Select(
            placeholder="一度削除すると二度とデータは戻りません。",
            options = select_options
        )
        select.callback = self.delete_server_callback
        self.add_item(select)

    async def delete_server_callback(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.send_modal(DeleteConfirmModal(interaction.data["values"][0], self.servers))

class DeleteConfirmModal(discord.ui.Modal):
    def __init__(self, original_sv_name, servers:list):
        super().__init__(title="削除するサーバー名を入力", timeout=TIMEOUT_SEC)
        self.sv_name = original_sv_name
        self.sv_port = [s[1] for s in servers if s[0] == original_sv_name][0]
        self.servers = servers
        print(f"[DEBUG] {self.sv_port}")
        
        self.delete_server_name_input = discord.ui.TextInput(
            label="一度削除すると二度とデータは戻りません。",
            placeholder="例: MyMinecraftServer",
            required=True,
            max_length=64,
            custom_id="delete_server_name_input"
        )
        self.add_item(self.delete_server_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.delete_server_name_input.value == self.sv_name:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(f"削除処理を実行中です。しばらくお待ちください・・・",ephemeral=True)
            if await self._execute_delete_server():
                await db_manager_instance.update_server_status(interaction.user.id, self.sv_name, 'deleting')
                await interaction.followup.send(f"サーバー名：`{self.sv_name}`の削除が完了しました。",ephemeral=True)
                return 
            else:
                await db_manager_instance.update_server_status(interaction.user.id, self.sv_name, 'error')
                await interaction.followup.send(f"サーバー名：`{self.sv_name}`の削除に失敗しました。管理者にお問い合わせください。",ephemeral=True)
                return
        else:
            await interaction.response.send_message(f"入力内容に間違いがあるため、削除処理を中止します。\nもう一度はじめからやり直してください。", ephemeral=True)
            return 

    async def _execute_delete_server(self):
        cmd1 = f"sudo /minecraft/scripts/DELETE-SERVER-SUDO.sh \"{self.sv_port}\""
        success1, _ = await execute_remote_command(SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH, SSH_PASS, cmd1)
        if not success1:
            return False
        return True

class ChangeRoleAdminView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=TIMEOUT_SEC)
        self.original_user_id = user_id

    @discord.ui.button(label="はい", style=discord.ButtonStyle.danger)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        self.stop()
        await interaction.response.send_modal(ChangeRoleAdminModal())
    
    @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("コマンド実行者のみ操作可能です。", ephemeral=True)
            return
        await interaction.response.send_message("処理をキャンセルしました。",ephemeral=True)
        self.stop()
        return

class ChangeRoleAdminModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Adminパスワード入力フォーム", timeout=TIMEOUT_SEC)
        
        self.admin_key_input = discord.ui.TextInput(
            label="Admin認証キーを入力してください",
            placeholder="例：password",
            required=True,
            max_length=64,
            custom_id="admin_key_input"
        )
        self.add_item(self.admin_key_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.admin_key_input.value == ADMIN_KEY:
            if await db_manager_instance.update_user_permission(interaction.user.id, 'admin'):
                max_sv_ct = await db_manager_instance.can_create_max_servers(interaction.user.id)
                await interaction.response.send_message(f"ユーザー`{interaction.user.name}`のパーミッションを`admin`に更新しました。\n現在の最大サーバー作成数は、`{max_sv_ct}`です。",ephemeral=True)
                return await super().on_submit(interaction)
        await interaction.response.send_message(f"キーの認証に失敗しました。処理を中断します。",ephemeral=True)
        return await super().on_submit(interaction)

# Bot起動時処理
@bot.event
async def on_ready():
    global db_manager_instance
    print(f"{bot.user}がオンラインになりました！")
    
    # ------------------
    # スラッシュコマンド同期処理
    # ------------------
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}個のコマンドを同期しました。")
    except Exception as e:
        print(f"コマンド同期エラー: {e}")
    
    db_manager_instance = db_manager()
    initial_cursor = await db_manager_instance.connect()
    if initial_cursor:
        print("DB初期接続が確立されました。")
    else:
        print("DB接続に失敗しました。ボットを終了します。")
        await bot.close()

# Bot終了時処理
@bot.event
async def on_disconnect():
    global db_manager_instance
    if db_manager_instance:
        await db_manager_instance.close()
        print("db_manager: データベース接続を閉じました。")

# --- プレフィックスコマンドからスラッシュコマンドへ変更 ---

# サーバー作成コマンド
@bot.tree.command(name="create", description="新しいMinecraftサーバーを作成します。")
async def create_mc_sv(interaction: discord.Interaction):
    await db_manager_instance.register_user(interaction.user.id, interaction.user.name)
    active_servers = await db_manager_instance.active_servers()
    if active_servers < (int(SV_MAX_PORT) - int(SV_MIN_PORT) + 1):
        if await db_manager_instance.can_create_server(interaction.user.id) and (interaction.user.id not in creating_users):
            creating_users.append(interaction.user.id)
            await interaction.response.send_message(
                f"**{DOMAIN_NAME}**でサーバーを作成しますか？",
                view=CreateServerView(interaction.user.id),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"`{interaction.user.name}`：サーバー作成上限に達しているか、現在作成中のサーバーが存在するため処理を中断します。",
                ephemeral=True
            )
    else:
        await interaction.response.send_message(
            f"稼働出来るサーバー数に空きがありません。",
            ephemeral=True
        )

# サーバー削除コマンド
@bot.tree.command(name="delete", description="現在稼働中のMinecraftサーバーを削除します。")
async def delete_server(interaction: discord.Interaction):
    servers = await db_manager_instance.get_active_user_servers(interaction.user.id)
    if not servers:
        await interaction.response.send_message(
            f"現在稼働中のサーバーが見つかりませんでした。",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(
        f"稼働中のサーバーが見つかりました。サーバー削除ウィザードに進みますか？",
        view=DeleteAgreeView(interaction.user.id, servers),
        ephemeral=True
    )

# Adminロール変更コマンド
@bot.tree.command(name="admin", description="Adminキーを入力してロールを変更します。")
async def admin_role(interaction: discord.Interaction):
    await db_manager_instance.register_user(interaction.user.id, interaction.user.name)
    max_sv_ct = await db_manager_instance.can_create_max_servers(interaction.user.id)
    await interaction.response.send_message(
        f"現在の最大サーバー作成数は、`{max_sv_ct}`です。\nAdminキーを入力することでロールの変更し、最大サーバー作成数を変更することが可能です。\nキー入力を行いますか？",
        view=ChangeRoleAdminView(interaction.user.id),
        ephemeral=True
    )

# Bot実行
bot.run(BOT_TOKEN)