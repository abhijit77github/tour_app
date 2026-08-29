from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "tour_app_db"
    mongodb_max_pool_size: int = 100
    mongodb_min_pool_size: int = 5
    mongodb_max_idle_time_ms: int = 60000
    mongodb_server_selection_timeout_ms: int = 5000
    mongodb_connect_timeout_ms: int = 5000
    mongodb_socket_timeout_ms: int = 15000
    mongodb_wait_queue_timeout_ms: int = 10000
    
    # JWT Settings
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8808
    
    # CORS
    frontend_url: str = "http://localhost:5173"
    
    # Email Settings (SMTP)
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_email: Optional[str] = None
    smtp_password: Optional[str] = None

    # SMS adapter scaffolding
    sms_provider: Optional[str] = None
    sms_api_key: Optional[str] = None
    sms_sender_id: Optional[str] = None

    # AWS Bedrock
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"

    # Planner billing configuration
    planner_impression_credits: int = 0
    planner_qualified_lead_credits: int = 0
    planner_conversion_credits: int = 0
    search_profile_click_credits: int = 1
    planner_intent_click_credits: int = 0
    billing_search_click_dedupe_minutes: int = 30
    billing_search_click_identity_mode: str = "session_first"
    billing_planner_impression_scope: str = "session"
    billing_refund_compensation_mode: str = "manual"

    # Payment gateway webhook scaffolding
    razorpay_webhook_secret: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    payu_webhook_secret: Optional[str] = None
    billing_webhook_event_retention_days: int = 180

    # Backup and restore
    backup_local_dir: str = "backups"
    backup_metadata_database_name: str = "tour_app_ops_db"
    backup_tool_mongodump: str = "mongodump"
    backup_tool_mongorestore: str = "mongorestore"
    backup_s3_bucket: Optional[str] = None
    backup_s3_prefix: str = "database-backups"
    backup_s3_region: Optional[str] = None
    backup_presign_expiry_seconds: int = 3600

    # Audit events
    audit_login_alert_threshold: int = 3
    audit_login_alert_window_minutes: int = 15

    # Authorization rollout controls
    rbac_step_up_required: bool = False
    rbac_step_up_max_age_minutes: int = 15
    rbac_audit_decisions: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
