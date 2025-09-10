import aiohttp

class APIClient:

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def get(self, endpoint: str, 
                  params: dict = None):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}{endpoint}", params=params) as response:
                return await response.json(), response.status

    async def post(self, endpoint: str, data: dict = None):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                return await response.json(), response.status