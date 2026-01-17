#!/usr/bin/env python3
"""
Скрипт для восстановления базы данных PostgreSQL из бэкапа.

Использование:
    python restore_backup.py <имя_бэкапа>
    python restore_backup.py smm_backup_20260117T103628Z.sql
    python restore_backup.py backups/smm_backup_20260117T103628Z.sql
"""

import sys
import subprocess
from pathlib import Path


# Имя контейнера в docker-compose
CONTAINER_NAME = "postgres"


def load_env() -> dict:
    """Загрузить переменные из .env файла."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    env_file = project_dir / ".env"
    
    env_vars = {}
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def get_db_config() -> tuple[str, str]:
    """Получить конфигурацию БД из .env или использовать значения по умолчанию."""
    env_vars = load_env()
    postgres_user = env_vars.get('POSTGRES_USER', 'app_user')
    postgres_db = env_vars.get('POSTGRES_DB', 'app')
    return postgres_user, postgres_db


def restore_backup(backup_path: Path):
    """Восстановить базу данных из файла бэкапа."""
    
    postgres_user, postgres_db = get_db_config()
    
    if not backup_path.exists():
        print(f"❌ Файл не найден: {backup_path}")
        sys.exit(1)
    
    print(f"📦 Восстановление из: {backup_path}")
    print(f"🗄️  База данных: {postgres_db}")
    print(f"👤 Пользователь: {postgres_user}")
    print()
    
    # Подтверждение
    confirm = input("⚠️  Это перезапишет данные в базе. Продолжить? (y/n): ")
    if confirm.lower() not in ('y', 'yes', 'д', 'да'):
        print("Отменено.")
        sys.exit(0)
    
    print()
    print("🔄 Выполняется восстановление...")
    
    # Читаем содержимое файла
    with open(backup_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Выполняем команду через docker compose exec
    cmd = [
        "docker", "compose", "exec", "-T",
        CONTAINER_NAME,
        "psql", "-U", postgres_user, "-d", postgres_db
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=sql_content,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print("✅ База данных успешно восстановлена!")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Ошибка при восстановлении:")
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        print("❌ Docker не найден. Убедитесь, что Docker установлен и запущен.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Использование: python restore_backup.py <имя_бэкапа>")
        print("Пример: python restore_backup.py smm_backup_20260117T103628Z.sql")
        sys.exit(1)
    
    backup_name = sys.argv[1]
    
    # Определяем путь к бэкапу
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    backups_dir = project_dir / "backups"
    
    backup_path = Path(backup_name)
    
    # Если указано только имя файла, ищем в папке backups
    if not backup_path.exists():
        backup_path = backups_dir / backup_name
    
    # Если всё ещё не найден, добавляем .sql
    if not backup_path.exists() and not backup_name.endswith('.sql'):
        backup_path = backups_dir / f"{backup_name}.sql"
    
    restore_backup(backup_path)


if __name__ == "__main__":
    main()
