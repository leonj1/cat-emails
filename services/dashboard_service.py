"""
Dashboard Data Service for Cat-Emails Web UI Dashboard

This service aggregates email category data from the existing database and enforces
the 40-character category name constraint while providing formatted data for web consumption.
"""
import logging
from utils.logger import get_logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from services.database_service import DatabaseService
from models.email_category import EmailCategory

logger = get_logger(__name__)


class TimePeriod(Enum):
    """Supported time periods for dashboard data"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendDirection(Enum):
    """Trend direction indicators"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


@dataclass
class CategoryData:
    """Data structure for category information"""
    name: str  # Truncated display name (≤40 chars)
    original_name: str  # Original category name
    count: int
    percentage: float
    rank: int
    deleted: int = 0
    archived: int = 0
    trend: TrendDirection = TrendDirection.STABLE


@dataclass
class DashboardStatistics:
    """Overall dashboard statistics"""
    total_emails: int
    total_processed: int
    total_deleted: int
    total_archived: int
    total_skipped: int
    avg_processing_time: float
    success_rate: float
    period: str
    last_updated: datetime


class DashboardService:
    """Service for dashboard data aggregation and formatting"""
    
    MAX_CATEGORY_NAME_LENGTH = 40
    DEFAULT_TOP_CATEGORIES_LIMIT = 25
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        """Initialize dashboard service with database service dependency"""
        self.db_service = db_service or DatabaseService()
        logger.info("Dashboard service initialized")
    
    def _get_display_name(self, category_name: str) -> str:
        """Convert category name to user-friendly display name"""
        try:
            # Try to get enum display name
            if hasattr(EmailCategory, category_name):
                enum_category = getattr(EmailCategory, category_name)
                return enum_category.name.replace('_', ' ').title()
        except:
            pass
        
        # Fallback to basic formatting
        if category_name.isupper() and '_' in category_name:
            return category_name.replace('_', ' ').title()
        
        return category_name
    
    def format_category_name(self, category_name: str, max_length: int = MAX_CATEGORY_NAME_LENGTH) -> str:
        """
        Intelligently truncate category names to specified length.
        
        Preserves important words and adds ellipsis when truncated.
        Always tries to use display name format first.
        
        Args:
            category_name: Original category name
            max_length: Maximum allowed length (default: 40)
            
        Returns:
            Formatted category name ≤ max_length characters
        """
        # First, try to get the display name
        display_name = self._get_display_name(category_name)
        
        # If display name fits, use it
        if len(display_name) <= max_length:
            return display_name
        
        # If original name is shorter and fits, use it
        if len(category_name) <= max_length:
            return category_name
        
        # Need to truncate - use the shorter of original or display name as base
        base_name = display_name if len(display_name) < len(category_name) else category_name
        
        if len(base_name) <= max_length:
            return base_name
        
        # Reserve space for ellipsis
        available_length = max_length - 3
        
        # Split into words and try to preserve important words
        words = base_name.split()
        
        if len(words) == 1:
            # Single word - truncate with ellipsis
            return base_name[:available_length] + "..."
        
        # Multi-word - preserve first and important words
        result = words[0]
        
        for word in words[1:]:
            if len(result + " " + word) <= available_length:
                result += " " + word
            else:
                break
        
        return result + "..."
    
    def calculate_percentages(self, category_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate percentage of total for each category.
        
        Args:
            category_data: List of category dictionaries with 'count' field
            
        Returns:
            Updated category data with 'percentage' field
        """
        if not category_data:
            return category_data
        
        total_count = sum(item.get('count', 0) for item in category_data)
        
        if total_count == 0:
            for item in category_data:
                item['percentage'] = 0.0
            return category_data
        
        for item in category_data:
            count = item.get('count', 0)
            item['percentage'] = round((count / total_count) * 100, 1)
        
        return category_data
    
    def _calculate_trend_direction(self, current_count: int, previous_count: int, 
                                 threshold: float = 0.1) -> TrendDirection:
        """
        Calculate trend direction based on current vs previous counts.
        
        Args:
            current_count: Current period count
            previous_count: Previous period count
            threshold: Minimum change threshold (10% default)
            
        Returns:
            TrendDirection enum value
        """
        if previous_count == 0:
            return TrendDirection.STABLE if current_count == 0 else TrendDirection.UP
        
        change_ratio = abs(current_count - previous_count) / previous_count
        
        if change_ratio < threshold:
            return TrendDirection.STABLE
        elif current_count > previous_count:
            return TrendDirection.UP
        else:
            return TrendDirection.DOWN
    
    def get_top_categories(self, limit: int = DEFAULT_TOP_CATEGORIES_LIMIT, 
                          period: str = TimePeriod.WEEK.value) -> Dict[str, Any]:
        """
        Get top N categories with counts, percentages, and trends.
        
        Args:
            limit: Maximum number of categories to return (default: 25)
            period: Time period ('day', 'week', 'month')
            
        Returns:
            Dictionary with categories, metadata, and statistics
        """
        try:
            logger.info(f"Getting top {limit} categories for period: {period}")
            
            # Get current period data
            if period == TimePeriod.DAY.value:
                current_data = self.db_service.get_daily_summary()
            elif period == TimePeriod.WEEK.value:
                current_data = self.db_service.get_weekly_summary()
            elif period == TimePeriod.MONTH.value:
                current_data = self.db_service.get_monthly_summary()
            else:
                raise ValueError(f"Unsupported period: {period}")
            
            # Get previous period data for trend calculation
            if period == TimePeriod.DAY.value:
                previous_data = self.db_service.get_daily_summary(
                    datetime.now() - timedelta(days=1)
                )
            elif period == TimePeriod.WEEK.value:
                previous_data = self.db_service.get_weekly_summary(weeks_ago=1)
            elif period == TimePeriod.MONTH.value:
                previous_data = self.db_service.get_monthly_summary(months_ago=1)
            
            # Create lookup for previous period counts
            previous_counts = {}
            for cat in previous_data.get('categories', []):
                previous_counts[cat['name']] = cat['count']
            
            # Process current categories
            current_categories = current_data.get('categories', [])[:limit]
            
            # Add percentages
            categories_with_percentages = self.calculate_percentages(current_categories)
            
            # Build category data with trends
            formatted_categories = []
            
            for rank, category in enumerate(categories_with_percentages, 1):
                original_name = category['name']
                formatted_name = self.format_category_name(original_name)
                
                # Calculate trend
                current_count = category['count']
                previous_count = previous_counts.get(original_name, 0)
                trend = self._calculate_trend_direction(current_count, previous_count)
                
                category_data = CategoryData(
                    name=formatted_name,
                    original_name=original_name,
                    count=current_count,
                    percentage=category.get('percentage', 0.0),
                    rank=rank,
                    deleted=category.get('deleted', 0),
                    trend=trend
                )
                
                formatted_categories.append({
                    'name': category_data.name,
                    'original_name': category_data.original_name,
                    'count': category_data.count,
                    'percentage': category_data.percentage,
                    'rank': category_data.rank,
                    'deleted': category_data.deleted,
                    'trend': category_data.trend.value
                })
            
            # Build response
            total_emails = current_data.get('metrics', {}).get('total_processed', 0)
            
            response = {
                'categories': formatted_categories,
                'total_emails': total_emails,
                'period': period,
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'metadata': {
                    'limit_applied': limit,
                    'categories_returned': len(formatted_categories),
                    'total_categories_available': len(current_data.get('categories', [])),
                    'period_info': current_data.get('period', {})
                }
            }
            
            logger.info(f"Successfully retrieved {len(formatted_categories)} categories")
            return response
            
        except Exception as e:
            logger.error(f"Error getting top categories: {e}")
            return {
                'categories': [],
                'total_emails': 0,
                'period': period,
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'error': str(e)
            }
    
    def get_category_statistics(self, period: str = TimePeriod.WEEK.value) -> Dict[str, Any]:
        """
        Get overall category statistics and distribution data.
        
        Args:
            period: Time period ('day', 'week', 'month')
            
        Returns:
            Dictionary with comprehensive statistics
        """
        try:
            logger.info(f"Getting category statistics for period: {period}")
            
            # Get period data
            if period == TimePeriod.DAY.value:
                data = self.db_service.get_daily_summary()
            elif period == TimePeriod.WEEK.value:
                data = self.db_service.get_weekly_summary()
            elif period == TimePeriod.MONTH.value:
                data = self.db_service.get_monthly_summary()
            else:
                raise ValueError(f"Unsupported period: {period}")
            
            metrics = data.get('metrics', {})
            categories = data.get('categories', [])
            domains = data.get('domains', [])
            senders = data.get('senders', [])
            
            # Calculate success rate
            total_processed = metrics.get('total_processed', 0)
            total_error = total_processed - metrics.get('total_archived', 0) - metrics.get('total_deleted', 0)
            success_rate = ((total_processed - max(0, total_error)) / max(1, total_processed)) * 100
            
            # Create dashboard statistics
            statistics = DashboardStatistics(
                total_emails=total_processed,
                total_processed=total_processed,
                total_deleted=metrics.get('total_deleted', 0),
                total_archived=metrics.get('total_archived', 0),
                total_skipped=metrics.get('total_skipped', 0),
                avg_processing_time=metrics.get('avg_processing_seconds', 0),
                success_rate=round(success_rate, 1),
                period=period,
                last_updated=datetime.utcnow()
            )
            
            # Format category distribution
            formatted_categories = []
            categories_with_percentages = self.calculate_percentages(categories)
            
            for category in categories_with_percentages:
                original_name = category['name']
                formatted_name = self.format_category_name(original_name)
                
                formatted_categories.append({
                    'name': formatted_name,
                    'original_name': original_name,
                    'count': category['count'],
                    'percentage': category.get('percentage', 0.0),
                    'deleted': category.get('deleted', 0)
                })
            
            response = {
                'statistics': {
                    'total_emails': statistics.total_emails,
                    'total_processed': statistics.total_processed,
                    'total_deleted': statistics.total_deleted,
                    'total_archived': statistics.total_archived,
                    'total_skipped': statistics.total_skipped,
                    'avg_processing_time_seconds': statistics.avg_processing_time,
                    'success_rate_percent': statistics.success_rate,
                    'period': statistics.period,
                    'last_updated': statistics.last_updated.isoformat() + 'Z'
                },
                'category_distribution': formatted_categories,
                'top_domains': [
                    {
                        'domain': domain['domain'],
                        'count': domain['count'],
                        'deleted': domain.get('deleted', 0),
                        'is_blocked': domain.get('is_blocked', False)
                    } for domain in domains[:10]
                ],
                'top_senders': [
                    {
                        'email': sender['email'],
                        'name': sender.get('name', ''),
                        'count': sender['count'],
                        'deleted': sender.get('deleted', 0)
                    } for sender in senders[:10]
                ],
                'period_info': data.get('period', {})
            }
            
            logger.info("Successfully retrieved category statistics")
            return response
            
        except Exception as e:
            logger.error(f"Error getting category statistics: {e}")
            return {
                'statistics': {},
                'category_distribution': [],
                'top_domains': [],
                'top_senders': [],
                'error': str(e)
            }
    
    def get_trends_data(self, categories: Optional[List[str]] = None, 
                       days: int = 30) -> Dict[str, Any]:
        """
        Get historical trend data for specified categories.
        
        Args:
            categories: List of category names to include (None for all)
            days: Number of days to look back
            
        Returns:
            Dictionary with trend data and metadata
        """
        try:
            logger.info(f"Getting trends data for {days} days")
            
            # Get raw trend data from database
            raw_trends = self.db_service.get_category_trends(days=days)
            
            if not raw_trends:
                return {
                    'trends': {},
                    'days': days,
                    'categories_included': [],
                    'total_categories': 0,
                    'last_updated': datetime.utcnow().isoformat() + 'Z'
                }
            
            # Filter categories if specified
            if categories:
                filtered_trends = {}
                for category, data_points in raw_trends.items():
                    # Check both original name and display name
                    formatted_name = self.format_category_name(category)
                    
                    if (category in categories or 
                        formatted_name in categories):
                        filtered_trends[category] = data_points
                raw_trends = filtered_trends
            
            # Format trend data
            formatted_trends = {}
            categories_included = []
            
            for category, data_points in raw_trends.items():
                formatted_name = self.format_category_name(category)
                
                # Convert data points to JSON-serializable format
                trend_data = []
                for date, count in data_points:
                    trend_data.append({
                        'date': date.isoformat(),
                        'count': count
                    })
                
                # Calculate trend indicators
                if len(trend_data) >= 2:
                    recent_avg = sum(point['count'] for point in trend_data[-7:]) / min(7, len(trend_data))
                    older_avg = sum(point['count'] for point in trend_data[-14:-7]) / min(7, len(trend_data[:-7]))
                    trend_direction = self._calculate_trend_direction(int(recent_avg), int(older_avg))
                else:
                    trend_direction = TrendDirection.STABLE
                
                formatted_trends[formatted_name] = {
                    'original_name': category,
                    'display_name': formatted_name,
                    'data_points': trend_data,
                    'total_points': len(trend_data),
                    'trend_direction': trend_direction.value,
                    'latest_count': trend_data[-1]['count'] if trend_data else 0,
                    'max_count': max(point['count'] for point in trend_data) if trend_data else 0
                }
                
                categories_included.append(formatted_name)
            
            response = {
                'trends': formatted_trends,
                'days': days,
                'categories_included': categories_included,
                'total_categories': len(formatted_trends),
                'date_range': {
                    'start': (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z',
                    'end': datetime.utcnow().isoformat() + 'Z'
                },
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }
            
            logger.info(f"Successfully retrieved trends for {len(formatted_trends)} categories")
            return response
            
        except Exception as e:
            logger.error(f"Error getting trends data: {e}")
            return {
                'trends': {},
                'days': days,
                'categories_included': [],
                'total_categories': 0,
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }
    
    def get_processing_performance(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent processing performance metrics.
        
        Args:
            limit: Number of recent runs to include
            
        Returns:
            Dictionary with performance data
        """
        try:
            logger.info(f"Getting processing performance for {limit} recent runs")
            
            runs = self.db_service.get_processing_runs(limit=limit)
            
            if not runs:
                return {
                    'performance_metrics': {},
                    'recent_runs': [],
                    'last_updated': datetime.utcnow().isoformat() + 'Z'
                }
            
            # Calculate aggregate metrics
            total_runs = len(runs)
            successful_runs = sum(1 for run in runs if run.get('success', False))
            total_processed = sum(run.get('emails_processed', 0) for run in runs)
            total_duration = sum(run.get('duration_seconds', 0) or 0 for run in runs if run.get('duration_seconds'))
            
            success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0
            avg_processing_time = total_duration / len([r for r in runs if r.get('duration_seconds')]) if any(r.get('duration_seconds') for r in runs) else 0
            avg_emails_per_run = total_processed / total_runs if total_runs > 0 else 0
            
            # Format recent runs
            formatted_runs = []
            for run in runs[:limit]:
                formatted_runs.append({
                    'run_id': run.get('run_id', ''),
                    'started_at': run.get('started_at').isoformat() + 'Z' if run.get('started_at') else None,
                    'completed_at': run.get('completed_at').isoformat() + 'Z' if run.get('completed_at') else None,
                    'duration_seconds': run.get('duration_seconds', 0),
                    'emails_processed': run.get('emails_processed', 0),
                    'emails_deleted': run.get('emails_deleted', 0),
                    'success': run.get('success', False),
                    'error_message': run.get('error_message', '')
                })
            
            response = {
                'performance_metrics': {
                    'total_runs_analyzed': total_runs,
                    'success_rate_percent': round(success_rate, 1),
                    'avg_processing_time_seconds': round(avg_processing_time, 2),
                    'avg_emails_per_run': round(avg_emails_per_run, 1),
                    'total_emails_processed': total_processed,
                    'total_duration_seconds': round(total_duration, 2)
                },
                'recent_runs': formatted_runs,
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }
            
            logger.info("Successfully retrieved processing performance metrics")
            return response
            
        except Exception as e:
            logger.error(f"Error getting processing performance: {e}")
            return {
                'performance_metrics': {},
                'recent_runs': [],
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }
    
    def get_comprehensive_dashboard_data(self, period: str = TimePeriod.WEEK.value, 
                                       top_categories_limit: int = DEFAULT_TOP_CATEGORIES_LIMIT) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data in a single call.
        
        Args:
            period: Time period for data aggregation
            top_categories_limit: Number of top categories to include
            
        Returns:
            Dictionary with all dashboard data
        """
        try:
            logger.info(f"Getting comprehensive dashboard data for period: {period}")
            
            # Get all required data
            top_categories = self.get_top_categories(limit=top_categories_limit, period=period)
            statistics = self.get_category_statistics(period=period)
            trends = self.get_trends_data(days=30)  # Last 30 days for trends
            performance = self.get_processing_performance(limit=10)
            
            response = {
                'overview': {
                    'period': period,
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'data_version': '1.0.0'
                },
                'top_categories': top_categories,
                'statistics': statistics,
                'trends': trends,
                'performance': performance
            }
            
            logger.info("Successfully generated comprehensive dashboard data")
            return response
            
        except Exception as e:
            logger.error(f"Error getting comprehensive dashboard data: {e}")
            return {
                'overview': {
                    'period': period,
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'error': str(e)
                },
                'top_categories': {'categories': [], 'total_emails': 0},
                'statistics': {'statistics': {}, 'category_distribution': []},
                'trends': {'trends': {}},
                'performance': {'performance_metrics': {}, 'recent_runs': []}
            }


# Example usage and testing
if __name__ == "__main__":
    # Test the dashboard service
    dashboard = DashboardService()
    
    print("Testing category name formatting...")
    test_names = [
        "FINANCIAL_NOTIFICATION_ALERTS_BANKING",
        "HEALTH_WELLNESS",
        "PERSONAL_CORRESPONDENCE", 
        "This is a very long category name that exceeds forty characters and needs truncation",
        "Short"
    ]
    
    for name in test_names:
        formatted = dashboard.format_category_name(name)
        print(f"  '{name}' -> '{formatted}' ({len(formatted)} chars)")
    
    print("\nTesting dashboard data retrieval...")
    try:
        data = dashboard.get_comprehensive_dashboard_data(period="week")
        print(f"  Categories returned: {len(data['top_categories']['categories'])}")
        print(f"  Total emails: {data['top_categories']['total_emails']}")
        print("  Dashboard service working correctly!")
    except Exception as e:
        print(f"  Error: {e}")