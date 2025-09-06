# Real-Time Email Processing Status - Technical Specification

## Overview

This specification outlines the implementation of a real-time status system that allows the web frontend to monitor which email accounts are currently being processed by the FastAPI background service. The system will provide live updates on processing state, progress, and completion status.

## Current Architecture Analysis

### Background Processing (api_service.py)
- **Background Thread**: `background_gmail_processor()` runs continuously in a separate thread
- **Processing Cycle**: Every 5 minutes (configurable via `BACKGROUND_SCAN_INTERVAL`)
- **Account Processing**: Sequential processing of accounts from database
- **Current Logging**: Console logging only, no real-time status tracking

### Web Dashboard (web_dashboard.py)
- **Flask-based**: Serves static dashboard with API endpoints
- **Current APIs**: Statistics, categories, trends, health checks
- **No Real-time Updates**: Currently static data only

## Requirements

### Functional Requirements
1. **Real-time Status Visibility**: Frontend must show current processing state
2. **Account-specific Tracking**: Display which email account is being processed
3. **Progress Indicators**: Show processing progress within each account
4. **Historical Status**: Track recent processing runs and their outcomes
5. **WebSocket Communication**: Real-time updates without polling
6. **Error Handling**: Display processing errors and failures

### Non-Functional Requirements
1. **Performance**: Minimal impact on existing email processing performance
2. **Reliability**: Status updates should not crash main processing
3. **Scalability**: Support multiple simultaneous account processing (future)
4. **Security**: Status information should respect API key authentication

## Technical Design

### 1. Shared State Management

#### ProcessingStatusManager Class
```python
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import threading
import json

class ProcessingState(Enum):
    IDLE = "idle"
    CONNECTING = "connecting" 
    FETCHING = "fetching"
    PROCESSING = "processing"
    CATEGORIZING = "categorizing"
    LABELING = "labeling"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AccountStatus:
    email_address: str
    state: ProcessingState
    current_step: str
    progress: Optional[Dict[str, int]] = None  # {"current": 5, "total": 20}
    start_time: Optional[datetime] = None
    last_updated: datetime = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['state'] = self.state.value
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.last_updated:
            result['last_updated'] = self.last_updated.isoformat()
        return result

class ProcessingStatusManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._current_status: Optional[AccountStatus] = None
        self._recent_runs: List[AccountStatus] = []
        self._max_history = 50
        
    def start_processing(self, email_address: str) -> None:
        with self._lock:
            self._current_status = AccountStatus(
                email_address=email_address,
                state=ProcessingState.CONNECTING,
                current_step="Initializing connection to Gmail",
                start_time=datetime.now(),
                last_updated=datetime.now()
            )
    
    def update_status(self, state: ProcessingState, step: str, 
                     progress: Optional[Dict[str, int]] = None,
                     error_message: Optional[str] = None) -> None:
        with self._lock:
            if self._current_status:
                self._current_status.state = state
                self._current_status.current_step = step
                self._current_status.progress = progress
                self._current_status.last_updated = datetime.now()
                if error_message:
                    self._current_status.error_message = error_message
    
    def complete_processing(self) -> None:
        with self._lock:
            if self._current_status:
                self._current_status.state = ProcessingState.COMPLETED
                self._current_status.last_updated = datetime.now()
                # Archive to recent runs
                self._recent_runs.append(self._current_status)
                if len(self._recent_runs) > self._max_history:
                    self._recent_runs.pop(0)
                self._current_status = None
    
    def get_current_status(self) -> Optional[Dict]:
        with self._lock:
            return self._current_status.to_dict() if self._current_status else None
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        with self._lock:
            return [run.to_dict() for run in self._recent_runs[-limit:]]
```

### 2. Background Processing Integration

#### Modified api_service.py Integration
```python
# Global status manager
processing_status = ProcessingStatusManager()

def process_account_emails(email_address: str) -> Dict:
    """Enhanced version with real-time status updates"""
    processing_status.start_processing(email_address)
    
    try:
        processing_status.update_status(
            ProcessingState.CONNECTING,
            f"Connecting to Gmail IMAP for {email_address}"
        )
        
        # Simulate connection time
        time.sleep(1)
        
        processing_status.update_status(
            ProcessingState.FETCHING,
            f"Fetching emails from last {BACKGROUND_PROCESS_HOURS} hours"
        )
        
        # Simulate email fetching
        time.sleep(2)
        simulated_email_count = 15
        
        processing_status.update_status(
            ProcessingState.PROCESSING,
            f"Found {simulated_email_count} emails to process",
            progress={"current": 0, "total": simulated_email_count}
        )
        
        # Process each email with progress updates
        for i in range(simulated_email_count):
            processing_status.update_status(
                ProcessingState.CATEGORIZING,
                f"Categorizing email {i+1}/{simulated_email_count}",
                progress={"current": i+1, "total": simulated_email_count}
            )
            
            time.sleep(0.5)  # AI categorization
            
            processing_status.update_status(
                ProcessingState.LABELING,
                f"Applying Gmail labels {i+1}/{simulated_email_count}",
                progress={"current": i+1, "total": simulated_email_count}
            )
            
            time.sleep(0.2)  # Gmail API call
        
        result = {
            "account": email_address,
            "emails_processed": simulated_email_count,
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
        
        processing_status.complete_processing()
        return result
        
    except Exception as e:
        processing_status.update_status(
            ProcessingState.ERROR,
            f"Error processing {email_address}",
            error_message=str(e)
        )
        processing_status.complete_processing()
        raise
```

