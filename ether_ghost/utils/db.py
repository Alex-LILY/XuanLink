"""数据库管理，管理session info等信息"""

import datetime
import typing as t
from dataclasses import dataclass
from uuid import uuid4, UUID
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType  # type: ignore
from ..session_types import SessionInfo, SessionConnectorInfo

from .const import SETTINGS_VERSION, STORE_URL

engine = sa.create_engine(STORE_URL)
OrmSession = sa.orm.sessionmaker(bind=engine)
orm_session = OrmSession()
Base = sa.orm.declarative_base()


class SessionInfoModel(Base):  # type: ignore
    """sqlalchemy的Model，用于在数据库中保存session info"""

    __tablename__ = "session_info"
    record_id = sa.Column(sa.Integer, primary_key=True)
    session_type = sa.Column(sa.String)  # type: ignore
    session_id = sa.Column(UUIDType(binary=False), default=uuid4)  # type: ignore
    name = sa.Column(sa.String)
    note = sa.Column(sa.String)
    location = sa.Column(sa.String)
    connection = sa.Column(sa.JSON)

    # 缓存字段，用于列表页展示
    tags = sa.Column(sa.JSON, default=list)
    os = sa.Column(sa.String, default="")
    internal_ip = sa.Column(sa.String, default="")
    external_ip = sa.Column(sa.String, default="")
    hostname = sa.Column(sa.String, default="")
    username = sa.Column(sa.String, default="")
    last_connected_at = sa.Column(sa.DateTime, nullable=True)
    status = sa.Column(sa.String, default="unknown")


class SessionConnectorModel(Base):  # type: ignore
    """sqlalchemy的Model，用于在数据库中保存session connector"""

    __tablename__ = "session_connector"
    record_id = sa.Column(sa.Integer, primary_key=True)
    connector_type = sa.Column(sa.String)  # type: ignore
    connector_id = sa.Column(UUIDType(binary=False), default=uuid4)  # type: ignore
    name = sa.Column(sa.String)
    note = sa.Column(sa.String)
    connection = sa.Column(sa.JSON)
    autostart = sa.Column(sa.Boolean)  # run on program startup


class SettingsModel(Base):  # type: ignore
    """sqlalchemy的Model，用于在数据库中保存设置"""

    __tablename__ = "settings"
    record_id = sa.Column(sa.Integer, primary_key=True)
    version = sa.Column(sa.String)
    settings = sa.Column(sa.JSON)


class HttpProxyModel(Base):  # type: ignore
    """sqlalchemy的Model，用于在数据库中保存HTTP代理列表"""

    __tablename__ = "http_proxy"
    record_id = sa.Column(sa.Integer, primary_key=True)
    proxy_id = sa.Column(UUIDType(binary=False), default=uuid4)  # type: ignore
    url = sa.Column(sa.String)
    latency_ms = sa.Column(sa.Float, nullable=True)
    last_checked_at = sa.Column(sa.DateTime, nullable=True)
    status = sa.Column(sa.String, default="unknown")
    note = sa.Column(sa.String, default="")


class AuthConfigModel(Base):  # type: ignore
    """sqlalchemy的Model，用于在数据库中保存认证配置"""

    __tablename__ = "auth_config"
    id = sa.Column(sa.Integer, primary_key=True)
    password_hash = sa.Column(sa.String)
    salt = sa.Column(sa.String)
    needs_password_change = sa.Column(sa.Boolean, default=True)
    otp_enabled = sa.Column(sa.Boolean, default=False)
    otp_secret = sa.Column(sa.String, nullable=True)


@dataclass
class SessionInfoModelTypeHint:
    """SessionInfoModel的type hint
    解决pylint不能正确识别SQLAlchemy属性类型的问题"""

    record_id: int
    session_type: str
    session_id: UUID
    name: str
    note: str
    location: str
    connection: t.Dict[t.Any, t.Any]
    tags: t.List[str]
    os: str
    internal_ip: str
    external_ip: str
    hostname: str
    username: str
    last_connected_at: t.Optional[datetime.datetime]
    status: str


@dataclass
class SessionConnectorModelTypeHint:
    """SessionConnectorModel的type hint
    解决pylint不能正确识别SQLAlchemy属性类型的问题"""

    record_id: int
    connector_type: str
    connector_id: UUID
    name: str
    note: str
    connection: t.Dict[t.Any, t.Any]
    autostart: bool


