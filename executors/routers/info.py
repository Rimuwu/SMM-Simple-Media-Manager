from fastapi import APIRouter, Request
from modules.executors_manager import manager
from modules.constants import CLIENTS
from global_modules.limiter import limiter

router = APIRouter(prefix="/info", tags=["info"])

@router.get("/available-executors")
@limiter.limit("2/second")
async def available_executors(request: Request):
    return {"executors": list(manager.get_available())}

@router.get("/executors-status")
@limiter.limit("2/second")
async def executors_status(request: Request):

    status = {}
    for name in manager.get_available():
        executor = manager.get(name)
        status[name] = {
            "is_running": executor.is_running,
            "type": executor.executor_name
        }

    return {"status": status}

@router.get("/clients")
@limiter.limit("2/second")
async def clients_info(request: Request):
    return CLIENTS