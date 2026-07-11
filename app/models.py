from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    links = relationship("Link", back_populates="dono", cascade="all, delete-orphan")

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    url_original = Column(String, nullable=False)
    codigo_curto = Column(String, unique=True, index=True, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    dono = relationship("User", back_populates="links")
    cliques = relationship("Click", back_populates="link", cascade="all, delete-orphan")

class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    device_type = Column(String, nullable=True)  # "desktop" | "mobile" | "tablet"

    link = relationship("Link", back_populates="cliques")
