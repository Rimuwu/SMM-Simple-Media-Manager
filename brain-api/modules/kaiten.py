from global_modules.kaiten_client import KaitenClient
from os import getenv

TOKEN = getenv("KAITEN_TOKEN", '')
DOMAIN = getenv("KAITEN_DOMAIN", "kaiten.io")
kaiten = KaitenClient(token=TOKEN, domain=DOMAIN)