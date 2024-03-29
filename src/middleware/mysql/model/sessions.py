from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from .base import BaseSchema
from .llms import LLMSchema
from .users import UserSchema


class SessionSchema(BaseSchema):

    __tablename__ = "sessions"
    session_id: int = Column(Integer, primary_key=True, autoincrement=True)
    create_at: datetime = Column(DateTime, default=datetime.now)
    update_at: datetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    delete_at: datetime = Column(DateTime, nullable=True)
    llm_id: int = Column(Integer, ForeignKey(LLMSchema.llm_id, ondelete="CASCADE"), nullable=True)
    uid: int = Column(Integer, ForeignKey(UserSchema.uid, ondelete="CASCADE"), nullable=False)