### 3. WebSocket Implementation

#### WebSocket Handler (websocket_handler.py)
```python
import asyncio
import json
import logging
from typing import Set
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

class StatusWebSocketManager:
    def __init__(self, status_manager: ProcessingStatusManager):
        self.status_manager = status_manager
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.broadcast_task = None
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        logger.info(f"New WebSocket client connected. Total clients: {len(self.clients)}")
        
        # Send current status immediately
        current_status = self.status_manager.get_current_status()
        if current_status:
            await self.send_to_client(websocket, {
                "type": "status_update",
                "data": current_status
            })
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.clients)}")
    
    async def send_to_client(self, websocket: websockets.WebSocketServerProtocol, message: dict):
        """Send message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except ConnectionClosed:
            await self.unregister_client(websocket)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
    
    async def broadcast_status(self):
        """Broadcast current status to all connected clients"""
        if not self.clients:
            return
            
        current_status = self.status_manager.get_current_status()
        message = {
            "type": "status_update",
            "data": current_status,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all clients
        disconnected_clients = set()
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message))
            except ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)
    
    async def start_broadcasting(self):
        """Start the background broadcasting task"""
        while True:
            try:
                await self.broadcast_status()
                await asyncio.sleep(2)  # Broadcast every 2 seconds
            except Exception as e:
                logger.error(f"Error in broadcasting loop: {e}")
                await asyncio.sleep(5)
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle a new WebSocket client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                # Handle incoming messages from clients if needed
                try:
                    data = json.loads(message)
                    if data.get("type") == "get_recent_runs":
                        recent_runs = self.status_manager.get_recent_runs(limit=10)
                        await self.send_to_client(websocket, {
                            "type": "recent_runs",
                            "data": recent_runs
                        })
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message from client: {message}")
        except ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)

# Global WebSocket manager instance
ws_manager = None

def init_websocket_manager(status_manager: ProcessingStatusManager):
    global ws_manager
    ws_manager = StatusWebSocketManager(status_manager)
    return ws_manager
```

### 4. FastAPI WebSocket Integration

#### Enhanced api_service.py
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio

# Initialize WebSocket manager
from websocket_handler import init_websocket_manager
ws_manager = init_websocket_manager(processing_status)

