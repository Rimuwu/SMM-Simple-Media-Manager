"""
Простой пример использования системы исполнителей
"""
import asyncio
from executor import ExecutorManager
from os import getenv
from tg.main import TelegramExecutor
from vk.main import VKExecutor

def main():
    print('start executors')
    manager = ExecutorManager()
    
    clients = {

        # "vk": {
        #     "base_class": VKExecutor
        # },

        "telegram": {
            "base_class": TelegramExecutor,
            "config": {
                "token": getenv('TG_BOT_TOKEN')
            }
        }
    }

    for key, client in clients.items():
        executor = client['base_class'](
            config=client['config']
        )
        manager.register(executor)
        print(f'{key} executor register...')

    print(manager.get_available())
    manager.start_all()
    print('end-2')


if __name__ == "__main__":
    # asyncio.run(main())
    main()
