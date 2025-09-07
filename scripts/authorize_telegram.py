#!/usr/bin/env python3
"""
Скрипт для первоначальной авторизации Telegram Pyrogram клиента.
Запустите этот скрипт локально, чтобы создать файл сессии.
"""

import asyncio
import os
from pyrogram import Client

async def authorize():
    # Получаем данные из переменных окружения
    api_id = input("Введите TP_API_ID: ").strip()
    api_hash = input("Введите TP_API_HASH: ").strip()
    phone_number = input("Введите TP_PHONE_NUMBER: ").strip()
    password = input("Введите TP_PASSWORD (если включена двухфакторная аутентификация, иначе оставьте пустым): ").strip()
    
    if not api_id or not api_hash:
        print("Ошибка: Укажите TP_API_ID и TP_API_HASH в переменных окружения")
        return
    
    if not phone_number:
        print("Ошибка: Укажите TP_PHONE_NUMBER в переменных окружения")
        return
    
    # Создаем директорию для сессий если её нет
    sessions_dir = "../sessions"
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir)
    
    print(f"API ID: {api_id}")
    print(f"Phone: {phone_number}")
    print(f"Sessions dir: {sessions_dir}")
    
    # Создаем клиент
    client = Client(
        name="tp_session",
        api_id=int(api_id),
        api_hash=api_hash,
        phone_number=phone_number,
        workdir=sessions_dir,
        password=password
    )
    
    try:
        print("Запускаем авторизацию...")
        await client.start()
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        print(f"Успешно авторизован как: {me.first_name} (@{me.username})")
        print(f"Файл сессии создан в: {sessions_dir}/tp_session.session")
        
    except Exception as e:
        print(f"Ошибка авторизации: {e}")
    finally:
        await client.stop()

if __name__ == "__main__":
    print("=== Telegram Pyrogram Authorization ===")
    print("Этот скрипт поможет создать файл сессии для Telegram.")
    print("Убедитесь, что установлены переменные окружения:")
    print("- TP_API_ID")
    print("- TP_API_HASH") 
    print("- TP_PHONE_NUMBER")
    print("- TP_PASSWORD (если включена двухфакторная аутентификация)")
    print()
    
    asyncio.run(authorize())