Base.metadata.create_all(engine)


# 数据库迁移：为旧版数据库自动添加新增列
_NEW_SESSION_INFO_COLUMNS = [
    ("tags", "JSON", "'[]'"),
    ("os", "VARCHAR", "''"),
    ("internal_ip", "VARCHAR", "''"),
    ("external_ip", "VARCHAR", "''"),
    ("hostname", "VARCHAR", "''"),
    ("username", "VARCHAR", "''"),
    ("last_connected_at", "DATETIME", "NULL"),
    ("status", "VARCHAR", "'unknown'"),
]


def migrate_db():
    """检测 session_info 表是否缺少新增列，若缺少则使用 ALTER TABLE 添加"""
    inspector = sa.inspect(engine)
    if not inspector.has_table("session_info"):
        return
    existing_columns = {
        col["name"] for col in inspector.get_columns("session_info")
    }
    with engine.begin() as conn:
        for col_name, col_type, default_value in _NEW_SESSION_INFO_COLUMNS:
            if col_name not in existing_columns:
                conn.execute(
                    sa.text(
                        f"ALTER TABLE session_info ADD COLUMN {col_name} {col_type} DEFAULT {default_value}"
                    )
                )


migrate_db()


# 转换函数


def model_to_info(model: SessionInfoModelTypeHint) -> SessionInfo:
    """将SessionInfoModel(SQLAlchemy的对象)转换成SessionInfo(Pydantic的对象)"""
    connection = {**model.connection}
    result = SessionInfo(
        session_type=model.session_type,
        name=model.name,
        connection=connection,
        session_id=model.session_id,
        note=model.note,
        location=model.location,
        tags=model.tags or [],
        os=model.os or "",
        internal_ip=model.internal_ip or "",
        external_ip=model.external_ip or "",
        hostname=model.hostname or "",
        username=model.username or "",
        last_connected_at=model.last_connected_at,
        status=model.status or "unknown",
    )
    return result


def info_to_model(info: SessionInfo) -> SessionInfoModel:
    """将SessionInfo(Pydantic的对象)转换成SessionInfoModel(SQLAlchemy的对象)"""
    info_dict = info.model_dump()
    return SessionInfoModel(**info_dict)


def model_to_connector(model: SessionConnectorModelTypeHint) -> SessionConnectorInfo:
    """将SessionConnectorModel(SQLAlchemy的对象)转换成SessionConnector(Pydantic的对象)"""
    connection = {**model.connection}
    result = SessionConnectorInfo(
        connector_type=model.connector_type,
        name=model.name,
        connection=connection,
        connector_id=model.connector_id,
        note=model.note,
        autostart=model.autostart,
    )
    return result


def connector_to_model(connector: dict) -> SessionConnectorModel:
    """将dict转换成SessionConnectorModel(SQLAlchemy的对象)"""
    return SessionConnectorModel(**connector)


# 操作数据库


# TODO: list session by created time
def list_sessions() -> t.List[SessionInfo]:
    """列出数据库中所有的session"""
    return [model_to_info(model) for model in orm_session.query(SessionInfoModel).all()]


def add_session_info(info: SessionInfo):
    """添加一个session"""
    orm_session.add(info_to_model(info))
    orm_session.commit()


def update_session_info_cache(session_id: t.Union[str, UUID], data: t.Dict[str, t.Any]) -> bool:
    """更新 session 的缓存字段（由探测/心跳任务调用）"""
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    model = (
        orm_session.query(SessionInfoModel)
        .filter(SessionInfoModel.session_id == session_id)
        .first()
    )
    if model is None:
        return False
    allowed_fields = {
        "tags", "os", "internal_ip", "external_ip", "hostname",
        "username", "last_connected_at", "status",
    }
    for key, value in data.items():
        if key in allowed_fields and hasattr(model, key):
            setattr(model, key, value)
    orm_session.commit()
    return True


def add_session_infos(infos: t.List[SessionInfo]):
    """批量添加多个session"""
    models = [info_to_model(info) for info in infos]
    orm_session.add_all(models)
    orm_session.commit()


