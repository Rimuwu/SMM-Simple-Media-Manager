import random
import time
from g4f import Client
import concurrent.futures
from g4f.Provider import PollinationsAI

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
proxies = [
    # 'http://KxxvFT:Kg0MSmP7iv@45.147.192.2:6070',
    # 'http://KxxvFT:Kg0MSmP7iv@77.94.1.194:6070',
    # 'http://KxxvFT:Kg0MSmP7iv@77.83.148.232:6070'
]

def send_ai_request(text: str, client: Client) -> str:
    user_agent = random.choice(user_agents)
    proxy = random.choice(proxies) if proxies else None
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
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f'{text}'
                },
            ],
            headers=headers,
            proxy=proxy
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(do_request)
        try:
            response = future.result(timeout=30)
        except concurrent.futures.TimeoutError:
            return ''

    return response.choices[0].message.content

def send(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text

    client = Client(PollinationsAI)
    forbidden = [
        "HTTP", "ERR_CHALLENGE", "Blocked by DuckDuckGo", "Bot limit exceeded", "ERR_BN_LIMIT",
        "Misuse detected. Please get in touch, we can   come up with a solution for your use case.",
        "Too Many Requests", "Misuse", "message='Too", "AI-powered", 'more](https://pollinations.ai/redirect/2699274)', "module—no guesswork", '\n\n---\n', 'Telegram bot', '\u0000', 'pollinations.ai'
    ]

    for _ in range(25):
        new_text = send_ai_request(text, client)
        if not new_text:
            continue

        if any(f in new_text for f in forbidden):
            # Найден запрещённый текст
            continue

        return new_text
    return text

print(
    send('Напиши рецепт пирога в средневековом стиле')
)