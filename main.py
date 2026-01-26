import json
import asyncio
import tomllib
from pathlib import Path
from typing import Any

from aiomcrcon import Client as RconClient
from napcat import NapCatClient, GroupMessageEvent

from napcat.types import (
    MessageText, 
    MessageAt, 
    MessageImage, 
    MessageFace, 
    MessageReply,
    MessageSegmentType
)

def load_config() -> dict[str, Any]:
    config_path = Path("pyproject.toml")
    if not config_path.exists():
        raise FileNotFoundError("Configuration file 'pyproject.toml' not found.")
    
    with config_path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("bot", {})

def parse_message_chain(message_chain: tuple[MessageSegmentType, ...]) -> str:
    """
    将复杂的 QQ 消息链转换为适合 MC 显示的纯文本
    """
    text_buffer: list[str] = []
    
    for seg in message_chain:
        match seg:
            case MessageText(data=d):
                text_buffer.append(d.text)
            
            case MessageImage():
                text_buffer.append("[图片]")
            
            case MessageAt(data=d):
                name = d.name if d.name is not None else d.qq
                text_buffer.append(f"@{name} ")
                
            case MessageFace():
                text_buffer.append("[表情]")
            
            case MessageReply():
                text_buffer.append("[回复] ")
                
            case _:
                pass

    return "".join(text_buffer)

async def reconnect_rcon(rcon: RconClient, max_attempts: int = 3) -> bool:
    """
    RCON 重连逻辑，返回是否成功
    """
    for attempt in range(1, max_attempts + 1):
        try:
            await rcon.connect()
            print(f"RCON 重连成功 (尝试 {attempt}/{max_attempts})")
            return True
        except Exception as e:
            print(f"RCON 重连失败 (尝试 {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                await asyncio.sleep(1)
    
    print("RCON 重连失败，已达到最大尝试次数")
    return False

async def send_to_mc(rcon: RconClient, nickname: str, content: str) -> None:
    """
    使用 tellraw 发送彩色 JSON 消息到 MC，失败时自动重连
    """
    payload: list[dict[str, Any]] = [
        {"text": "[QQ] ", "color": "gold", "bold": True},
        {"text": f"{nickname}: ", "color": "aqua"},
        {"text": content, "color": "white"}
    ]
    
    command = f'tellraw @a {json.dumps(payload)}'
    
    try:
        await rcon.send_cmd(command)
        print(f"已转发: {nickname} -> {content}")
    except Exception as e:
        print(f"转发失败 (RCON Error): {e}")
        print("尝试重连 RCON...")
        if await reconnect_rcon(rcon):
            # 重连成功后再试一次
            try:
                await rcon.send_cmd(command)
                print(f"已转发: {nickname} -> {content}")
            except Exception as e:
                print(f"重连后仍然失败: {e}，放弃本次消息")
        else:
            print("重连失败，放弃本次消息")

async def main() -> None:
    config = load_config()
    target_group = int(config.get("target_group_id", 0))
    host = str(config.get("mc_server_host", "localhost"))
    port = int(config.get("mc_server_port", 25575))
    password = str(config.get("mc_server_password", ""))
    
    if target_group == 0:
        print("错误: 请在 pyproject.toml 中配置 target_group_id")
        return

    mc_client = RconClient(host, port, password)
    print("RCON 客户端已创建，将在收到消息时自动连接")

    napcat_url = str(config.get("napcat_url", "ws://localhost:3001"))
    napcat_token = str(config.get("napcat_token", ""))
    
    # NapCat 连接重试逻辑
    while True:
        try:
            async with NapCatClient(napcat_url, napcat_token) as client:
                print("NapCat 连接成功")
                async for event in client.events():
                    match event:
                        case GroupMessageEvent(group_id=gid, sender=sender, message=message) if int(gid) == target_group:
                            
                            content = parse_message_chain(message)
                            
                            if content.strip():
                                display_name = sender.card or sender.nickname or "未知用户"
                                await send_to_mc(mc_client, display_name, content)
                        
                        case _:
                            pass
        except Exception as e:
            print(f"NapCat 连接断开: {e}，5秒后重连...")
            await asyncio.sleep(5)

    await mc_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot 已停止")