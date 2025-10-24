from global_modules.api_client import APIClient

executors_api = APIClient('http://executors:8003')
calendar_api = APIClient('http://calendar-api:8001')