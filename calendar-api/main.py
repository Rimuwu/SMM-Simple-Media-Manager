import asyncio
import uvicorn
from modules.api import app
from modules.logs import calendar_logger


async def api_start():
    calendar_logger.info("Starting Calendar API...")

    config = uvicorn.Config(app, 
                            host="0.0.0.0", 
                            port=8001, # 8001
                            log_level="warning"
                            )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    tasks = [
        asyncio.create_task(api_start())
    ]

    # Запускаем все таски параллельно
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
