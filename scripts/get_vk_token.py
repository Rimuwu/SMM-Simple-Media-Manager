"""
Скрипт для получения VK User Token
Запусти: python scripts/get_vk_token.py
"""

import vk_api


def auth_handler():
    """Обработчик двухфакторной аутентификации"""
    code = input("Введите код из SMS или приложения-аутентификатора: ")
    remember_device = True
    return code, remember_device


def captcha_handler(captcha):
    """Обработчик капчи"""
    print(f"Капча: {captcha.get_url()}")
    key = input("Введите код с картинки: ")
    return captcha.try_again(key)


def main():
    print("=" * 50)
    print("Получение VK User Token для загрузки фото")
    print("=" * 50)
    print()
    
    # Ввод данных
    login = input("Введите логин VK (телефон или email): ")
    password = input("Введите пароль: ")
    
    # ID твоего приложения
    app_id = 54386242
    
    # Права доступа
    scope = 'photos,wall,groups,offline'
    
    print()
    print("Авторизация...")
    
    try:
        vk_session = vk_api.VkApi(
            login=login,
            password=password,
            app_id=app_id,
            scope=scope,
            auth_handler=auth_handler,
            captcha_handler=captcha_handler
        )
        
        vk_session.auth(token_only=True)
        
        token = vk_session.token['access_token']
        
        print()
        print("=" * 50)
        print("УСПЕХ! Твой VK User Token:")
        print("=" * 50)
        print()
        print(token)
        print()
        print("=" * 50)
        print()
        print("Добавь его в .env файл:")
        print(f"VK_USER_TOKEN={token}")
        print()
        print("Или в docker-compose.yml в секцию environment:")
        print(f"  - VK_USER_TOKEN={token}")
        print()
        
        # Сохраняем в файл
        with open("scripts/vk_user_token.txt", "w") as f:
            f.write(f"VK_USER_TOKEN={token}\n")
        print("Токен также сохранён в scripts/vk_user_token.txt")
        
    except vk_api.AuthError as e:
        print(f"Ошибка авторизации: {e}")
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
