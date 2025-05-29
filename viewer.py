import os
import json
import asyncio
import random
from datetime import datetime, time, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetMessagesViewsRequest

# Config dosyasını oku
with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
channels = config["channels"]

ACCOUNTS_DIR = "accounts"

# Tüm hesapları yükle
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

# Yüzde bazlı zaman dağılımı
def assign_clients_time_based(clients):
    total = len(clients)

    skip_pct = random.randint(5, 10)
    skip_count = round(total * skip_pct / 100)
    remaining = total - skip_count

    early_pct = random.randint(20, 30)
    main_pct = 70  # 09:30 - 10:30
    late_pct = 100 - early_pct - main_pct - skip_pct

    early_count = round(remaining * early_pct / 100)
    main_count = round(remaining * main_pct / 100)
    late_count = remaining - early_count - main_count

    random.shuffle(clients)
    return {
        "skip": clients[:skip_count],
        "early": clients[skip_count:skip_count+early_count],
        "main": clients[skip_count+early_count:skip_count+early_count+main_count],
        "late": clients[skip_count+early_count+main_count:]
    }

# Mesajı belirli gecikmeyle görüntüle
async def realistic_view(client, channel_username, message_id, delay):
    try:
        await asyncio.sleep(delay)
        await client(JoinChannelRequest(channel_username))
        await client.send_read_acknowledge(channel_username, max_id=message_id)
        entity = await client.get_entity(channel_username)
        await client(GetMessagesViewsRequest(
            peer=entity,
            id=[message_id],
            increment=True
        ))
        print(f"[✓] {client.session.filename} → @{channel_username} görüntülendi ({delay:.1f}s)")
    except Exception as e:
        print(f"[!] {client.session.filename} hata: {e}")

# Mesaj geldiğinde
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
        msg_id = event.id
        print(f"\n📨 Yeni mesaj: @{username} (ID: {msg_id})")

        groups = assign_clients_time_based(clients)
        now = datetime.now()

        for group, user_list in groups.items():
            if group == "skip":
                for client in user_list:
                    print(f"[⏩] {client.session.filename} bu mesajı atladı.")
                continue

            for client in user_list:
                if group == "early":
                    # Mesajdan sonra 0–30 dakika içinde rastgele
                    delay = random.uniform(0, 30 * 60)
                elif group == "main":
                    # Mesajdan sonra 30–90 dakika içinde
                    delay = random.uniform(30 * 60, 90 * 60)
                elif group == "late":
                    # Mesajdan sonra 1.5–24 saat içinde
                    delay = random.uniform(90 * 60, 24 * 60 * 60)

                asyncio.create_task(realistic_view(client, username, msg_id, delay))

    print(f"[✅] {len(clients)} hesapla dinleniyor, yeni gönderiler bekleniyor...\n")
    await main_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
