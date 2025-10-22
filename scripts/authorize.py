import asyncio
import getpass
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


async def main() -> None:
    load_dotenv()

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_name = os.getenv("TELEGRAM_SESSION_NAME", "telegram_session")

    if not api_id or not api_hash:
        raise RuntimeError("Defina TELEGRAM_API_ID e TELEGRAM_API_HASH no ambiente ou em um arquivo .env.")

    phone = os.getenv("TELEGRAM_PHONE") or input("Informe o telefone com código do país (ex: +5511999999999): ").strip()
    client = TelegramClient(session_name, int(api_id), api_hash)

    await client.connect()

    if await client.is_user_authorized():
        print("Sessão já autorizada.")
        await client.disconnect()
        return

    await client.send_code_request(phone)
    code = input("Digite o código recebido pelo Telegram: ").strip()

    try:
        await client.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        password = getpass.getpass("Digite a senha do segundo fator: ").strip()
        await client.sign_in(password=password)

    await client.disconnect()
    print("Autorização concluída. Sessão salva em", session_name + ".session")


if __name__ == "__main__":
    asyncio.run(main())
