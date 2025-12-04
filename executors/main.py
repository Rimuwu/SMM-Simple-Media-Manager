import asyncio
import uvicorn
import logging


from modules.executors_manager import executors_start
from modules.api import app


async def api_start():
    config = uvicorn.Config(app, 
                            host="0.0.0.0", 
                            port=8003, 
                            # log_level="info"
                            )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    # logging.basicConfig(level=logging.INFO)

    tasks = await executors_start() # Запускаем всех исполнителей

    tasks.append(
        asyncio.create_task(api_start())
        ) # Добавляем запуск API в список тасков

    # Запускаем все таски параллельно
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
