import paramiko
import asyncio

async def execute_remote_command(
    hostname: str,
    port: int,
    username: str,
    key_filename: str,
    passphrase: str,
    command: str
) -> tuple[bool, str]:
    """
    SSH経由でリモートコマンドを実行し、成功/失敗とエラーメッセージを返す。
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # パラメータは asyncio を考慮し、asyncssh への移行も検討
        # 今は既存の paramiko を使用
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.connect(
                hostname=hostname,
                port=port,
                username=username,
                key_filename=key_filename,
                passphrase=passphrase
            )
        )
        print(f"[DEBUG] SSH接続完了: {hostname}:{port}")

        stdin, stdout, stderr = client.exec_command(command)
        
        # 非同期処理で完了を待つ
        await loop.run_in_executor(None, lambda: stdout.channel.recv_exit_status())
        
        exit_status = stdout.channel.recv_exit_status()

        if exit_status != 0:
            error_output = stderr.read().decode('utf-8').strip()
            print(f"[ERROR] コマンド実行失敗（ステータスコード: {exit_status}）。コマンド: '{command}' エラー: {error_output}")
            return False, error_output
        else:
            print(f"[DEBUG] コマンド実行成功: '{command}'")
            return True, ""

    except paramiko.AuthenticationException:
        error_msg = "SSH認証エラー：鍵ファイルまたはパスフレーズが正しくありません。"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except paramiko.SSHException as ssh_ex:
        error_msg = f"SSH接続エラー：{ssh_ex}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"予期せぬエラーが発生しました：{e}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    finally:
        client.close()
        print("[DEBUG] SSH接続を閉じました。")