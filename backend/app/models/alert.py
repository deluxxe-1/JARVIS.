import uuid
from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    asset_type: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(50))
    condition: Mapped[str] = mapped_column(String(50))
    threshold: Mapped[float] = mapped_column(Float)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="alerts")
