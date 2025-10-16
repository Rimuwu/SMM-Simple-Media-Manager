from global_modules.kaiten_client import KaitenClient
from os import getenv
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = getenv('KAITEN_TOKEN')
DOMAIN = getenv('KAITEN_DOMAIN')

def main(): 
    pass


# asyncio.run(main())
main()

