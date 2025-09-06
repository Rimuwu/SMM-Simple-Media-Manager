from modules.executor import ExecutorManager
from global_modules.logs import logger
from modules.constants import EXECUTORS
from modules.json_format import check_env_config
from global_modules.function_way import str_to_func

manager = ExecutorManager()

async def executors_start():
    logger.info("Starting Executors...")

    for exe_name, executor_data in EXECUTORS.items():
        base_class = str_to_func(executor_data['base_class'])

        executor = base_class(
            config=check_env_config(
                executor_data['config'] # Заменяем данные на переменные из окружения
                ),
            executor_name=exe_name
        )
        manager.register(executor)

    logger.info(
        f"Registered executors: {list(manager.executors.keys())}"
        )
    tasks = manager.start_all()
    return tasks