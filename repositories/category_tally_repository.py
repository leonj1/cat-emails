"""
Category Tally Repository Implementation.

This implementation uses SQLAlchemy ORM to persist and retrieve email category tallies.
"""
from typing import List, Optional, Dict
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from repositories.category_tally_repository_interface import ICategoryTallyRepository
from models.category_tally_models import (
    DailyCategoryTally,
    CategorySummaryItem,
    AggregatedCategoryTally
)
from models.database import CategoryDailyTally


class CategoryTallyRepository(ICategoryTallyRepository):
    """
    SQLAlchemy implementation of ICategoryTallyRepository.

    This repository manages category tallies in a normalized database schema
    where each category count is stored as a separate row.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def save_daily_tally(
        self,
        email_address: str,
        tally_date: date,
        category_counts: dict,
        total_emails: int
    ) -> DailyCategoryTally:
        """
        Save or update a daily category tally for an account.

        Implements upsert semantics by updating existing records or creating new ones.
        """
        now = datetime.utcnow()

        # For each category in the counts, upsert a row
        for category, count in category_counts.items():
            # Check if record exists
            existing = self.session.query(CategoryDailyTally).filter(
                and_(
                    CategoryDailyTally.email_address == email_address,
                    CategoryDailyTally.tally_date == tally_date,
                    CategoryDailyTally.category == category
                )
            ).first()

            if existing:
                # Replace count with new value (upsert semantics)
                existing.count = count
                existing.total_emails = total_emails
                existing.updated_at = now
            else:
                # Create new record
                new_tally = CategoryDailyTally(
                    email_address=email_address,
                    tally_date=tally_date,
                    category=category,
                    count=count,
                    total_emails=total_emails,
                    created_at=now,
                    updated_at=now
                )
                self.session.add(new_tally)

        # Commit once after all category updates for better transaction management
        self.session.commit()

        # Return the consolidated tally
        return self._build_daily_tally(email_address, tally_date, category_counts, total_emails)

    def get_tally(
        self,
        email_address: str,
        tally_date: date
    ) -> Optional[DailyCategoryTally]:
        """
        Retrieve a single daily tally for a specific account and date.
        """
        # Query all category rows for this email and date
        records = self.session.query(CategoryDailyTally).filter(
            and_(
                CategoryDailyTally.email_address == email_address,
                CategoryDailyTally.tally_date == tally_date
            )
        ).all()

        if not records:
            return None

        # Consolidate into a single DailyCategoryTally
        category_counts = {record.category: record.count for record in records}
        total_emails = records[0].total_emails
        created_at = records[0].created_at
        updated_at = max(record.updated_at for record in records)
        tally_id = records[0].id

        return DailyCategoryTally(
            id=tally_id,
            email_address=email_address,
            tally_date=tally_date,
            category_counts=category_counts,
            total_emails=total_emails,
            created_at=created_at,
            updated_at=updated_at
        )

    def get_tallies_for_period(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> List[DailyCategoryTally]:
        """
        Retrieve all daily tallies for an account within a date range.
        """
        # Query all records in the date range
        records = self.session.query(CategoryDailyTally).filter(
            and_(
                CategoryDailyTally.email_address == email_address,
                CategoryDailyTally.tally_date >= start_date,
                CategoryDailyTally.tally_date <= end_date
            )
        ).order_by(CategoryDailyTally.tally_date).all()

        if not records:
            return []

        # Group records by date
        tallies_by_date = defaultdict(list)
        for record in records:
            tallies_by_date[record.tally_date].append(record)

        # Build DailyCategoryTally for each date
        result = []
        for tally_date, date_records in sorted(tallies_by_date.items()):
            category_counts = {record.category: record.count for record in date_records}
            total_emails = date_records[0].total_emails
            created_at = date_records[0].created_at
            updated_at = max(record.updated_at for record in date_records)
            tally_id = date_records[0].id

            result.append(DailyCategoryTally(
                id=tally_id,
                email_address=email_address,
                tally_date=tally_date,
                category_counts=category_counts,
                total_emails=total_emails,
                created_at=created_at,
                updated_at=updated_at
            ))

        return result

    def get_aggregated_tallies(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> AggregatedCategoryTally:
        """
        Get aggregated statistics across a date range for an account.
        """
        # Query all records in the date range
        records = self.session.query(CategoryDailyTally).filter(
            and_(
                CategoryDailyTally.email_address == email_address,
                CategoryDailyTally.tally_date >= start_date,
                CategoryDailyTally.tally_date <= end_date
            )
        ).all()

        if not records:
            # Return empty aggregation
            return AggregatedCategoryTally(
                email_address=email_address,
                start_date=start_date,
                end_date=end_date,
                total_emails=0,
                days_with_data=0,
                category_summaries=[]
            )

        # Calculate total emails (use the total_emails field from any record)
        # Get unique dates to count days with data
        unique_dates = set(record.tally_date for record in records)
        days_with_data = len(unique_dates)

        # Aggregate by category
        category_totals = defaultdict(int)
        for record in records:
            category_totals[record.category] += record.count

        # Calculate total emails across all categories
        total_emails = sum(category_totals.values())

        # Build category summaries
        category_summaries = []
        for category, total_count in category_totals.items():
            # Calculate percentage
            percentage = (total_count / total_emails * 100.0) if total_emails > 0 else 0.0

            # Calculate daily average
            daily_average = total_count / days_with_data if days_with_data > 0 else 0.0

            category_summaries.append(CategorySummaryItem(
                category=category,
                total_count=total_count,
                percentage=percentage,
                daily_average=daily_average,
                trend=None
            ))

        return AggregatedCategoryTally(
            email_address=email_address,
            start_date=start_date,
            end_date=end_date,
            total_emails=total_emails,
            days_with_data=days_with_data,
            category_summaries=category_summaries
        )

    def delete_tallies_before(
        self,
        email_address: str,
        cutoff_date: date
    ) -> int:
        """
        Delete all tallies for an account before a cutoff date.
        """
        # Count records to be deleted
        deleted_count = self.session.query(CategoryDailyTally).filter(
            and_(
                CategoryDailyTally.email_address == email_address,
                CategoryDailyTally.tally_date < cutoff_date
            )
        ).delete(synchronize_session=False)

        self.session.commit()
        return deleted_count

    def _build_daily_tally(
        self,
        email_address: str,
        tally_date: date,
        category_counts: Dict[str, int],
        total_emails: int
    ) -> DailyCategoryTally:
        """
        Helper method to build a DailyCategoryTally from saved data.
        """
        # Query one record to get timestamps
        record = self.session.query(CategoryDailyTally).filter(
            and_(
                CategoryDailyTally.email_address == email_address,
                CategoryDailyTally.tally_date == tally_date
            )
        ).first()

        if record:
            return DailyCategoryTally(
                id=record.id,
                email_address=email_address,
                tally_date=tally_date,
                category_counts=category_counts,
                total_emails=total_emails,
                created_at=record.created_at,
                updated_at=record.updated_at
            )
        else:
            # Fallback if no record found
            now = datetime.utcnow()
            return DailyCategoryTally(
                id=None,
                email_address=email_address,
                tally_date=tally_date,
                category_counts=category_counts,
                total_emails=total_emails,
                created_at=now,
                updated_at=now
            )
