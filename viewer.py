import os
import json
import asyncio
import random
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest, GetMessagesViewsRequest

with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
channels = config["channels"]
ACCOUNTS_DIR = "accounts"

async def start_account_sessions():
    clients = []
    for session_file in os.listdir(ACCOUNTS_DIR):
        if not session_file.endswith(".session"):
            continue
        name = session_file.replace(".session", "")
        client = TelegramClient(os.path.join(ACCOUNTS_DIR, name), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            print(f"[!] {name} giriş yapılmamış.")
            continue
        clients.append(client)
    return clients

async def get_latest_message_id(client, channel_username):
    try:
        entity = await client.get_entity(channel_username)
        history = await client(GetHistoryRequest(
            peer=entity,
            limit=1,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))
        return history.messages[0].id if history.messages else None
    except Exception as e:
        print(f"[!] {channel_username} son mesaj alınamadı: {e}")
        return None

async def realistic_view(client, channel_username, message_id, delay):
    try:
        await asyncio.sleep(delay)
        await client(JoinChannelRequest(channel_username))
        await client.send_read_acknowledge(channel_username, max_id=message_id)
        entity = await client.get_entity(channel_username)
        await client(GetMessagesViewsRequest(peer=entity, id=[message_id], increment=True))
        print(f"[✓] {client.session.filename} → @{channel_username} görüntülendi ({delay:.1f}s)")
    except Exception as e:
        print(f"[!] {client.session.filename} hata: {e}")

async def main():
    clients = await start_account_sessions()
    if not clients:
        print("Aktif hesap yok.")
        return

    for channel_username in channels:
        message_id = await get_latest_message_id(clients[0], channel_username)
        if not message_id:
            continue

        for client in clients:
            delay = random.uniform(10, 60 * 60)  # 10 saniye - 60 dakika arası gecikme
            asyncio.create_task(realistic_view(client, channel_username, message_id, delay))

    while True:
        await asyncio.sleep(3600)  # Görevler tamamlanana kadar uygulama açık kalır

if __name__ == "__main__":
    asyncio.run(main())
