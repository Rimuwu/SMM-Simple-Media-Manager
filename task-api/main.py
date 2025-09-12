
import asyncio
import os
from kaiten_client import KaitenClient
from pprint import pprint

KAITEN_DOMAIN=os.getenv("KAITEN_DOMAIN")
KAITEN_TOKEN=os.getenv("KAITEN_TOKEN")

async def main():
    """Демонстрация основных возможностей клиента."""
    print("🚀 Запуск демонстрации Kaiten API клиента")

    async with KaitenClient(KAITEN_TOKEN, KAITEN_DOMAIN) as client:
        try:

            space_id = 656020
            board_id = 1489554

            column1_id = 5167704
            column2_id = 5167705
            column3_id = 5167706
            
            # board = await client.get_board(
            #     board_id
            # )
            
            # card = await board.create_card(
            #     title="Я перемещаюсь",
            #     column_id=column1_id
            # )

            # await card.move_to_column(column2_id)
            
            # await asyncio.sleep(5)
            # await card.move_to_column(column3_id)

            # await card.add_comment(
            #     "12345666"
            # )
            
            # await client.
            
            card_id = 55346897
            
            card = await client.get_card(
                card_id
            )
            files = await card.get_files()
            for file in files:
                pprint(file.url)

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())