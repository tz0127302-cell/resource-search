from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from backend.database import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    url = Column(String(1024), nullable=False)
    resource_type = Column(String(50), index=True, default="other")  # netdisk, website, other
    tags = Column(String(500), default="")
    description = Column(Text, default="")
    source = Column(String(255), default="")  # where it was crawled from
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
