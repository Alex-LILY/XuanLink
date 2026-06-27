from uuid import UUID, uuid4
import datetime
import typing as t
from pydantic import BaseModel, Field


class SessionInfo(BaseModel):
    """session的基本信息"""

    session_type: str
    name: str
    connection: t.Dict[str, t.Any]
    session_id: UUID = Field(default_factory=uuid4)
    note: str = ""
    location: str = ""

    # 缓存字段：由探测/心跳任务写入，用于列表页展示
    tags: t.List[str] = Field(default_factory=list)
    os: str = ""
    internal_ip: str = ""
    external_ip: str = ""
    hostname: str = ""
    username: str = ""
    last_connected_at: t.Optional[datetime.datetime] = None
    status: str = "unknown"  # online / offline / unknown

    class Config:
        from_attributes = True


class SessionConnectorInfo(BaseModel):
    """Session connector 的 Pydantic model"""

    connector_type: str
    connector_id: UUID
    name: str
    note: str
    connection: t.Dict[t.Any, t.Any]
    autostart: bool

    class Config:
        from_attributes = True