def get_session_info_by_id(
    session_id: t.Union[str, UUID],
) -> t.Union[None, SessionInfo]:
    """根据ID查询session，以sessioninfo的形式输出"""
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    model = (
        orm_session.query(SessionInfoModel)
        .filter(SessionInfoModel.session_id == session_id)
        .first()
    )
    if model is None:
        return None
    return model_to_info(model)


def delete_session_info_by_id(
    session_id: t.Union[str, UUID], ignore_unexist=False
) -> bool:
    """根据ID查询session，并将对应的session info转换成session实例"""
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    model = (
        orm_session.query(SessionInfoModel)
        .filter(SessionInfoModel.session_id == session_id)
        .first()
    )
    if model is None:
        return ignore_unexist  # True if ignore_unexist else False
    orm_session.delete(model)
    orm_session.commit()
    return True


def get_session_by_session_type(session_type: str) -> t.List[SessionInfo]:
    """根据session_type查询所有session"""
    models = (
        orm_session.query(SessionInfoModel)
        .filter(SessionInfoModel.session_type == session_type)
        .all()
    )
    return [model_to_info(model) for model in models]


def delete_session_by_session_type(session_type: str) -> int:
    """根据session_type删除所有session，返回删除的数量"""
    models = (
        orm_session.query(SessionInfoModel)
        .filter(SessionInfoModel.session_type == session_type)
        .all()
    )
    count = len(models)
    for model in models:
        orm_session.delete(model)
    if count > 0:
        orm_session.commit()
    return count


def delete_all_sessions() -> int:
    """删除所有session，返回删除的数量"""
    count = orm_session.query(SessionInfoModel).delete()
    orm_session.commit()
    return count


def list_session_connectors() -> t.List[SessionConnectorInfo]:
    """列出数据库中所有的session connector"""
    return [
        model_to_connector(model)
        for model in orm_session.query(SessionConnectorModel).all()
    ]


def add_session_connector(connector: SessionConnectorInfo):
    """添加一个session connector"""
    orm_session.add(connector_to_model(connector.model_dump()))
    orm_session.commit()


def add_session_connectors(connectors: t.List[SessionConnectorInfo]):
    """批量添加多个session connector"""
    models = [connector_to_model(connector.model_dump()) for connector in connectors]
    orm_session.add_all(models)
    orm_session.commit()

def get_session_connector_all() -> t.List[SessionConnectorInfo]:
    """获取所有session connector"""
    models = orm_session.query(SessionConnectorModel).all()
    return [model_to_connector(model) for model in models]

def get_session_connector_by_connector_id(
    connector_id: t.Union[str, UUID],
) -> t.Union[None, SessionConnectorInfo]:
    """根据connector_id查询session connector"""
    if isinstance(connector_id, str):
        connector_id = UUID(connector_id)
    model = (
        orm_session.query(SessionConnectorModel)
        .filter(SessionConnectorModel.connector_id == connector_id)
        .first()
    )
    if model is None:
        return None
    return model_to_connector(model)


def update_session_connector(connector: SessionConnectorInfo) -> bool:
    """根据connector_id更新session connector"""
    connector_id = connector.connector_id
    if isinstance(connector_id, str):
        connector_id = UUID(connector_id)
    model = (
        orm_session.query(SessionConnectorModel)
        .filter(SessionConnectorModel.connector_id == connector_id)
        .first()
    )
    if model is None:
        return False
    data = connector.model_dump()
    for key, value in data.items():
        if hasattr(model, key):
            setattr(model, key, value)
    orm_session.commit()
    return True


def delete_session_connector_by_connector_id(
    connector_id: t.Union[str, UUID], ignore_unexist=False
) -> bool:
    """根据connector_id删除session connector"""
    if isinstance(connector_id, str):
        connector_id = UUID(connector_id)
    model = (
        orm_session.query(SessionConnectorModel)
        .filter(SessionConnectorModel.connector_id == connector_id)
        .first()
    )
    if model is None:
        return ignore_unexist
    orm_session.delete(model)
    orm_session.commit()
    return True


def get_settings() -> dict:
    """查询当前设置"""
    model = orm_session.query(SettingsModel).first()
    if model is None:
        return {}
    assert model.version == SETTINGS_VERSION, (
        "The version of the settings is not supported!"
        + " Did you load a newer settings?"
    )
    return model.settings


def set_settings(settings: dict):
    model = orm_session.query(SettingsModel).first()
    if model:
        orm_session.delete(model)
    orm_session.add(SettingsModel(version=SETTINGS_VERSION, settings=settings))
    orm_session.commit()


