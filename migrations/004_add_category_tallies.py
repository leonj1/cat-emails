"""
Migration 004: Add category daily tallies table.

This migration creates the category_daily_tallies table for storing
daily email category aggregations per account.
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, Index, UniqueConstraint
from datetime import datetime


def upgrade(engine):
    """
    Create the category_daily_tallies table.

    This table stores daily category tallies with a normalized schema where
    each category count is a separate row.
    """
    from sqlalchemy import MetaData, Table

    metadata = MetaData()

    # Create category_daily_tallies table
    category_daily_tallies = Table(
        'category_daily_tallies',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('email_address', String(255), nullable=False, index=True),
        Column('tally_date', Date, nullable=False, index=True),
        Column('category', String(100), nullable=False),
        Column('count', Integer, default=0, nullable=False),
        Column('total_emails', Integer, default=0, nullable=False),
        Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
        Column('updated_at', DateTime, default=datetime.utcnow, nullable=False),

        # Constraints
        UniqueConstraint('email_address', 'tally_date', 'category', name='uq_email_date_category'),

        # Indexes for efficient queries
        Index('idx_email_date', 'email_address', 'tally_date'),
        Index('idx_email_category', 'email_address', 'category'),
        Index('idx_date_range', 'email_address', 'tally_date', 'category'),
    )

    metadata.create_all(engine)


def downgrade(engine):
    """
    Drop the category_daily_tallies table.
    """
    from sqlalchemy import MetaData, Table

    metadata = MetaData()
    metadata.reflect(bind=engine)

    if 'category_daily_tallies' in metadata.tables:
        table = metadata.tables['category_daily_tallies']
        table.drop(engine)
