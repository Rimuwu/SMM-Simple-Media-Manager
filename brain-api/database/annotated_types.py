

from datetime import datetime
from typing import Annotated
from uuid import uuid4, UUID as _UUID
from sqlalchemy import DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Стандартный тип для создания uuid полей
uuidPK = Annotated[_UUID, mapped_column(UUID(as_uuid=True), 
    primary_key=True, default=uuid4)
                   ]

# Старндартный тип для создания поля с временем создания (UTC)
createAT = Annotated[datetime, mapped_column(DateTime,
    server_default=text("TIMEZONE('utc', now())"))
                     ]

# Стандартный тип для создания поля с временем обновления (UTC)
updateAT = Annotated[datetime, mapped_column(DateTime,
    server_default=text("TIMEZONE('utc', now())"),
    onupdate=datetime.utcnow)
                   ]

# Стандартный тип для создания автоинкрементных полей числа
intAutoPK = Annotated[Integer, mapped_column(Integer,
    primary_key=True, autoincrement=True)
                   ]