@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates"""
    await websocket.accept()
    await ws_manager.register_client(websocket)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.ping()
    except WebSocketDisconnect:
        await ws_manager.unregister_client(websocket)

@app.on_event("startup")
async def startup_event():
    """Start WebSocket broadcasting on app startup"""
    if ws_manager:
        asyncio.create_task(ws_manager.start_broadcasting())

# Enhanced status API endpoint
@app.get("/api/processing/current-status")
async def get_current_processing_status():
    """Get current processing status via REST API"""
    current = processing_status.get_current_status()
    recent = processing_status.get_recent_runs(5)
    
    return {
        "current_processing": current,
        "recent_runs": recent,
        "timestamp": datetime.now().isoformat()
    }
```

### 5. Frontend Implementation

#### WebSocket Client (dashboard.html)
```javascript
class ProcessingStatusClient {
    constructor() {
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.statusContainer = document.getElementById('processing-status');
        
        this.connect();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/status`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.showConnectionStatus('Connected', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket disconnected');
                this.showConnectionStatus('Disconnected', 'error');
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.showConnectionStatus('Error', 'error');
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.attemptReconnect();
        }
    }
    
    handleMessage(message) {
        switch (message.type) {
            case 'status_update':
                this.updateProcessingStatus(message.data);
                break;
            case 'recent_runs':
                this.updateRecentRuns(message.data);
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }
    
    updateProcessingStatus(status) {
        const container = this.statusContainer;
        
        if (!status) {
            // No active processing
            container.innerHTML = `
                <div class="status-idle">
                    <div class="status-indicator idle"></div>
                    <div class="status-text">
                        <h4>Email Processing Status</h4>
                        <p>System is idle - waiting for next scan cycle</p>
                    </div>
                </div>
            `;
            return;
        }
        
        const progressBar = status.progress ? 
            `<div class="progress">
                <div class="progress-bar" style="width: ${(status.progress.current / status.progress.total) * 100}%"></div>
                <span class="progress-text">${status.progress.current}/${status.progress.total}</span>
            </div>` : '';
        
        const errorMessage = status.error_message ? 
            `<div class="error-message">Error: ${status.error_message}</div>` : '';
        
        container.innerHTML = `
            <div class="status-active">
                <div class="status-indicator ${status.state}"></div>
                <div class="status-content">
                    <h4>Processing: ${status.email_address}</h4>
                    <p class="current-step">${status.current_step}</p>
                    ${progressBar}
                    ${errorMessage}
                    <small>Started: ${new Date(status.start_time).toLocaleTimeString()}</small>
                </div>
            </div>
        `;
    }
    
    showConnectionStatus(status, type) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            statusEl.className = `connection-status ${type}`;
            statusEl.textContent = `WebSocket: ${status}`;
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.showConnectionStatus('Failed to reconnect', 'error');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
    
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const statusClient = new ProcessingStatusClient();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        statusClient.disconnect();
    });
});
```

#### CSS Styles for Status Display
```css
.processing-status {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
    margin-bottom: 20px;
}

.status-idle {
    display: flex;
    align-items: center;
    gap: 15px;
}

.status-active {
    display: flex;
    align-items: flex-start;
    gap: 15px;
}

.status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-top: 4px;
}

.status-indicator.idle { background-color: #6c757d; }
.status-indicator.connecting { background-color: #ffc107; animation: pulse 2s infinite; }
.status-indicator.fetching { background-color: #17a2b8; animation: pulse 2s infinite; }
.status-indicator.processing { background-color: #007bff; animation: pulse 1s infinite; }
.status-indicator.categorizing { background-color: #28a745; animation: pulse 1s infinite; }
.status-indicator.labeling { background-color: #28a745; animation: pulse 1s infinite; }
.status-indicator.completed { background-color: #28a745; }
.status-indicator.error { background-color: #dc3545; animation: pulse 1s infinite; }

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

.status-content h4 {
    margin: 0 0 8px 0;
    color: #333;
    font-size: 16px;
}

.current-step {
    margin: 0 0 12px 0;
    color: #666;
    font-size: 14px;
}

.progress {
    background-color: #e9ecef;
    border-radius: 4px;
    height: 20px;
    position: relative;
    margin-bottom: 8px;
}

.progress-bar {
    background-color: #007bff;
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}

.progress-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #333;
    font-size: 12px;
    font-weight: bold;
}

.error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 8px;
    font-size: 14px;
}

.connection-status {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 1000;
}

.connection-status.success {
    background-color: #d4edda;
    color: #155724;
}

.connection-status.error {
    background-color: #f8d7da;
    color: #721c24;
}
```

## Implementation Plan

### Phase 1: Core Status Management
1. Create `ProcessingStatusManager` class
2. Create basic data models for status tracking
3. Add unit tests for status management

### Phase 2: Background Processing Integration
1. Modify `process_account_emails()` function
2. Add status update calls throughout processing flow
3. Test status updates during processing

### Phase 3: WebSocket Infrastructure
1. Implement WebSocket handler class
2. Add WebSocket endpoint to FastAPI
3. Add REST API endpoint for status polling fallback

### Phase 4: Frontend Implementation
1. Create WebSocket client JavaScript
2. Add status display UI components
3. Add CSS styling for status indicators

### Phase 5: Testing & Polish
1. End-to-end testing with real email processing
2. Error handling and edge case testing
3. Performance optimization
4. Documentation updates

## Database Schema Changes

### New Table: processing_runs
```sql
CREATE TABLE processing_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_address TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    state TEXT NOT NULL,  -- idle, connecting, fetching, processing, etc.
    emails_found INTEGER DEFAULT 0,
    emails_processed INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processing_runs_email ON processing_runs(email_address);
CREATE INDEX idx_processing_runs_start_time ON processing_runs(start_time);
```

## Security Considerations

1. **API Key Protection**: WebSocket connections should validate API keys
2. **Rate Limiting**: Prevent WebSocket connection spam
3. **Data Sanitization**: Ensure status messages don't expose sensitive email content
4. **Connection Limits**: Limit concurrent WebSocket connections per client

## Performance Considerations

1. **Broadcasting Frequency**: 2-second intervals to balance real-time feel with performance
2. **Client Limit**: Maximum 50 concurrent WebSocket connections
3. **Memory Usage**: Limit status history to 50 recent runs
4. **Thread Safety**: Use proper locking for shared status data

## Error Handling

1. **WebSocket Disconnections**: Automatic reconnection with exponential backoff
2. **Processing Errors**: Graceful error state handling and user notification
3. **Network Issues**: Fallback to REST API polling if WebSocket fails
4. **Data Persistence**: Status survives application restarts via database

## Future Enhancements

1. **Multiple Account Processing**: Support for parallel account processing
2. **Historical Analytics**: Detailed processing performance metrics
3. **Mobile Support**: Responsive design for mobile devices
4. **Push Notifications**: Browser notifications for processing completion
5. **Admin Controls**: Ability to pause/resume processing from UI

---

This specification provides a comprehensive foundation for implementing real-time email processing status updates while maintaining system performance and reliability.