# 📱 SMM — Simple Media Manager

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**Микросервисная система управления контентом для социальных сетей**

*Автоматизация публикаций • Интеграция с Kaiten • Google Calendar • Telegram Bot • VK API*

</div>

---

## 📖 О проекте

**SMM (Simple Media Manager)** — это комплексная система для управления контентом в социальных сетях, построенная на микросервисной архитектуре. Проект объединяет работу с таск-менеджером Kaiten, Google Calendar и платформами Telegram и VKontakte в единую экосистему для SMM-специалистов.

### ✨ Ключевые возможности

- 🎯 **Управление задачами** — интеграция с Kaiten для отслеживания карточек контента
- 📅 **Планирование публикаций** — синхронизация с Google Calendar для расписания постов
- 🤖 **Telegram Bot** — удобный интерфейс для создания и управления контентом
- 📢 **VK Publishing** — автоматическая публикация постов в группы ВКонтакте
- 🧠 **AI-генерация** — интеграция с AI для помощи в создании контента
- 👥 **Ролевая система** — разделение на копирайтеров, редакторов и администраторов
- 📊 **Статистика** — отслеживание выполненных задач по периодам

---

## 🏗️ Архитектура

Проект состоит из 4 микросервисов, взаимодействующих через REST API:

```
┌──────────────────────────────────────────────────────────────────┐
│                        SMM System                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Calendar API  │◄───│  Brain API   │◄──►│  Executors   │       │
│  │  (Port 8001)  │    │  (Port 8000) │    │  (Port 8003) │       │
│  └───────┬───────┘    └──────────────┘    └───────┬──────┘       │
│          │                                        │              │
│          │            ┌──────────────┐            │              │
│          └───────────►│  PostgreSQL  │◄───────────┘              │
│                       │  (Port 5432) │                           │
│                       └──────────────┘                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │             Внешние сервисы             │
        ├─────────────────────────────────────────┤
           📋 Kaiten API      📅 Google Calendar 
           💬 Telegram        📢 VKontakte       
        └─────────────────────────────────────────┘
```

### 🧠 Brain API (Порт 8000)

Центральный сервис управления данными и бизнес-логикой:

- **Управление карточками** — CRUD операции для контент-задач
- **Пользователи и роли** — система авторизации и прав доступа
- **Интеграция Kaiten** — синхронизация с таск-менеджером
- **Планировщик задач** — автоматическое выполнение по расписанию
- **AI эндпоинты** — генерация контента с помощью AI
- **Сцены** — управление состояниями пользователей бота

### 📅 Calendar API (Порт 8001)

Сервис работы с Google Calendar:

- **Создание событий** — планирование публикаций в календаре
- **Управление расписанием** — CRUD операции для событий
- **Проверка доступности** — контроль пересечений в расписании
- **Синхронизация** — связь календаря с карточками контента

### ⚡ Executors (Порт 8003)

Сервис публикации и взаимодействия с платформами:

- **Telegram Bot** — интерактивный бот на aiogram 3.x
- **VK Publisher** — автопубликация в сообщества ВКонтакте
- **Telegram Userbot** — расширенные возможности через Pyrogram
- **Сценарии создания** — пошаговое создание контента через бота

---

## 🗂️ Структура проекта

```
SMM-Simple-Media-Manager/
├── 🧠 brain-api/           # Центральный API сервис
│   ├── database/           # Модели и подключение к БД
│   ├── models/             # SQLAlchemy модели
│   │   ├── Card.py         # Модель карточки контента
│   │   ├── User.py         # Модель пользователя
│   │   ├── Scene.py        # Модель сцены бота
│   │   └── ScheduledTask.py # Отложенные задачи
│   ├── routers/            # API эндпоинты
│   │   ├── card.py         # Управление карточками
│   │   ├── user.py         # Управление пользователями
│   │   ├── ai.py           # AI генерация
│   │   ├── kaiten.py       # Интеграция Kaiten
│   │   └── scene.py        # Сцены бота
│   └── modules/            # Бизнес-логика
│
├── 📅 calendar-api/        # Сервис календаря
│   ├── routers/            # API эндпоинты
│   └── modules/            # Логика Google Calendar
│
├── ⚡ executors/           # Сервис публикации
│   ├── tg/                 # Telegram бот
│   │   ├── handlers/       # Обработчики команд
│   │   ├── scenes/         # Сценарии создания контента
│   │   └── oms/            # One Message System
│   ├── vk/                 # VK публикация
│   └── modules/            # Общие модули
│
├── 🔧 global_modules/      # Общие модули для всех сервисов
│   ├── kaiten_client/      # Клиент Kaiten API
│   ├── classes/            # Общие классы и Enum
│   └── middlewares/        # Middleware компоненты
│
├── 📄 json/                # JSON конфигурации
├── 📝 logs/                # Логи приложения
├── 🔐 sessions/            # Сессии Telegram
└── 📜 scripts/             # Вспомогательные скрипты
```

