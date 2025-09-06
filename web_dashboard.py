#!/usr/bin/env python3
"""
Flask Web Dashboard for Cat-Emails
Provides a web interface for viewing email categorization statistics and trends
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify, request, redirect, url_for
from services.database_service import DatabaseService
from services.dashboard_service import DashboardService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize services
db_path = os.getenv('DB_PATH', './email_summaries/summaries.db')
db_service = DatabaseService(db_path)
dashboard_service = DashboardService(db_service)

def truncate_category_name(name: str, max_length: int = 40) -> str:
    """Truncate category names to specified length with ellipsis if needed"""
    if len(name) <= max_length:
        return name
    return name[:max_length-3] + "..."

def format_category_display(name: str) -> str:
    """Format category name for display (replace underscores, title case)"""
    return name.replace('_', ' ').title()


@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        logger.info("Rendering dashboard page")
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/api/stats/overview')
def api_overview_stats():
    """API endpoint for overview statistics"""
    try:
        period = request.args.get('period', 'week')  # day, week, month
        
        if period == 'day':
            summary = db_service.get_daily_summary()
        elif period == 'month':
            summary = db_service.get_monthly_summary()
        else:  # default to week
            summary = db_service.get_weekly_summary()
        
        return jsonify({
            'success': True,
            'data': summary,
            'period': period
        })
    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats/categories')
def api_category_stats():
    """API endpoint for top email categories"""
    try:
        period = request.args.get('period', 'week')
        limit = int(request.args.get('limit', 25))
        
        if period == 'day':
            summary = db_service.get_daily_summary()
        elif period == 'month':
            summary = db_service.get_monthly_summary()
        else:
            summary = db_service.get_weekly_summary()
        
        # Process categories and limit to top 25 with 40 char names
        categories = summary.get('categories', [])
        processed_categories = []
        
        for category in categories[:limit]:
            display_name = format_category_display(category['name'])
            truncated_name = truncate_category_name(display_name, 40)
            
            processed_categories.append({
                'name': truncated_name,
                'original_name': category['name'],
                'display_name': display_name,
                'count': category['count'],
                'deleted': category.get('deleted', 0),
                'percentage': 0  # Will be calculated on frontend
            })
        
        return jsonify({
            'success': True,
            'data': processed_categories,
            'period': period,
            'total_count': len(categories)
        })
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats/senders')
def api_sender_stats():
    """API endpoint for top email senders"""
    try:
        period = request.args.get('period', 'week')
        limit = int(request.args.get('limit', 25))
        
        if period == 'day':
            summary = db_service.get_daily_summary()
        elif period == 'month':
            summary = db_service.get_monthly_summary()
        else:
            summary = db_service.get_weekly_summary()
        
        senders = summary.get('senders', [])[:limit]
        
        return jsonify({
            'success': True,
            'data': senders,
            'period': period,
            'total_count': len(summary.get('senders', []))
        })
    except Exception as e:
        logger.error(f"Error getting sender stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats/domains')
def api_domain_stats():
    """API endpoint for top email domains"""
    try:
        period = request.args.get('period', 'week')
        limit = int(request.args.get('limit', 25))
        
        if period == 'day':
            summary = db_service.get_daily_summary()
        elif period == 'month':
            summary = db_service.get_monthly_summary()
        else:
            summary = db_service.get_weekly_summary()
        
        domains = summary.get('domains', [])[:limit]
        
        return jsonify({
            'success': True,
            'data': domains,
            'period': period,
            'total_count': len(summary.get('domains', []))
        })
    except Exception as e:
        logger.error(f"Error getting domain stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats/trends')
def api_trends():
    """API endpoint for category trends over time"""
    try:
        days = int(request.args.get('days', 30))
        trends = db_service.get_category_trends(days)
        
        # Format trends data for Chart.js
        formatted_trends = {}
        for category, data_points in trends.items():
            display_name = format_category_display(category)
            truncated_name = truncate_category_name(display_name, 40)
            
            formatted_trends[truncated_name] = [
                {
                    'date': point[0].isoformat(),
                    'count': point[1]
                } for point in data_points
            ]
        
        return jsonify({
            'success': True,
            'data': formatted_trends,
            'days': days
        })
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats/processing-runs')
def api_processing_runs():
    """API endpoint for recent processing runs"""
    try:
        limit = int(request.args.get('limit', 50))
        runs = db_service.get_processing_runs(limit)
        
        return jsonify({
            'success': True,
            'data': runs,
            'total_count': len(runs)
        })
    except Exception as e:
        logger.error(f"Error getting processing runs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories/top')
def api_categories_top():
    """API endpoint for top N categories with counts (using DashboardService)"""
    try:
        limit = int(request.args.get('limit', 25))
        period = request.args.get('period', 'week')
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({
                'success': False,
                'error': 'Limit must be between 1 and 100'
            }), 400
        
        # Validate period
        valid_periods = ['day', 'week', 'month']
        if period not in valid_periods:
            return jsonify({
                'success': False,
                'error': f'Period must be one of: {", ".join(valid_periods)}'
            }), 400
        
        data = dashboard_service.get_top_categories(limit=limit, period=period)
        
        return jsonify({
            'success': True,
            'data': data['categories'],
            'metadata': data.get('metadata', {}),
            'total_emails': data['total_emails'],
            'period': data['period'],
            'last_updated': data['last_updated']
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error getting top categories: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/api/metrics')
def api_metrics():
    """API endpoint for system performance metrics (using DashboardService)"""
    try:
        limit = int(request.args.get('limit', 10))
        include_runs = request.args.get('include_runs', 'true').lower() == 'true'
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({
                'success': False,
                'error': 'Limit must be between 1 and 100'
            }), 400
        
        # Get performance data
        performance_data = dashboard_service.get_processing_performance(limit=limit)
        
        response = {
            'success': True,
            'data': {
                'performance_metrics': performance_data['performance_metrics'],
                'last_updated': performance_data['last_updated']
            }
        }
        
        # Optionally include recent runs
        if include_runs:
            response['data']['recent_runs'] = performance_data['recent_runs']
        
        return jsonify(response)
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    try:
        # Test database connectivity
        db_healthy = False
        try:
            # Try to get a simple summary to verify DB works
            test_summary = db_service.get_daily_summary()
            db_healthy = True
        except Exception as db_error:
            logger.warning(f"Database health check failed: {db_error}")
        
        # Test dashboard service
        dashboard_healthy = False
        try:
            # Try to format a category name to verify service works
            test_format = dashboard_service.format_category_name("TEST_CATEGORY")
            dashboard_healthy = True
        except Exception as service_error:
            logger.warning(f"Dashboard service health check failed: {service_error}")
        
        overall_healthy = db_healthy and dashboard_healthy
        status_code = 200 if overall_healthy else 503
        
        return jsonify({
            'success': True,
            'status': 'healthy' if overall_healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': 'healthy' if db_healthy else 'unhealthy',
                'dashboard_service': 'healthy' if dashboard_healthy else 'unhealthy'
            }
        }), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Configuration
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Cat-Emails Web Dashboard on {host}:{port}")
    logger.info(f"Database path: {db_path}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)