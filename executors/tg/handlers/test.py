import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from tg.filters.authorize import Authorize
from tg.filters.role_filter import RoleFilter
from modules.logs import executors_logger as logger
from modules.executors_manager import manager
from global_modules.brain_client import brain_client

client_executor = manager.get("telegram_executor")
dp: Dispatcher = client_executor.dp
bot: Bot = client_executor.bot


@dp.message(Command("test"), RoleFilter("admin"))
async def run_e2e_test(message: Message):
    """Запускает интеграционный тест-воркфлоу: создание карточек, обновления, загрузка файлов, смена статусов и отправка"""
    chat_id = message.chat.id
    await message.answer("🚀 Запуск E2E теста: создание карточек...")

    results = []

    async def safe_send(text: str):
        try:
            await message.answer(text)
        except Exception:
            logger.exception("Failed to send message to chat")

    try:
        # 1) Создать public карточку
        public_payload = {
            "title": "E2E Test - Public",
            "description": "Test public card",
            "deadline": None,
            "send_time": None,
            "executor_id": None,
            "customer_id": None,
            "editor_id": None,
            "channels": [],
            "need_check": True,
            "image_prompt": None,
            "tags": [],
            "type_id": "public"
        }
        res, status = await brain_client.api.post("/card/create", data=public_payload, no_filter_none=True)
        if status != 200 or not res.get('card_id'):
            await safe_send(f"❌ Не удалось создать public карточку: {res} (status={status})")
            return
        public_card_id = res['card_id']
        await safe_send(f"✅ Public card created: {public_card_id}")

        # 2) Создать private карточку
        private_payload = public_payload.copy()
        private_payload.update({"title": "E2E Test - Private", "type_id": "private"})
        res2, status2 = await brain_client.api.post("/card/create", data=private_payload, no_filter_none=True)
        if status2 != 200 or not res2.get('card_id'):
            await safe_send(f"❌ Не удалось создать private карточку: {res2} (status={status2})")
            return
        private_card_id = res2['card_id']
        await safe_send(f"✅ Private card created: {private_card_id}")

        # 3) Обновить карточку: поменять название и добавить теги
        update_res = await brain_client.update_card(
            card_id=public_card_id,
            name="E2E Public Updated",
            tags=["content", "stream"]
        )
        if not update_res:
            await safe_send("❌ Не удалось обновить public карточку")
        else:
            await safe_send("✅ Public card updated")

        await brain_client.api.post(
            '/card/set-content',
            data={
                'card_id': public_card_id,
                'content': 'This is the updated content for E2E testing.',
                'client_key': None
            }
        )

        # 4) Добавить файл в public карточку (через brain-api /files/upload)
        await safe_send("⬆️ Загружаю файл в public карточку...")
        file_content = b"Hello, this is an E2E test file"
        async with aiohttp.ClientSession() as s:
            data = aiohttp.FormData()
            data.add_field('file', file_content, filename='e2e_test.txt', content_type='text/plain')
            async with s.post(f"{brain_client.api.base_url}/files/upload/{public_card_id}", data=data) as resp:
                j = await resp.json()
                if resp.status != 200:
                    await safe_send(f"❌ Ошибка загрузки файла: {resp.status} {j}")
                else:
                    uploaded_filename = j.get('filename')
                    await safe_send(f"✅ Файл загружен: {uploaded_filename}")

        # 5) Список файлов
        files_list, st = await brain_client.api.get(f"/files/list/{public_card_id}")
        if st == 200:
            await safe_send(f"📁 Files for public card: {len(files_list.get('files', []))}")
        else:
            await safe_send(f"❌ Не удалось получить список файлов: {st}")

        # 6) Change status -> ready -> sent
        from global_modules.classes.enums import CardStatus
        await safe_send("🔁 Меняю статус карточки на 'ready'...")
        res_ready = await brain_client.change_card_status(public_card_id, CardStatus.ready)
        if not res_ready:
            await safe_send("⚠️ Не удалось перевести карточку в статус 'ready'")
        else:
            await safe_send("✅ Статус -> ready")

        await safe_send("🔁 Меняю статус карточки на 'sent' (симуляция отправки)...")
        res_sent = await brain_client.change_card_status(public_card_id, CardStatus.sent)
        if not res_sent:
            await safe_send("⚠️ Не удалось перевести карточку в статус 'sent'")
        else:
            await safe_send("✅ Статус -> sent")

    except Exception as e:
        logger.exception("E2E test failed")
        await safe_send(f"❌ E2E test failed: {e}")
        return

    await safe_send("🎉 E2E тест завершён — проверьте результаты в базе и в storage_api")

