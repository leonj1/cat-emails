"""
Chart generator for email summary reports.
Creates beautiful visualizations for email statistics.
"""
import base64
import io
from typing import Dict, List, Optional, Any
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import pandas as pd

from models.email_summary import DailySummaryReport, CategoryCount, DomainCount


class ChartGenerator:
    """Generate charts for email summary reports."""
    
    def __init__(self):
        """Initialize chart generator with style settings."""
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
        # Default figure settings
        self.fig_dpi = 100
        self.fig_size = (10, 6)
        
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.fig_dpi, bbox_inches='tight')
        buf.seek(0)
        base64_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return base64_str
        
    def generate_category_distribution(self, report: DailySummaryReport) -> str:
        """
        Generate a pie chart of email category distribution.
        
        Args:
            report: Summary report containing category data
            
        Returns:
            Base64 encoded PNG image
        """
        # Get top categories
        categories = report.stats.top_categories[:8]  # Limit to top 8
        
        if not categories:
            return ""
            
        # Prepare data
        labels = [cat.category for cat in categories]
        sizes = [cat.count for cat in categories]
        
        # Calculate "Others" if there are more categories
        total_shown = sum(sizes)
        total_all = report.stats.total_processed
        if total_all > total_shown:
            labels.append("Others")
            sizes.append(total_all - total_shown)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Create pie chart with better styling
        colors = sns.color_palette("husl", len(labels))
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.85,
            explode=[0.05] * len(labels)  # Slightly separate all slices
        )
        
        # Customize text
        for text in texts:
            text.set_fontsize(12)
            text.set_weight('bold')
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')
        
        # Add title
        plt.title(f'Email Category Distribution\n{report.report_type} Report', 
                 fontsize=16, weight='bold', pad=20)
        
        # Equal aspect ratio ensures circular pie
        ax.axis('equal')
        
        return self._fig_to_base64(fig)
        
    def generate_top_senders_chart(self, report: DailySummaryReport, limit: int = 10) -> str:
        """
        Generate a horizontal bar chart of top email senders.
        
        Args:
            report: Summary report containing sender data
            limit: Number of top senders to show
            
        Returns:
            Base64 encoded PNG image
        """
        # Get top senders
        top_senders = report.get_top_senders(limit=limit)
        
        if not top_senders:
            return ""
            
        # Prepare data
        senders = [s['sender'] for s in top_senders]
        counts = [s['count'] for s in top_senders]
        
        # Truncate long sender names
        senders = [s[:40] + '...' if len(s) > 40 else s for s in senders]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, max(6, len(senders) * 0.5)))
        
        # Create horizontal bar chart
        bars = ax.barh(senders, counts)
        
        # Color bars with gradient
        colors = sns.color_palette("viridis", len(bars))
        for bar, color in zip(bars, colors):
            bar.set_color(color)
        
        # Add value labels
        for i, (bar, count) in enumerate(zip(bars, counts)):
            ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height()/2, 
                   f'{count}', ha='left', va='center', fontsize=10, weight='bold')
        
        # Customize
        ax.set_xlabel('Number of Emails', fontsize=12, weight='bold')
        ax.set_title(f'Top {limit} Email Senders\n{report.report_type} Report', 
                    fontsize=16, weight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)
        
        # Adjust layout
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
        
    def generate_daily_volume_chart(self, daily_data: List[Dict[str, Any]]) -> str:
        """
        Generate a line chart showing daily email volume over the past week.
        
        Args:
            daily_data: List of daily email statistics
            
        Returns:
            Base64 encoded PNG image
        """
        if not daily_data:
            return ""
            
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(daily_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.fig_size)
        
        # Plot lines
        ax.plot(df['date'], df['total'], marker='o', linewidth=2.5, 
                markersize=8, label='Total Emails', color='#2E86AB')
        ax.plot(df['date'], df['kept'], marker='s', linewidth=2, 
                markersize=6, label='Kept', color='#48BB78', alpha=0.8)
        ax.plot(df['date'], df['deleted'], marker='^', linewidth=2, 
                markersize=6, label='Archived', color='#F56565', alpha=0.8)
        
        # Fill areas under lines
        ax.fill_between(df['date'], df['kept'], alpha=0.2, color='#48BB78')
        ax.fill_between(df['date'], df['deleted'], alpha=0.2, color='#F56565')
        
        # Customize
        ax.set_xlabel('Date', fontsize=12, weight='bold')
        ax.set_ylabel('Number of Emails', fontsize=12, weight='bold')
        ax.set_title('Daily Email Volume - Past 7 Days', fontsize=16, weight='bold', pad=20)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %d'))
        plt.xticks(rotation=45)
        
        # Add legend
        ax.legend(loc='upper left', frameon=True, shadow=True)
        
        # Grid
        ax.grid(True, alpha=0.3)
        
        # Tight layout
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
        
    def generate_performance_chart(self, performance_data: List[Dict[str, Any]]) -> str:
        """
        Generate a chart showing processing performance over time.
        
        Args:
            performance_data: List of performance metrics over time
            
        Returns:
            Base64 encoded PNG image
        """
        if not performance_data:
            return ""
            
        # Convert to DataFrame
        df = pd.DataFrame(performance_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Plot emails per minute
        ax1.plot(df['timestamp'], df['emails_per_minute'], 
                marker='o', linewidth=2.5, markersize=6, color='#667EEA')
        ax1.fill_between(df['timestamp'], df['emails_per_minute'], alpha=0.3, color='#667EEA')
        ax1.set_ylabel('Emails/Minute', fontsize=12, weight='bold')
        ax1.set_title('Processing Performance Over Time', fontsize=16, weight='bold', pad=20)
        ax1.grid(True, alpha=0.3)
        
        # Plot average processing time
        ax2.plot(df['timestamp'], df['avg_processing_time'], 
                marker='s', linewidth=2.5, markersize=6, color='#F6AD55')
        ax2.fill_between(df['timestamp'], df['avg_processing_time'], alpha=0.3, color='#F6AD55')
        ax2.set_ylabel('Avg Processing Time (seconds)', fontsize=12, weight='bold')
        ax2.set_xlabel('Time', fontsize=12, weight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)
        
        # Tight layout
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
        
    def generate_weekly_comparison_chart(self, current_week: Dict[str, int], 
                                       last_week: Dict[str, int]) -> str:
        """
        Generate a comparison chart between current and last week.
        
        Args:
            current_week: Current week's statistics
            last_week: Last week's statistics
            
        Returns:
            Base64 encoded PNG image
        """
        # Prepare data
        categories = list(current_week.keys())
        current_values = list(current_week.values())
        last_values = list(last_week.values())
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.fig_size)
        
        # Set bar positions
        x = range(len(categories))
        width = 0.35
        
        # Create bars
        bars1 = ax.bar([i - width/2 for i in x], last_values, width, 
                       label='Last Week', color='#A0AEC0', alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], current_values, width, 
                       label='This Week', color='#667EEA')
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(current_values + last_values) * 0.01,
                       f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # Customize
        ax.set_xlabel('Metrics', fontsize=12, weight='bold')
        ax.set_ylabel('Count', fontsize=12, weight='bold')
        ax.set_title('Week-over-Week Comparison', fontsize=16, weight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend(frameon=True, shadow=True)
        ax.grid(axis='y', alpha=0.3)
        
        # Tight layout
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
        
    def generate_domain_charts(self, report: DailySummaryReport) -> Dict[str, str]:
        """
        Generate bar charts for top kept and archived domains.
        
        Args:
            report: Summary report containing domain data
            
        Returns:
            Dictionary with 'kept_domains' and 'archived_domains' charts
        """
        charts = {}
        
        # Generate kept domains chart
        if report.stats.top_kept_domains:
            try:
                charts['kept_domains'] = self._generate_domain_chart(
                    report.stats.top_kept_domains,
                    "Top 10 Kept Domains",
                    "#48BB78"  # Green color for kept
                )
            except Exception as e:
                print(f"Error generating kept domains chart: {e}")
        
        # Generate archived domains chart
        if report.stats.top_archived_domains:
            try:
                charts['archived_domains'] = self._generate_domain_chart(
                    report.stats.top_archived_domains,
                    "Top 10 Archived Domains",
                    "#F56565"  # Red color for archived
                )
            except Exception as e:
                print(f"Error generating archived domains chart: {e}")
                
        return charts
    
    def _generate_domain_chart(self, domains: List[DomainCount], title: str, color: str) -> str:
        """
        Generate a horizontal bar chart for domain statistics.
        
        Args:
            domains: List of DomainCount objects
            title: Chart title
            color: Bar color
            
        Returns:
            Base64 encoded PNG image
        """
        if not domains:
            return ""
            
        # Prepare data
        domain_names = [d.domain for d in domains]
        counts = [d.count for d in domains]
        
        # Truncate long domain names
        domain_names = [d[:35] + '...' if len(d) > 35 else d for d in domain_names]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, max(6, len(domains) * 0.5)))
        
        # Create horizontal bar chart
        bars = ax.barh(domain_names, counts, color=color, alpha=0.8)
        
        # Add value labels
        for bar, count, domain in zip(bars, counts, domains):
            # Add count
            ax.text(bar.get_width() + max(counts) * 0.01, bar.get_y() + bar.get_height()/2, 
                   f'{count} ({domain.percentage}%)', 
                   ha='left', va='center', fontsize=10, weight='bold')
        
        # Customize
        ax.set_xlabel('Number of Emails', fontsize=12, weight='bold')
        ax.set_title(title, fontsize=16, weight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)
        
        # Invert y-axis to show highest at top
        ax.invert_yaxis()
        
        # Adjust layout
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
        
    def generate_all_charts(self, report: DailySummaryReport, 
                          performance_metrics: Optional[Dict[str, Any]] = None,
                          weekly_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Generate all relevant charts for the report.
        
        Args:
            report: Summary report
            performance_metrics: Performance metrics
            weekly_data: Weekly comparison data
            
        Returns:
            Dictionary of chart_name -> base64_image
        """
        charts = {}
        
        try:
            # Category distribution chart
            charts['category_distribution'] = self.generate_category_distribution(report)
        except Exception as e:
            print(f"Error generating category distribution chart: {e}")
            
        try:
            # Top senders chart
            charts['top_senders'] = self.generate_top_senders_chart(report)
        except Exception as e:
            print(f"Error generating top senders chart: {e}")
            
        try:
            # Domain charts
            domain_charts = self.generate_domain_charts(report)
            charts.update(domain_charts)
        except Exception as e:
            print(f"Error generating domain charts: {e}")
            
        # Additional charts for weekly reports
        if report.report_type == "Weekly" and weekly_data:
            try:
                if 'daily_volumes' in weekly_data:
                    charts['daily_volume'] = self.generate_daily_volume_chart(
                        weekly_data['daily_volumes']
                    )
            except Exception as e:
                print(f"Error generating daily volume chart: {e}")
                
            try:
                if 'comparison' in weekly_data:
                    charts['weekly_comparison'] = self.generate_weekly_comparison_chart(
                        weekly_data['comparison']['current'],
                        weekly_data['comparison']['previous']
                    )
            except Exception as e:
                print(f"Error generating weekly comparison chart: {e}")
        
        # Performance chart if metrics available
        if performance_metrics and 'history' in performance_metrics:
            try:
                charts['performance'] = self.generate_performance_chart(
                    performance_metrics['history']
                )
            except Exception as e:
                print(f"Error generating performance chart: {e}")
        
        return charts