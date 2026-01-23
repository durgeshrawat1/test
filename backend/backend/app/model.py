from sqlalchemy import Column, Integer, String, Boolean, DateTime, MetaData, Text
from sqlalchemy.sql import func
from .database import Base

# System metadata lives in the 'system' schema to keep it separate from BU data
metadata = MetaData(schema="system")

class SchemaMetadata(Base):
    __tablename__ = "schemas"
    __table_args__ = {"schema": "system"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)         # Display name of the table
    description = Column(Text)
    business_unit = Column(String, index=True)    # e.g., 'Finance', 'Market'
    access_group = Column(String, index=True)     # e.g., 'Finance_Analyst'
    physical_table_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
