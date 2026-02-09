import json
import asyncio
import tomllib
from pathlib import Path
from typing import Any

from aiomcrcon import Client as RconClient
from aiomcrcon.errors import RCONConnectionError, ClientNotConnectedError
from napcat import (
    __version__,
    NapCatClient,
    GroupMessageEvent,
    Message,
    UnknownMessageSegment,
    Text,
    Image,
    At,
    Face,
    Reply,
    Forward
)


def load_config() -> dict[str, Any]:
    config_path = Path("pyproject.toml")
    if not config_path.exists():
        raise FileNotFoundError("Configuration file 'pyproject.toml' not found.")
    
    with config_path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("bot", {})

def parse__chain(_chain: tuple[Message | UnknownMessageSegment, ...] | str) -> str:
    text_buffer: list[str] = []
    
    for seg in _chain:
        match seg:
            case Text(text=t):
                text_buffer.append(t)
            case Image():
                text_buffer.append("[图片]")
            case At(qq=q, name=n):
                name = n if n is not None else q
                text_buffer.append(f"@{name} ")
            case Face():
                text_buffer.append("[表情]")
            case Reply():
                text_buffer.append("[回复]")
            case Forward():
                text_buffer.append("[转发]")
            case _:
                pass

    return "".join(text_buffer)

# --- 核心优化：通用 RCON 执行器 (带重试) ---
async def execute_rcon_command(rcon: RconClient, command: str, max_retries: int = 1) -> str | None:
    """
    执行 RCON 命令，包含自动重连和重试逻辑。
    返回: 命令响应文本(str)，如果最终失败则返回 None。
    """
    for attempt in range(max_retries + 1):
        try:
            # 尝试发送
            res, _ = await rcon.send_cmd(command)
            return res

        except (ClientNotConnectedError, RCONConnectionError, OSError) as e:
            # 连接错误，尝试重连
            print(f"RCON 执行异常: {e}，正在尝试重连...")
            
            # 如果是最后一次尝试，就不再重连了，直接抛出或返回
            if attempt == max_retries:
                print(f"RCON 命令最终失败: {command}")
                return None

            # 尝试重新建立连接
            try:
                # 某些情况下 close 能清理旧的 broken pipe
                await rcon.close() 
                await rcon.connect()
                print("RCON 重连成功，重试命令...")
                continue # 进入下一次循环重试 send_cmd
            except Exception as connect_err:
                print(f"重连失败: {connect_err}")
                return None
        except Exception as e:
            # 其他逻辑错误（如命令格式错误），不重试
            print(f"未知错误: {e}")
            return None
    return None

async def query_online_players(rcon: RconClient) -> list[str] | None:
    # 复用 execute_rcon_command，享受重连机制
    response = await execute_rcon_command(rcon, "list")
    
    if response is None:
        return None

    part = response.split("online: ")

    if len(part) != 2:
        return None
    
    players_str = part[1].strip()
    players = [p.strip() for p in players_str.split(",")] if players_str else []
    return players


async def send_to_mc(rcon: RconClient, nickname: str, content: str) -> None:
    payload: list[dict[str, Any]] = [
        {"text": "[QQ] ", "color": "gold", "bold": True},
        {"text": f"{nickname}: ", "color": "aqua"},
        {"text": content, "color": "white"}
    ]
    command = f'tellraw @a {json.dumps(payload)}'
    
    # 复用执行器，不需要返回值
    await execute_rcon_command(rcon, command)

async def main() -> None:
    config = load_config()
    target_group = int(config.get("target_group_id", 0))
    host = str(config.get("mc_server_host", "localhost"))
    port = int(config.get("mc_server_port", 25575))
    password = str(config.get("mc_server_password", ""))
    
    if target_group == 0:
        print("错误: 请配置 target_group_id")
        return

    mc_client = RconClient(host, port, password)
    
    # 优化：启动时尝试连接一次
    try:
        await mc_client.connect()
        print("RCON 初始化连接成功")
    except Exception as e:
        print(f"RCON 初始化连接失败: {e} (将在发送消息时自动重试)")

    napcat_url = str(config.get("napcat_url", "ws://localhost:3001"))
    napcat_token = str(config.get("napcat_token", ""))
    
    print(f"开始监听 NapCat: {napcat_url}，目标群: {target_group}")

    while True:
        try:
            async for event in NapCatClient(napcat_url, napcat_token):
                match event:
                    case GroupMessageEvent(group_id=gid, sender=sender, message=message) if int(gid) == target_group:
                        
                        raw_content = parse__chain(message)
                        clean_content = raw_content.strip()

                        if clean_content:
                            display_name = sender.card or sender.nickname or "未知用户"
                            await send_to_mc(mc_client, display_name, clean_content)

                        match clean_content:
                            case ".mc":
                                players = await query_online_players(mc_client)
                                if players is None:
                                    await event.send_msg("无法获取在线玩家列表，请检查 RCON 连接。")
                                elif not players:
                                    await event.send_msg("当前没有在线玩家。")
                                else:
                                    player_list = ", ".join(players)
                                    await event.send_msg(f"当前在线玩家({len(players)} / 40): {player_list}")
                            case ".ping":
                                await event.send_msg("Pong! 机器人在线。")
                            case ".version":
                                await event.send_msg(f"NapCat SDK 版本：{__version__}")
                            case _:
                                pass
                    case _:
                        pass
        except Exception as e:
            print(f"NapCat 连接断开: {e}，5秒后重连...")
            await asyncio.sleep(5)

    # 这里的 close 实际上很难被执行到，除非 break loop
    await mc_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot 已停止")