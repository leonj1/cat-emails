"""Add repeat offender patterns table for tracking emails that consistently get deleted."""

from sqlalchemy import text


def upgrade(connection):
    """Add repeat_offender_patterns table."""
    connection.execute(text("""
        CREATE TABLE repeat_offender_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name VARCHAR(255) NOT NULL,
            
            -- Pattern identifiers (at least one must be set)
            sender_email VARCHAR(255) NULL,
            sender_domain VARCHAR(255) NULL,
            subject_pattern VARCHAR(500) NULL,
            
            -- Tracking information
            category VARCHAR(100) NOT NULL,
            total_occurrences INTEGER DEFAULT 0,
            deletion_count INTEGER DEFAULT 0,
            confidence_score REAL DEFAULT 0.0,
            
            -- Timestamps
            first_seen DATETIME NOT NULL,
            last_seen DATETIME NOT NULL,
            marked_as_repeat_offender DATETIME NULL,
            
            -- Status
            is_active BOOLEAN DEFAULT 1
        )
    """))
    
    # Add indexes
    connection.execute(text("""
        CREATE INDEX idx_account_sender ON repeat_offender_patterns (account_name, sender_email)
    """))
    
    connection.execute(text("""
        CREATE INDEX idx_account_domain ON repeat_offender_patterns (account_name, sender_domain)
    """))
    
    connection.execute(text("""
        CREATE INDEX idx_account_subject ON repeat_offender_patterns (account_name, subject_pattern)
    """))
    
    connection.execute(text("""
        CREATE INDEX idx_active_patterns ON repeat_offender_patterns (account_name, is_active)
    """))


def downgrade(connection):
    """Remove repeat_offender_patterns table."""
    connection.execute(text("DROP TABLE IF EXISTS repeat_offender_patterns"))
