from kaiten_client import KaitenClient
from os import getenv
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = getenv('KAITEN_TOKEN')
DOMAIN = getenv('KAITEN_DOMAIN')

async def main(): 
    
    async with KaitenClient(TOKEN, DOMAIN) as client:

        # space = await client.get_spaces()
        # board = await client.get_boards(space[0].id)
        # column = await client.get_columns(board[0].id)
        # card = await client.create_card('werwer', 
        #                                 column_id=column[0].id,
        #                                 board_id=board[0].id)
        
        card = await client.get_card(55371436)
        print(await card.get_members())
        
        # await card.add_member(908324)


asyncio.run(main())