Слой взаимодействия с календарём.


# Google Calendar API Integration

Модуль для работы с Google Calendar API в рамках SMM-Simple-Media-Manager.

## Настройка

### 1. Создание Service Account в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Calendar API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Calendar API" и включите его
4. Создайте Service Account:
   - Перейдите в "APIs & Services" > "Credentials"
   - Нажмите "Create Credentials" > "Service Account"
   - Заполните данные и создайте аккаунт
5. Скачайте JSON ключ:
   - Откройте созданный Service Account
   - Перейдите во вкладку "Keys"
   - Нажмите "Add Key" > "Create new key" > "JSON"
   - Сохраните файл с ключом

### 2. Создание и настройка календаря

1. Откройте [Google Calendar](https://calendar.google.com/)
2. Создайте новый календарь:
   - В левой панели нажмите "+" рядом с "Other calendars"
   - Выберите "Create new calendar"
   - Заполните название и описание
   - Нажмите "Create calendar"
3. Получите ID календаря:
   - Откройте настройки созданного календаря
   - В разделе "Integrate calendar" найдите "Calendar ID"
   - Скопируйте ID (обычно заканчивается на @group.calendar.google.com)
4. Предоставьте доступ Service Account:
   - В настройках календаря перейдите в "Share with specific people"
   - Добавьте email вашего Service Account (из JSON файла, поле "client_email")
   - Установите права "Make changes to events"

### 3. Настройка переменных окружения

Создайте или обновите файл `.env` в корне проекта:

```env
# Google Calendar API Configuration
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", "project_id": "your-project-id", "private_key_id": "...", "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n", "client_email": "your-service-account@your-project.iam.gserviceaccount.com", "client_id": "...", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_x509_cert_url": "..."}

GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
```

**Важно:** Скопируйте весь JSON из скачанного файла в одну строку для переменной `GOOGLE_SERVICE_ACCOUNT_JSON`.