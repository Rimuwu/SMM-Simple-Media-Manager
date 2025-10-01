from webhooks import KaitenWebhookServer
import asyncio

server = KaitenWebhookServer(port=8888)

async def main(): 
    import handlers

    server.run()

if __name__ == "__main__":
    asyncio.run(main())