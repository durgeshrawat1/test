from sqlalchemy import Column, Integer, String, Boolean, DateTime, MetaData
from sqlalchemy.sql import func
from .database import Base

# --- INDUSTRY STANDARD: Schema Isolation ---
# We define a metadata object pointing to our specific schema 'banking'
# This avoids the mess and permission issues of the default 'public' schema.
metadata = MetaData(schema="banking")

class User(Base):
    __tablename__ = "users"
    
    # Explicitly tell SQLAlchemy to put this table in the 'banking' schema
    __table_args__ = {"schema": "banking"}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Audit trail fields (Critical for finance)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# You can add more financial models here (Accounts, Transactions)
