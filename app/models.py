from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    url_original = Column(String, nullable=False)
    codigo_curto = Column(String, unique=True, index=True, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
