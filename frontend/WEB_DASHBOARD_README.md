# Cat-Emails Web Dashboard

A responsive web interface for viewing Cat-Emails AI-powered email categorization statistics and analytics.

## Features

- **Real-time Dashboard**: View email processing statistics with automatic updates
- **Top 25 Categories**: Display most common email categories with ≤40 character names
- **Interactive Charts**: Pie charts, bar charts, and trend lines using Chart.js
- **Multiple Time Periods**: View data for today, this week, or this month
- **Responsive Design**: Bootstrap 5 responsive layout works on all devices
- **Processing Runs**: Monitor email processing job history and performance

## Quick Start

### 1. Install Dependencies

```bash
# Install Flask and web dependencies
pip install flask werkzeug jinja2

# Or install all web dependencies
pip install -r requirements-web.txt
```

### 2. Run the Dashboard

```bash
# Simple start (uses defaults)
python run_dashboard.py

# Or run directly
python web_dashboard.py
```

### 3. Access the Dashboard

Open your browser to: `http://localhost:5000`

## Configuration

Set these environment variables to customize the dashboard:

```bash
# Server configuration
FLASK_HOST=0.0.0.0          # Server host (default: 0.0.0.0)
FLASK_PORT=5000             # Server port (default: 5000)
FLASK_DEBUG=False           # Debug mode (default: False)

# Database configuration
DB_PATH=./email_summaries/summaries.db  # Database path

# Security
SECRET_KEY=your-secret-key  # Flask secret key (change in production!)
```

### Example with Custom Configuration

```bash
# Run on different port with debug enabled
FLASK_PORT=8080 FLASK_DEBUG=True python run_dashboard.py

# Use custom database location
DB_PATH=/path/to/custom/summaries.db python run_dashboard.py
```

## API Endpoints

The dashboard provides REST API endpoints for external integration:

- `GET /api/health` - Health check
- `GET /api/stats/overview?period=week` - Overview statistics  
- `GET /api/stats/categories?period=week&limit=25` - Top categories
- `GET /api/stats/senders?period=week&limit=25` - Top senders
- `GET /api/stats/domains?period=week&limit=25` - Top domains
- `GET /api/stats/trends?days=30` - Category trends over time
- `GET /api/stats/processing-runs?limit=50` - Recent processing runs

### API Parameters

- `period`: `day`, `week`, `month` (default: `week`)
- `limit`: Number of results to return (default: 25, max: 100)
- `days`: Number of days for trends (default: 30)

## Dashboard Sections

### 1. Overview Cards
- Total emails processed
- Emails deleted/archived
- Average processing time
- Active categories count

### 2. Categories Tab
- Interactive pie chart of top categories
- List of top 25 categories with counts and percentages
- Category names truncated to 40 characters max

### 3. Senders Tab
- Horizontal bar chart of top senders
- Detailed sender list with email addresses and counts

### 4. Domains Tab
- Bar chart showing email volume by domain
- Domain blocking status (blocked/allowed)
- Visual indicators for blocked domains

### 5. Trends Tab
- Line chart showing category trends over time
- Configurable time periods (7, 30, 90 days)
- Top 7 categories by volume

### 6. Processing Runs
- Table of recent email processing jobs
- Run duration, status, and performance metrics
- Error tracking and debugging information

## File Structure

```
cat-emails/
├── web_dashboard.py              # Main Flask application
├── run_dashboard.py              # Startup script with error checking
├── requirements-web.txt          # Web-specific dependencies
├── templates/                    # Jinja2 templates
│   ├── base.html                # Base template with Bootstrap 5
│   ├── dashboard.html           # Main dashboard page
│   ├── 404.html                 # 404 error page
│   └── 500.html                 # 500 error page
└── static/                       # Static assets
    ├── css/
    │   └── dashboard.css        # Custom CSS styles
    └── js/
        └── dashboard.js         # Dashboard JavaScript logic
```

## Troubleshooting

### Dashboard Won't Start

1. **Check Dependencies**: Run `pip install flask` 
2. **Check Database**: Ensure the database path exists or run email processing first
3. **Check Ports**: Make sure port 5000 isn't already in use

### No Data Showing

1. **Run Email Processing**: The dashboard needs data from `gmail_fetcher.py`
2. **Check Database Path**: Verify `DB_PATH` points to the correct database
3. **Check API Responses**: Open browser dev tools and check for API errors

### Performance Issues

1. **Limit Results**: Use smaller `limit` values in API calls
2. **Reduce Trend Days**: Use fewer days in trends view
3. **Enable Caching**: Install `flask-caching` for better performance

## Development

### Adding New Charts

1. Add new API endpoint in `web_dashboard.py`
2. Create chart rendering function in `dashboard.js`
3. Add HTML container in `dashboard.html`
4. Update CSS styles in `dashboard.css`

### Customizing Appearance

- Modify `static/css/dashboard.css` for custom styles
- Edit `templates/base.html` for layout changes  
- Update Chart.js configuration in `dashboard.js`

### Security Considerations

- Change `SECRET_KEY` in production
- Use HTTPS in production
- Consider adding authentication for sensitive data
- Install `flask-talisman` for security headers

## Production Deployment

### Using Gunicorn

```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web_dashboard:app
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt requirements-web.txt ./
RUN pip install -r requirements.txt -r requirements-web.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "web_dashboard:app"]
```

### Environment Variables for Production

```bash
FLASK_DEBUG=False
SECRET_KEY=your-secure-random-secret-key
DB_PATH=/data/summaries.db
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```