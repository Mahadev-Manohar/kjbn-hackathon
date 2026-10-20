from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # reconnect after the host suspends an idle database
    # Auto-prepared statements break behind transaction poolers such as Neon's pooled endpoint.
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=True,
)
