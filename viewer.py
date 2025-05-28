import os
import json
import asyncio
import random
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetMessagesViewsRequest
from telethon.tl.types import InputPeerChannel, InputMessageID

# Config dosyasını oku
with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
channels = config["channels"]
delay_min, delay_max = config["delay_range_seconds"]

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

async def realistic_view(client, channel_username):
    try:
        # Kanala katıl (zaten üyeyse hata vermez)
        await client(JoinChannelRequest(channel_username))
        await asyncio.sleep(random.randint(2, 5))  # Doğal bekleme

        async for message in client.iter_messages(channel_username, limit=1):
            await asyncio.sleep(random.randint(delay_min, delay_max))

            # Mesajı "okundu" olarak işaretle
            await client.send_read_acknowledge(channel_username, max_id=message.id)

            # Kanal bilgisi alalım
            channel_entity = await client.get_entity(channel_username)

            # Görüntüleme sayısını arttırmaya çalış
            try:
                views = await client(GetMessagesViewsRequest(
                    peer=channel_entity,
                    id=[message.id],
                    increment=True
                ))
                print(f"[✓] {client.session.filename} mesajı görüntüledi ve view sayısı arttırıldı: {views}")
            except Exception as e:
                print(f"[!] {client.session.filename} view sayısı arttırılamadı: {e}")

            print(f"[✓] {client.session.filename} ile {channel_username} mesaj okundu olarak işaretlendi.")
            return

    except Exception as e:
        print(f"[X] {client.session.filename} hata: {e}")

async def main():
    clients = await start_account_sessions()
    if not clients:
        print("Aktif hesap yok.")
        return

    main_client = clients[0]

    @main_client.on(events.NewMessage(chats=channels))
    async def handler(event):
        channel = await event.get_chat()
        username = channel.username or channel.id
        print(f"[📢] Yeni mesaj: {username} / ID: {event.id}")

        for client in clients:
            asyncio.create_task(realistic_view(client, username))

    print("[✅] Bot çalışıyor, yeni gönderiler bekleniyor...")
    await main_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
