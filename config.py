from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


load_dotenv()


class Settings(BaseModel):
    tg_api_id: int = Field(default_factory=lambda: int(os.getenv("TG_API_ID", "0")))
    tg_api_hash: str = Field(default_factory=lambda: os.getenv("TG_API_HASH", ""))
    tg_session_name: str = Field(default_factory=lambda: os.getenv("TG_SESSION_NAME", "tg_mt5_session"))
    tg_allowed_chat: str = Field(default_factory=lambda: os.getenv("TG_ALLOWED_CHAT", ""))

    mt5_login: int = Field(default_factory=lambda: int(os.getenv("MT5_LOGIN", "0")))
    mt5_password: str = Field(default_factory=lambda: os.getenv("MT5_PASSWORD", ""))
    mt5_server: str = Field(default_factory=lambda: os.getenv("MT5_SERVER", ""))
    mt5_path: str = Field(default_factory=lambda: os.getenv("MT5_PATH", ""))
    mt5_symbol: str = Field(default_factory=lambda: os.getenv("MT5_SYMBOL", "auto"))
    mt5_magic: int = Field(default_factory=lambda: int(os.getenv("MT5_MAGIC", "260617")))

    risk_mode: str = Field(default_factory=lambda: os.getenv("RISK_MODE", "percent"))
    risk_percent: float = Field(default_factory=lambda: float(os.getenv("RISK_PERCENT", "1.0")))
    fixed_lot: float = Field(default_factory=lambda: float(os.getenv("FIXED_LOT", "0.02")))

    max_concurrent_signals: int = Field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_SIGNALS", "5")))
    default_soft_partial_percent: float = Field(default_factory=lambda: float(os.getenv("DEFAULT_SOFT_PARTIAL_PERCENT", "25")))
    tp1_close_percent: float = Field(default_factory=lambda: float(os.getenv("TP1_CLOSE_PERCENT", "50")))
    tp2_close_percent: float = Field(default_factory=lambda: float(os.getenv("TP2_CLOSE_PERCENT", "100")))
    be_after_tp1: bool = Field(default_factory=lambda: os.getenv("BE_AFTER_TP1", "true").lower() == "true")
    be_buffer_points: int = Field(default_factory=lambda: int(os.getenv("BE_BUFFER_POINTS", "20")))
    be_profit_lock_points: int = Field(default_factory=lambda: int(os.getenv("BE_PROFIT_LOCK_POINTS", "30")))
    enable_sl_buffer: bool = Field(default_factory=lambda: os.getenv("ENABLE_SL_BUFFER", "true").lower() == "true")
    sl_buffer_pips: float = Field(default_factory=lambda: float(os.getenv("SL_BUFFER_PIPS", "5")))
    zone_second_entry_enabled: bool = Field(default_factory=lambda: os.getenv("ZONE_SECOND_ENTRY_ENABLED", "true").lower() == "true")
    zone_best_plus_pips_close_worst: float = Field(default_factory=lambda: float(os.getenv("ZONE_BEST_PLUS_PIPS_CLOSE_WORST", "30")))
    zone_entry_policy_enabled: bool = Field(default_factory=lambda: os.getenv("ZONE_ENTRY_POLICY_ENABLED", "true").lower() == "true")
    zone_entry_wait_outside_enabled: bool = Field(default_factory=lambda: os.getenv("ZONE_ENTRY_WAIT_OUTSIDE_ENABLED", "true").lower() == "true")
    zone_entry_chase_buffer_pips: float = Field(default_factory=lambda: float(os.getenv("ZONE_ENTRY_CHASE_BUFFER_PIPS", "0")))
    trailing_enabled: bool = Field(default_factory=lambda: os.getenv("TRAILING_ENABLED", "false").lower() == "true")
    trailing_trigger_to_tp2_percent: float = Field(default_factory=lambda: float(os.getenv("TRAILING_TRIGGER_TO_TP2_PERCENT", "80")))
    trailing_step_points: int = Field(default_factory=lambda: int(os.getenv("TRAILING_STEP_POINTS", "20")))
    proactive_partials_enabled: bool = Field(default_factory=lambda: os.getenv("PROACTIVE_PARTIALS_ENABLED", "true").lower() == "true")
    proactive_partial_first_percent: float = Field(default_factory=lambda: float(os.getenv("PROACTIVE_PARTIAL_FIRST_PERCENT", "15")))
    proactive_partial_second_percent: float = Field(default_factory=lambda: float(os.getenv("PROACTIVE_PARTIAL_SECOND_PERCENT", "20")))
    proactive_partial_near_tp_pips: int = Field(default_factory=lambda: int(os.getenv("PROACTIVE_PARTIAL_NEAR_TP_PIPS", "80")))
    proactive_partial_medium_tp_pips: int = Field(default_factory=lambda: int(os.getenv("PROACTIVE_PARTIAL_MEDIUM_TP_PIPS", "150")))
    proactive_partial_be_trigger_pips: int = Field(default_factory=lambda: int(os.getenv("PROACTIVE_PARTIAL_BE_TRIGGER_PIPS", "30")))
    reentry_mode: str = Field(default_factory=lambda: os.getenv("REENTRY_MODE", "auto"))
    continuation_max_adds: int = Field(default_factory=lambda: int(os.getenv("CONTINUATION_MAX_ADDS", "2")))
    same_direction_close_on_reentry: bool = Field(default_factory=lambda: os.getenv("SAME_DIRECTION_CLOSE_ON_REENTRY", "false").lower() == "true")

    dry_run: bool = Field(default_factory=lambda: os.getenv("DRY_RUN", "true").lower() == "true")
    auto_close_opposite: bool = Field(default_factory=lambda: os.getenv("AUTO_CLOSE_OPPOSITE", "true").lower() == "true")
    slippage_deviation_points: int = Field(default_factory=lambda: int(os.getenv("SLIPPAGE_DEVIATION_POINTS", "50")))
    stale_signal_minutes: int = Field(default_factory=lambda: int(os.getenv("STALE_SIGNAL_MINUTES", "120")))
    reconcile_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("RECONCILE_INTERVAL_SECONDS", "20")))

    dashboard_host: str = Field(default_factory=lambda: os.getenv("DASHBOARD_HOST", "127.0.0.1"))
    dashboard_port: int = Field(default_factory=lambda: int(os.getenv("DASHBOARD_PORT", "8080")))

    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    parser_trace: bool = Field(default_factory=lambda: os.getenv("PARSER_TRACE", "false").lower() == "true")

    db_url: str = Field(default_factory=lambda: os.getenv("DB_URL", "sqlite:///state.db"))

    def validate_required(self) -> None:
        missing = []
        if not self.tg_api_id:
            missing.append("TG_API_ID")
        if not self.tg_api_hash:
            missing.append("TG_API_HASH")
        if not self.tg_allowed_chat:
            missing.append("TG_ALLOWED_CHAT")
        if not self.mt5_login:
            missing.append("MT5_LOGIN")
        if not self.mt5_password:
            missing.append("MT5_PASSWORD")
        if not self.mt5_server:
            missing.append("MT5_SERVER")

        if missing:
            raise ValueError(f"Missing required config keys: {', '.join(missing)}")


settings = Settings()
