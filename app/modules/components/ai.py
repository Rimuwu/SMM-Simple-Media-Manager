import random
import time
import concurrent.futures
import g4f

model = 'gpt-4'

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def send_ai_request(text: str):
    user_agent = random.choice(user_agents)
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Referer': 'https://www.google.com/',
    }
    time.sleep(random.uniform(0.1, 0.5))

    def do_request():
        return g4f.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f'{text}'
                },
            ],
            headers=headers
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(do_request)
        try:
            response = future.result(timeout=30)
        except concurrent.futures.TimeoutError:
            return ''
    return response

def send(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text

    forbidden = [
        "HTTP", "ERR_CHALLENGE", "Blocked by DuckDuckGo", "Bot limit exceeded", "ERR_BN_LIMIT",
        "Misuse detected. Please get in touch, we can   come up with a solution for your use case.",
        "Too Many Requests", "Misuse", "message='Too", "AI-powered", 'more](https://pollinations.ai/redirect/2699274)', "module—no guesswork", '\n\n---\n', 'Telegram bot', '\u0000', 'pollinations.ai'
    ]

    for _ in range(25):
        new_text = str(send_ai_request(text))
        if not new_text:
            print('нет текста')
            continue

        if any(f in new_text for f in forbidden):

            print("Найден запрещённый текст")
            continue

        return new_text
    return text