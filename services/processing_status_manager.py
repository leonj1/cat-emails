"""
Processing status manager for thread-safe email processing status tracking

Example usage in Cat-Emails project:

    from services.processing_status_manager import ProcessingStatusManager, ProcessingState
    
    # Initialize manager (typically as a singleton)
    status_manager = ProcessingStatusManager()
    
    try:
        # Start processing session
        status_manager.start_processing('user@example.com')
        
        # Update status throughout email processing workflow
        status_manager.update_status(ProcessingState.CONNECTING, 'Connecting to Gmail IMAP')
        status_manager.update_status(ProcessingState.FETCHING, 'Fetching emails', {'current': 50, 'total': 100})
        status_manager.update_status(ProcessingState.PROCESSING, 'Processing email content')
        status_manager.update_status(ProcessingState.CATEGORIZING, 'Categorizing with AI')
        status_manager.update_status(ProcessingState.LABELING, 'Applying Gmail labels')
        
        # Complete processing
        status_manager.complete_processing()
        
    except Exception as e:
        # Handle errors
        status_manager.update_status(ProcessingState.ERROR, 'Processing failed', error_message=str(e))
        status_manager.complete_processing()
    
    # Check current status (from another thread/API endpoint)
    current_status = status_manager.get_current_status()
    recent_runs = status_manager.get_recent_runs(limit=10)
    stats = status_manager.get_statistics()
"""
import logging
import threading
from datetime import datetime, timezone
from enum import Enum, auto
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from collections import deque


class ProcessingState(Enum):
    """Email processing state enumeration"""
    IDLE = auto()
    CONNECTING = auto()
    FETCHING = auto()
    PROCESSING = auto()
    CATEGORIZING = auto()
    LABELING = auto()
    COMPLETED = auto()
    ERROR = auto()


@dataclass
class AccountStatus:
    """Account processing status information"""
    email_address: str
    state: ProcessingState
    current_step: str
    progress: Optional[Dict[str, Any]] = None
    start_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = asdict(self)
        # Convert enum to string for JSON serialization
        result['state'] = self.state.name
        # Convert datetime objects to ISO format
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.last_updated:
            result['last_updated'] = self.last_updated.isoformat()
        return result