def ensure_settings():
    """保证当前设置存在，如果不存在设置则将写入默认设置"""
    default_settings = {"theme": "tool", "proxy": ""}
    if not get_settings():
        set_settings(default_settings)


def _proxy_protocol(url: str) -> str:
    """从代理URL中提取协议"""
    if "://" in url:
        return url.split("://", 1)[0]
    return "unknown"


def list_http_proxies() -> t.List[dict]:
    """列出所有HTTP代理"""
    models = orm_session.query(HttpProxyModel).all()
    return [
        {
            "proxy_id": str(model.proxy_id),
            "url": model.url,
            "protocol": _proxy_protocol(model.url),
            "latency_ms": model.latency_ms,
            "last_checked_at": (
                model.last_checked_at.isoformat() if model.last_checked_at else None
            ),
            "status": model.status,
            "note": model.note,
        }
        for model in models
    ]


def add_http_proxy(url: str, note: str = "") -> dict:
    """添加单个HTTP代理"""
    model = HttpProxyModel(url=url, note=note)
    orm_session.add(model)
    orm_session.commit()
    return {
        "proxy_id": str(model.proxy_id),
        "url": model.url,
        "protocol": _proxy_protocol(model.url),
        "latency_ms": model.latency_ms,
        "last_checked_at": None,
        "status": model.status,
        "note": model.note,
    }


def add_http_proxies(urls: t.List[str]) -> t.List[dict]:
    """批量添加HTTP代理"""
    models = [HttpProxyModel(url=url) for url in urls]
    orm_session.add_all(models)
    orm_session.commit()
    return [
        {
            "proxy_id": str(model.proxy_id),
            "url": model.url,
            "protocol": _proxy_protocol(model.url),
            "latency_ms": model.latency_ms,
            "last_checked_at": None,
            "status": model.status,
            "note": model.note,
        }
        for model in models
    ]


def get_http_proxy_by_id(proxy_id: t.Union[str, UUID]) -> t.Union[None, HttpProxyModel]:
    """根据ID查询HTTP代理Model"""
    if isinstance(proxy_id, str):
        proxy_id = UUID(proxy_id)
    return (
        orm_session.query(HttpProxyModel)
        .filter(HttpProxyModel.proxy_id == proxy_id)
        .first()
    )


def update_http_proxy_status(
    proxy_id: t.Union[str, UUID], latency_ms: t.Optional[float], status: str
) -> bool:
    """更新HTTP代理测速状态"""
    model = get_http_proxy_by_id(proxy_id)
    if model is None:
        return False
    model.latency_ms = latency_ms
    model.last_checked_at = datetime.datetime.now()
    model.status = status
    orm_session.commit()
    return True


def delete_http_proxy_by_id(proxy_id: t.Union[str, UUID]) -> bool:
    """根据ID删除HTTP代理"""
    model = get_http_proxy_by_id(proxy_id)
    if model is None:
        return False
    orm_session.delete(model)
    orm_session.commit()
    return True


def get_auth_config():
    model = orm_session.query(AuthConfigModel).first()
    if model is None:
        return None
    return {
        "password_hash": model.password_hash,
        "salt": model.salt,
        "needs_password_change": model.needs_password_change,
        "otp_enabled": model.otp_enabled,
        "otp_secret": model.otp_secret,
    }


def set_auth_config(password_hash, salt, needs_password_change, otp_enabled, otp_secret):
    model = orm_session.query(AuthConfigModel).first()
    if model:
        model.password_hash = password_hash
        model.salt = salt
        model.needs_password_change = needs_password_change
        model.otp_enabled = otp_enabled
        model.otp_secret = otp_secret
    else:
        orm_session.add(AuthConfigModel(
            password_hash=password_hash,
            salt=salt,
            needs_password_change=needs_password_change,
            otp_enabled=otp_enabled,
            otp_secret=otp_secret,
        ))
    orm_session.commit()


def ensure_auth_config():
    if get_auth_config() is not None:
        return
    import hashlib, secrets as sec
    salt = sec.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", b"admin123", salt.encode(), 100000).hex()
    set_auth_config(
        password_hash=pw_hash,
        salt=salt,
        needs_password_change=True,
        otp_enabled=False,
        otp_secret=None,
    )
