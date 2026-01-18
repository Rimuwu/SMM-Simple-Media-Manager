

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4, UUID as _UUID
from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Функция для получения текущего времени в UTC
def _get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Стандартный тип для создания uuid полей
uuidPK = Annotated[_UUID, mapped_column(UUID(as_uuid=True), 
    primary_key=True, default=uuid4)
                   ]

# Стандартный тип для создания str_pk полей
strPK = Annotated[str, mapped_column(String,
    primary_key=True)
                   ]

# Стандартный тип для создания поля с временем создания (UTC)
createAT = Annotated[datetime, mapped_column(DateTime,
    server_default=text("TIMEZONE('utc', now())"),
    default=_get_utc_now)
                     ]

# Стандартный тип для создания поля с временем обновления (UTC)
updateAT = Annotated[datetime, mapped_column(DateTime,
    server_default=text("TIMEZONE('utc', now())"),
    onupdate=text("TIMEZONE('utc', now())"),
    default=_get_utc_now)
                   ]

# Стандартный тип для создания автоинкрементных полей числа
intAutoPK = Annotated[int, mapped_column(Integer,
    primary_key=True, autoincrement=True)
                   ]