class ProcessingStatusManager:
    """
    Thread-safe manager for email processing status tracking.
    
    This class provides centralized status tracking for email processing operations,
    ensuring thread-safe access to processing state information and maintaining
    a history of recent processing runs.
    """
    
    def __init__(self, max_history: int = 50):
        """
        Initialize the processing status manager.
        
        Args:
            max_history: Maximum number of recent runs to keep in history
        """
        self._lock = threading.RLock()
        self._current_status: Optional[AccountStatus] = None
        self._recent_runs: deque = deque(maxlen=max_history)
        self._max_history = max_history
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"ProcessingStatusManager initialized with max_history={max_history}")
    
    def start_processing(self, email_address: str) -> None:
        """
        Start processing for a specific email account.
        
        Args:
            email_address: The email address being processed
            
        Raises:
            ValueError: If processing is already active for another account
        """
        with self._lock:
            if self._current_status is not None:
                raise ValueError(
                    f"Processing already active for {self._current_status.email_address}. "
                    f"Current state: {self._current_status.state.name}"
                )
            
            now = datetime.now(timezone.utc)
            self._current_status = AccountStatus(
                email_address=email_address,
                state=ProcessingState.IDLE,
                current_step="Initializing processing",
                start_time=now,
                last_updated=now
            )
            
            self.logger.info(f"Started processing for account: {email_address}")
    
    def update_status(
        self,
        state: ProcessingState,
        step: str,
        progress: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update the current processing status.
        
        Args:
            state: New processing state
            step: Description of the current processing step
            progress: Optional progress information (e.g., {'current': 5, 'total': 10})
            error_message: Optional error message if state is ERROR
            
        Raises:
            RuntimeError: If no processing session is active
        """
        with self._lock:
            if not self._current_status:
                raise RuntimeError("No active processing session to update")
            
            self._current_status.state = state
            self._current_status.current_step = step
            self._current_status.progress = progress
            self._current_status.error_message = error_message
            self._current_status.last_updated = datetime.now(timezone.utc)
            
            # Log status updates
            progress_str = ""
            if progress and 'current' in progress and 'total' in progress:
                progress_str = f" ({progress['current']}/{progress['total']})"
            
            if state == ProcessingState.ERROR:
                self.logger.error(
                    f"Processing error for {self._current_status.email_address}: {step}{progress_str} - {error_message}"
                )
            else:
                self.logger.info(
                    f"Processing update for {self._current_status.email_address}: {state.name} - {step}{progress_str}"
                )
    
    def complete_processing(self) -> None:
        """
        Complete the current processing session and archive it to history.
        
        The current status is moved to the recent runs history and reset.
        """
        with self._lock:
            if not self._current_status:
                self.logger.warning("Attempted to complete processing, but no session is active")
                return
            
            # Calculate duration
            duration_seconds = None
            if self._current_status.start_time and self._current_status.last_updated:
                duration = self._current_status.last_updated - self._current_status.start_time
                duration_seconds = duration.total_seconds()
            
            # Mark as completed if not already in error state
            if self._current_status.state != ProcessingState.ERROR:
                self._current_status.state = ProcessingState.COMPLETED
                self._current_status.current_step = "Processing completed"
                self._current_status.last_updated = datetime.now(timezone.utc)
            
            # Create archived run record
            archived_run = {
                'email_address': self._current_status.email_address,
                'start_time': self._current_status.start_time.isoformat() if self._current_status.start_time else None,
                'end_time': self._current_status.last_updated.isoformat() if self._current_status.last_updated else None,
                'duration_seconds': duration_seconds,
                'final_state': self._current_status.state.name,
                'final_step': self._current_status.current_step,
                'error_message': self._current_status.error_message,
                'final_progress': self._current_status.progress
            }
            
            # Add to history
            self._recent_runs.append(archived_run)
            
            self.logger.info(
                f"Completed processing for {self._current_status.email_address} "
                f"in {duration_seconds:.2f} seconds" if duration_seconds else "Completed processing"
            )
            
            # Reset current status
            self._current_status = None
    
    def get_current_status(self) -> Optional[Dict[str, Any]]:
        """
        Get the current processing status.
        
        Returns:
            Dictionary representation of current status, or None if no processing is active
        """
        with self._lock:
            if not self._current_status:
                return None
            
            return self._current_status.to_dict()
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent processing runs from history.
        
        Args:
            limit: Maximum number of recent runs to return
            
        Returns:
            List of recent processing runs, most recent first
        """
        with self._lock:
            # Convert deque to list and reverse to get most recent first
            recent_list = list(self._recent_runs)
            recent_list.reverse()
            
            # Apply limit
            if limit > 0:
                recent_list = recent_list[:limit]
            
            return recent_list
    
    def is_processing(self) -> bool:
        """
        Check if processing is currently active.
        
        Returns:
            True if processing is active, False otherwise
        """
        with self._lock:
            return self._current_status is not None
    
    def get_processing_email(self) -> Optional[str]:
        """
        Get the email address currently being processed.
        
        Returns:
            Email address if processing is active, None otherwise
        """
        with self._lock:
            if self._current_status:
                return self._current_status.email_address
            return None
    
    def clear_history(self) -> None:
        """Clear the processing history."""
        with self._lock:
            self._recent_runs.clear()
            self.logger.info("Processing history cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics from recent runs.
        
        Returns:
            Dictionary containing statistics about recent processing runs
        """
        with self._lock:
            runs = list(self._recent_runs)
            
            if not runs:
                return {
                    'total_runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'average_duration_seconds': 0,
                    'success_rate': 0.0
                }
            
            successful = sum(1 for run in runs if run['final_state'] == 'COMPLETED')
            failed = sum(1 for run in runs if run['final_state'] == 'ERROR')
            
            # Calculate average duration for runs that have duration data
            durations = [run['duration_seconds'] for run in runs if run['duration_seconds'] is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_runs': len(runs),
                'successful_runs': successful,
                'failed_runs': failed,
                'average_duration_seconds': avg_duration,
                'success_rate': (successful / len(runs)) * 100 if runs else 0.0
            }
    
    def __str__(self) -> str:
        """String representation of the processing status manager."""
        with self._lock:
            if self._current_status:
                return f"ProcessingStatusManager(active: {self._current_status.email_address}, state: {self._current_status.state.name})"
            else:
                return f"ProcessingStatusManager(idle, history: {len(self._recent_runs)} runs)"
    
    def __repr__(self) -> str:
        """Detailed representation of the processing status manager."""
        return self.__str__()