from dotenv import load_dotenv
from discord.ext import commands
import os
import discord
import paramiko
import mysql.connector

# 環境変数読み込み
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Bot設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# DB接続変数
db_connection = None
db_cursor = None

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
        return db_cursor
    new_connection = get_db_connection()
    if new_connection:
        db_connection = new_connection
        if db_cursor:
            try: db_cursor.close()
            except mysql.connector.Error as e: print(f"カーソルのクローズエラー：{e}")
        db_cursor = db_connection.cursor()
    else:
        print("DB接続エラー：get_db_connectionがNoneを返しました。")
        return None
    return db_cursor

# サーバー情報を設定するViewクラス
class ServerConfigView(discord.ui.View):
    def __init__(self, discord_user_id):
        super().__init__(timeout=60)
        self.original_user_id = discord_user_id
        self.selected_type = None
        self.selected_version = None
        
        # サーバーの種類選択ドロップダウン
        self.type_objects = discord.ui.Select(
            placeholder="サーバーの種類を選択してください",
            options=[
                discord.SelectOption(label="Vanilla", value="vanilla"),
                discord.SelectOption(label="Spigot", value="spigot"),
                discord.SelectOption(label="Paper", value="paper"),
                discord.SelectOption(label="Forge", value="forge")
            ],
            custom_id="server_type_select"
        )
        self.add_item(self.type_objects) # Viewにサーバータイプ選択を追加
        # サーバーのバージョン選択ドロップダウン
        self.version_objects = discord.ui.Select(
            placeholder="サーバーのバージョンを選択してください",
            options=[
                discord.SelectOption(label="1.21.8", value="1.21.8"),
                discord.SelectOption(label="1.21.7", value="1.21.7"),
                discord.SelectOption(label="1.21.6", value="1.21.6"),
                discord.SelectOption(label="1.21.5", value="1.21.5"),
                discord.SelectOption(label="1.21.4", value="1.21.4"),
                discord.SelectOption(label="1.21.3", value="1.21.3"),
                discord.SelectOption(label="1.21.2", value="1.21.2"),
                discord.SelectOption(label="1.21.1", value="1.21.1")
            ],
            custom_id="server_version_select"
        )
        self.add_item(self.version_objects) # Viewにサーバーバージョン選択を追加
        # 次に進むためのボタン
        self.next_button = discord.ui.Button(
            label="次へ",
            style=discord.ButtonStyle.primary,
            custom_id="next_to_button"
        )
        self.add_item(self.next_button) # Viewに次へボタンを追加
    # 本人か確認
    async def check_user(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("この操作は、コマンドを実行した本人のみが実行可能です。", ephemeral=True)
            return False
        return True
    # サーバータイプ選択時の処理
    @discord.ui.select(custom_id="server_type_select")
    async def server_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not await self.check_user(interaction):
            return
        self.selected_type = select.values[0] # プルダウンはリストで返ってくる為
        await interaction.response.send_message(f"サーバーの種類を `{self.selected_type}` に設定しました。", ephemeral=True)
    # サーバーバージョン選択時の処理
    @discord.ui.select(custom_id="server_version_select")
    async def server_version_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not await self.check_user(interaction):
            return
        self.selected_version = select.values[0] # プルダウンはリストで返ってくる為
        await interaction.response.send_message(f"サーバーのバージョンを `{self.selected_version}` に設定しました。", ephemeral=True)
    # 次へボタン押下時の処理
    @discord.ui.button(custom_id="next_to_button")
    async def next_button_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user(interaction):
            return
        if not self.selected_type or not self.selected_version:
            await interaction.response.send_message("サーバーの種類とバージョンを選択してください。", ephemeral=True)
            return
        # サーバー名入力モーダルを表示
        await interaction.response.send_modal(ServerNameModal(self.selected_type, self.selected_version))
        self.stop()  # Viewを停止して次の処理へ進む

# サーバー名入力用モーダルクラス
class ServerNameModal(discord.ui.Modal, title="サーバー作成ウィザード"):
    sv_name = discord.ui.TextInput(
        label="サーバー名を入力してください",
        placeholder="例: MyMinecraftServer (２つ目以降同じ名前は不可)",
        max_length=64,
        required=True,
    )
    # 選択されたサーバーの種類とバージョンを受取り、selfの属性に保存
    def __init__(self, selected_type: str, selected_version: str):
        super().__init__()
        self.selected_type = selected_type
        self.selected_version = selected_version

    # モーダル受取時の処理
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"サーバー作成を受け付けました！\n"
            f"**サーバー名**: `{self.sv_name.value}`\n"
            f"**サーバータイプ**: `{self.selected_type}`\n"
            f"**バージョン**: `{self.selected_version}`\n",
            ephemeral=True
        )
        print(f"サーバー名受信: '{self.sv_name.value}' (by {interaction.user.id})")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message("フォームの処理中にエラーが発生しました。時間を置いて再度お試しください。", ephemeral=True)
        print(f"モーダル処理エラー: {error}")

# 作成確認ビュー (YES/NOボタン)
class CreateServerView(discord.ui.View):
    def __init__(self, original_user_id: int):
        super().__init__(timeout=60)
        self.original_user_id = original_user_id

    @discord.ui.button(label="YES", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("この操作は、コマンドを実行した本人のみが実行可能です。", ephemeral=True)
            return
        
        # メッセージ本文を追加し、ServerConfigViewを表示
        await interaction.response.send_message(
            "Minecraftサーバーの設定を開始します。\n"
            "まずはサーバーの種類とバージョンを選択してください。",
            view=ServerConfigView(self.original_user_id) # ServerConfigViewのインスタンスを渡す
        )
        self.stop()

    @discord.ui.button(label="NO", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("この操作は、コマンドを実行した本人のみが実行可能です。", ephemeral=True)
            return
        
        await interaction.response.send_message("サーバー作成をキャンセルしました。", ephemeral=True)
        self.stop()

# Bot起動時処理
@bot.event
async def on_ready():
    print(f"{bot.user}がオンラインになりました！")
    current_cursor = await ensure_db_connection()
    if current_cursor:
        print("DB初期接続が確立されました。")
    else:
        print("DB接続に失敗しました。ボットを終了します。")
        await bot.close()

# コマンド関数定義
@bot.command(name=DOMAIN_NAME)
async def create_mc_sv(ctx: commands.Context):
    current_cursor = await ensure_db_connection()
    
    await ctx.send("サーバー作成ウィザードを開始しますか。", view=CreateServerView(ctx.author.id))

# Bot実行
bot.run(BOT_TOKEN)