---

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.11+ (для локальной разработки)
- Токены и ключи для внешних сервисов

### 1. Клонирование репозитория

```bash
git clone https://github.com/Rimuwu/SMM-Simple-Media-Manager.git
cd SMM-Simple-Media-Manager
```

### 2. Настройка переменных окружения

Скопируйте `.env.here` в `.env` и заполните необходимые переменные:

```bash
cp .env.here .env
```

<details>
<summary>📋 Описание переменных окружения</summary>

```env
# ═══════════════════════════════════════════════════
# 🗄️ Database Configuration (PostgreSQL)
# ═══════════════════════════════════════════════════
POSTGRES_DB=smm_db
POSTGRES_USER=smm_user
POSTGRES_PASSWORD=your_secure_password

# ═══════════════════════════════════════════════════
# 🤖 Telegram Bot Configuration
# ═══════════════════════════════════════════════════
TG_BOT_TOKEN=         # Токен от @BotFather
ADMIN_ID=             # Telegram ID администратора

# Pyrogram (для userbot функций)
TP_API_ID=            # API ID от my.telegram.org
TP_API_HASH=          # API Hash от my.telegram.org
TP_PHONE_NUMBER=      # Номер телефона

# ═══════════════════════════════════════════════════
# 📢 VKontakte Configuration
# ═══════════════════════════════════════════════════
VK_GROUP_ID=          # ID сообщества
VK_ACCESS_TOKEN=      # Токен сообщества
VK_USER_TOKEN=        # Токен пользователя (для загрузки фото)

# ═══════════════════════════════════════════════════
# 📅 Google Calendar Configuration
# ═══════════════════════════════════════════════════
GOOGLE_SERVICE_ACCOUNT_JSON=  # JSON Service Account
GOOGLE_CALENDAR_ID=           # ID календаря

# ═══════════════════════════════════════════════════
# 📋 Kaiten Configuration
# ═══════════════════════════════════════════════════
KAITEN_DOMAIN=        # Домен Kaiten
KAITEN_TOKEN=         # API токен Kaiten

# ═══════════════════════════════════════════════════
# ⚙️ General Settings
# ═══════════════════════════════════════════════════
DEBUG=false           # Режим отладки
```

</details>

### 3. Запуск через Docker Compose

```bash
docker-compose up -d
```

После запуска сервисы будут доступны:
- **Brain API**: http://localhost:8000
- **Calendar API**: http://localhost:8001
- **Executors API**: http://localhost:8003

### 4. Проверка работоспособности

```bash
# Проверка Brain API
curl http://localhost:8000/

# Просмотр логов
docker-compose logs -f
```

---

## 🔧 Настройка интеграций

### 📋 Kaiten

1. Получите API токен на [developers.kaiten.ru](https://developers.kaiten.ru)
2. Укажите `KAITEN_DOMAIN` и `KAITEN_TOKEN` в `.env`
3. Синхронизация настроек происходит автоматически при старте

### 📅 Google Calendar

Подробная инструкция в [calendar-api/README.md](./calendar-api/README.md):

1. Создайте Service Account в Google Cloud Console
2. Включите Google Calendar API
3. Создайте и настройте календарь
4. Добавьте JSON ключ в переменную `GOOGLE_SERVICE_ACCOUNT_JSON`

### 💬 Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Укажите токен в `TG_BOT_TOKEN`
3. Для userbot функций: получите API ID/Hash на [my.telegram.org](https://my.telegram.org)

### 📢 VKontakte

1. Создайте сообщество или используйте существующее
2. Получите токен сообщества в настройках API
3. Для загрузки фото: получите токен пользователя через OAuth

---

## 📚 API Документация

После запуска доступна Swagger документация:

- **Brain API**: http://localhost:8000/docs
- **Calendar API**: http://localhost:8001/docs
- **Executors API**: http://localhost:8003/docs

### Основные эндпоинты Brain API

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/card/create` | Создание карточки контента |
| `GET` | `/card/{id}` | Получение карточки |
| `PUT` | `/card/update` | Обновление карточки |
| `GET` | `/user/list` | Список пользователей |
| `POST` | `/ai/send` | AI генерация контента |

---

## 🛠️ Разработка

### Локальный запуск без Docker

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск Brain API
cd brain-api && python main.py

# Запуск Calendar API (в другом терминале)
cd calendar-api && python main.py

# Запуск Executors (в другом терминале)
cd executors && python main.py
```

### Технологический стек

| Компонент | Технология |
|-----------|------------|
| Backend | FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy 2.0 |
| Telegram | aiogram 3.x, Pyrogram |
| VK | vk_api |
| Calendar | Google Calendar API |
| AI | g4f |
| Containerization | Docker, Docker Compose |

---

## 📝 Лицензия

Этот проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).

---

## 👤 Автор

**Rimuwu**

- GitHub: [@Rimuwu](https://github.com/Rimuwu)

---

<div align="center">

**⭐ Если проект оказался полезным, поставьте звёздочку!**

</div>
