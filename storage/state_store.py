from __future__ import annotations

from datetime import datetime
from typing import Optional, List, cast

from sqlalchemy import create_engine, String, Float, Text, DateTime, Boolean, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column


Base = declarative_base()


class MessageEvent(Base):
    __tablename__ = "message_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SignalState(Base):
    __tablename__ = "signal_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_message_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), default="XAUUSD")
    side: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    lifecycle: Mapped[str] = mapped_column(String(32), default="PARSED")
    signal_group_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    entry_role: Mapped[str] = mapped_column(String(32), default="primary")
    closed_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    continuation_add_count: Mapped[int] = mapped_column(Integer, default=0)
    sl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tp1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tp2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TicketMap(Base):
    __tablename__ = "ticket_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    mt5_ticket: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    open_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppState(Base):
    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StateStore:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False, future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)

    def add_message_event(self, chat_id: str, message_id: int, action_type: str, raw_text: str) -> int:
        with self.Session() as s:
            evt = MessageEvent(
                chat_id=chat_id,
                message_id=message_id,
                action_type=action_type,
                raw_text=raw_text,
                processed=False,
            )
            s.add(evt)
            s.commit()
            s.refresh(evt)
            return cast(int, evt.id)

    def is_message_processed(self, chat_id: str, message_id: int) -> bool:
        with self.Session() as s:
            row = (
                s.query(MessageEvent)
                .filter(
                    MessageEvent.chat_id == chat_id,
                    MessageEvent.message_id == message_id,
                    MessageEvent.processed.is_(True),
                )
                .first()
            )
            return row is not None

    def mark_message_processed(self, chat_id: str, message_id: int) -> None:
        with self.Session() as s:
            row = (
                s.query(MessageEvent)
                .filter(
                    MessageEvent.chat_id == chat_id,
                    MessageEvent.message_id == message_id,
                )
                .order_by(MessageEvent.id.desc())
                .first()
            )
            if row:
                row.processed = True
                s.commit()

    def create_signal_state(
        self,
        chat_id: str,
        source_message_id: int,
        symbol: str,
        side: Optional[str],
        lifecycle: str,
        sl: Optional[float],
        tp1: Optional[float],
        tp2: Optional[float],
        signal_group_id: Optional[str] = None,
        entry_role: str = "primary",
        closed_reason: Optional[str] = None,
    ) -> int:
        with self.Session() as s:
            obj = SignalState(
                chat_id=chat_id,
                source_message_id=source_message_id,
                symbol=symbol,
                side=side,
                lifecycle=lifecycle,
                signal_group_id=signal_group_id,
                entry_role=entry_role,
                closed_reason=closed_reason,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
            )
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return cast(int, obj.id)

    def update_signal_lifecycle(self, signal_id: int, lifecycle: str) -> None:
        with self.Session() as s:
            obj = s.query(SignalState).filter(SignalState.id == signal_id).first()
            if obj:
                obj.lifecycle = lifecycle
                obj.updated_at = datetime.utcnow()
                s.commit()

    def set_signal_closed_reason(self, signal_id: int, reason: str) -> None:
        with self.Session() as s:
            obj = s.query(SignalState).filter(SignalState.id == signal_id).first()
            if obj:
                obj.closed_reason = reason
                obj.updated_at = datetime.utcnow()
                s.commit()

    def increment_continuation_add_count(self, signal_id: int) -> None:
        with self.Session() as s:
            obj = s.query(SignalState).filter(SignalState.id == signal_id).first()
            if obj:
                obj.continuation_add_count = int(obj.continuation_add_count or 0) + 1
                obj.updated_at = datetime.utcnow()
                s.commit()

    def get_latest_open_signal(self, symbol: str = "XAUUSD") -> Optional[SignalState]:
        with self.Session() as s:
            row = (
                s.query(SignalState)
                .filter(
                    SignalState.symbol == symbol,
                    SignalState.lifecycle.in_(["OPEN", "PARTIAL_CLOSED", "PENDING"]),
                )
                .order_by(SignalState.id.desc())
                .first()
            )
            return cast(Optional[SignalState], row)

    def get_latest_open_signal_by_group(self, signal_group_id: str) -> Optional[SignalState]:
        with self.Session() as s:
            row = (
                s.query(SignalState)
                .filter(
                    SignalState.signal_group_id == signal_group_id,
                    SignalState.lifecycle.in_(["OPEN", "PARTIAL_CLOSED", "PENDING"]),
                )
                .order_by(SignalState.id.desc())
                .first()
            )
            return cast(Optional[SignalState], row)

    def get_group_active_signals(self, signal_group_id: str) -> List[SignalState]:
        with self.Session() as s:
            rows = (
                s.query(SignalState)
                .filter(
                    SignalState.signal_group_id == signal_group_id,
                    SignalState.lifecycle.in_(["OPEN", "PARTIAL_CLOSED", "PENDING"]),
                )
                .order_by(SignalState.id.asc())
                .all()
            )
            return cast(List[SignalState], rows)

    def add_ticket(
        self,
        signal_id: int,
        mt5_ticket: int,
        side: str,
        volume: float,
        open_price: float,
        status: str = "OPEN",
    ) -> None:
        with self.Session() as s:
            t = TicketMap(
                signal_id=signal_id,
                mt5_ticket=mt5_ticket,
                side=side,
                volume=volume,
                open_price=open_price,
                status=status,
            )
            s.add(t)
            s.commit()

    def get_open_tickets_for_signal(self, signal_id: int) -> List[TicketMap]:
        with self.Session() as s:
            rows = (
                s.query(TicketMap)
                .filter(
                    TicketMap.signal_id == signal_id,
                    TicketMap.status.in_(["OPEN", "PARTIAL_CLOSED", "PENDING"]),
                )
                .all()
            )
            return cast(List[TicketMap], rows)

    def update_ticket_status(self, mt5_ticket: int, status: str, volume: Optional[float] = None) -> None:
        with self.Session() as s:
            row = s.query(TicketMap).filter(TicketMap.mt5_ticket == mt5_ticket).first()
            if row:
                row.status = status
                if volume is not None:
                    row.volume = volume
                row.updated_at = datetime.utcnow()
                s.commit()

    def set_flag(self, key: str, value: str) -> None:
        with self.Session() as s:
            row = s.query(AppState).filter(AppState.key == key).first()
            if row:
                row.value = value
                row.updated_at = datetime.utcnow()
            else:
                row = AppState(key=key, value=value)
                s.add(row)
            s.commit()

    def get_flag(self, key: str, default: str = "") -> str:
        with self.Session() as s:
            row = s.query(AppState).filter(AppState.key == key).first()
            return cast(str, row.value) if row else default
