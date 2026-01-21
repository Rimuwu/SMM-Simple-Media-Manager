import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import gzip
import shutil

# Конфигурация из переменных окружения (уже загружены через entrypoint)
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'app')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'app_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'app_password')

# Настройки бэкапа
BACKUP_DIR = Path('/backups')
RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
COMPRESS = os.getenv('BACKUP_COMPRESS', 'true').lower() == 'true'

def ensure_backup_dir():
    """Создает директорию для бэкапов если её нет"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Backup directory: {BACKUP_DIR}")

def create_backup():
    """Создает бэкап базы данных"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_{POSTGRES_DB}_{timestamp}.sql"
    backup_path = BACKUP_DIR / backup_filename
    
    print(f"📦 Creating backup: {backup_filename}")
    
    # Настройка окружения для pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = POSTGRES_PASSWORD
    
    # Команда pg_dump
    cmd = [
        'pg_dump',
        '-h', POSTGRES_HOST,
        '-p', POSTGRES_PORT,
        '-U', POSTGRES_USER,
        '-d', POSTGRES_DB,
        '-F', 'p',  # plain text format
        '-f', str(backup_path)
    ]
    
    try:
        # Выполнение pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Проверка создания файла
        if not backup_path.exists():
            raise Exception("Backup file was not created")
        
        file_size = backup_path.stat().st_size
        print(f"✓ Backup created successfully: {file_size / 1024 / 1024:.2f} MB")
        
        # Сжатие если включено
        if COMPRESS:
            compressed_path = backup_path.with_suffix('.sql.gz')
            print(f"🗜️  Compressing backup...")
            
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Удаление несжатого файла
            backup_path.unlink()
            
            compressed_size = compressed_path.stat().st_size
            compression_ratio = (1 - compressed_size / file_size) * 100
            print(f"✓ Compressed to: {compressed_size / 1024 / 1024:.2f} MB ({compression_ratio:.1f}% reduction)")
            
            return compressed_path
        
        return backup_path
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during backup creation:", file=sys.stderr)
        print(f"   STDOUT: {e.stdout}", file=sys.stderr)
        print(f"   STDERR: {e.stderr}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        raise

def rotate_backups():
    """Удаляет старые бэкапы согласно политике хранения"""
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0
    kept_count = 0
    
    print(f"🔄 Rotating backups (keeping last {RETENTION_DAYS} days)...")
    
    # Поиск всех бэкапов
    for backup_file in BACKUP_DIR.glob('backup_*.sql*'):
        try:
            # Извлечение даты из имени файла
            file_timestamp = backup_file.stem.split('_')[-2] + backup_file.stem.split('_')[-1]
            file_date = datetime.strptime(file_timestamp[:8], '%Y%m%d')
            
            if file_date < cutoff_date:
                file_size = backup_file.stat().st_size / 1024 / 1024
                backup_file.unlink()
                print(f"  🗑️  Deleted old backup: {backup_file.name} ({file_size:.2f} MB)")
                deleted_count += 1
            else:
                kept_count += 1
                
        except (ValueError, IndexError) as e:
            print(f"  ⚠️  Skipping file with invalid name format: {backup_file.name}")
            continue
    
    print(f"✓ Rotation complete: {deleted_count} deleted, {kept_count} kept")

def list_backups():
    """Выводит список существующих бэкапов"""
    backups = sorted(BACKUP_DIR.glob('backup_*.sql*'), reverse=True)
    
    if not backups:
        print("📭 No backups found")
        return
    
    print(f"\n📚 Available backups ({len(backups)}):")
    total_size = 0
    
    for backup in backups:
        size = backup.stat().st_size
        total_size += size
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"  • {backup.name}")
        print(f"    Size: {size / 1024 / 1024:.2f} MB | Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n💾 Total backup size: {total_size / 1024 / 1024:.2f} MB")

def main():
    """Основная функция"""
    print("=" * 60)
    print("PostgreSQL Backup Script")
    print(f"Database: {POSTGRES_DB} @ {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"Retention: {RETENTION_DAYS} days | Compression: {COMPRESS}")
    print("=" * 60)
    print()
    
    try:
        # Создание директории для бэкапов
        ensure_backup_dir()
        
        # Создание нового бэкапа
        backup_path = create_backup()
        print(f"✓ Backup saved: {backup_path}")
        
        # Ротация старых бэкапов
        rotate_backups()
        
        # Список всех бэкапов
        list_backups()
        
        print("\n✅ Backup completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Backup failed: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
