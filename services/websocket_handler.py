#!/usr/bin/env python3
"""
WebSocket handler for real-time client communication in Cat-Emails project.

This module provides the StatusWebSocketManager class for managing WebSocket
connections and broadcasting real-time status updates to connected clients.

Example usage:
    from services.processing_status_manager import ProcessingStatusManager
    from services.websocket_handler import StatusWebSocketManager
    
    # Initialize with status manager
    status_manager = ProcessingStatusManager()
    ws_manager = StatusWebSocketManager(status_manager)
    
    # Use with FastAPI WebSocket endpoint
    @app.websocket("/ws/status")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.handle_client(websocket)
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

try:
    from fastapi import WebSocket, WebSocketDisconnect
except ImportError:
    # Fallback for type hints if FastAPI not available
    WebSocket = Any
    WebSocketDisconnect = Exception

from services.processing_status_manager import ProcessingStatusManager

logger = logging.getLogger(__name__)


class ConnectionLimitExceeded(Exception):
    """Exception raised when maximum connection limit is exceeded."""
    pass


class StatusWebSocketManager:
    """
    WebSocket manager for real-time email processing status updates.
    
    This class manages WebSocket client connections, handles message broadcasting,
    and provides real-time updates about email processing status to connected clients.
    
    Features:
    - Client connection management with automatic cleanup
    - Real-time status broadcasting
    - Message handling for client requests
    - Connection limits and rate limiting
    - Comprehensive error handling
    - Integration with ProcessingStatusManager
    """
    
    # Configuration constants
    MAX_CLIENTS = 50
    BROADCAST_INTERVAL = 2.0  # seconds
    CLIENT_TIMEOUT = 30.0  # seconds
    MAX_MESSAGE_SIZE = 8192  # bytes
    HEARTBEAT_INTERVAL = 30.0  # seconds
    
    def __init__(self, status_manager: ProcessingStatusManager, max_clients: int = None):
        """
        Initialize the WebSocket manager.
        
        Args:
            status_manager: ProcessingStatusManager instance for status data
            max_clients: Maximum number of concurrent connections (default: 50)
        """
        self.status_manager = status_manager
        self.max_clients = max_clients or self.MAX_CLIENTS
        
        # Client management
        self.clients: Set[WebSocket] = set()
        self.client_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Background task management
        self.broadcast_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.is_broadcasting = False
        self.is_shutdown = False
        
        # Statistics
        self.total_connections = 0
        self.messages_sent = 0
        self.broadcast_errors = 0
        
        logger.info(f"StatusWebSocketManager initialized with max_clients={self.max_clients}")
    
    async def register_client(self, websocket: WebSocket) -> None:
        """
        Register a new WebSocket client.
        
        Args:
            websocket: WebSocket connection to register
            
        Raises:
            ConnectionLimitExceeded: If maximum client limit is reached
        """
        if len(self.clients) >= self.max_clients:
            logger.warning(f"Connection limit exceeded. Current: {len(self.clients)}, Max: {self.max_clients}")
            raise ConnectionLimitExceeded(f"Maximum {self.max_clients} clients allowed")
        
        # Add client to active set
        self.clients.add(websocket)
        self.client_metadata[websocket] = {
            'connected_at': datetime.now(timezone.utc),
            'messages_sent': 0,
            'last_ping': None,
            'user_agent': getattr(websocket, 'headers', {}).get('user-agent', 'Unknown')
        }
        
        self.total_connections += 1
        
        logger.info(f"New WebSocket client registered. Total clients: {len(self.clients)}")
        
        # Send current status immediately upon connection
        await self._send_initial_data(websocket)
    
    async def unregister_client(self, websocket: WebSocket) -> None:
        """
        Unregister a WebSocket client and clean up resources.
        
        Args:
            websocket: WebSocket connection to unregister
        """
        if websocket in self.clients:
            self.clients.discard(websocket)
            
            # Clean up metadata
            client_info = self.client_metadata.pop(websocket, {})
            connected_at = client_info.get('connected_at')
            if connected_at:
                duration = datetime.now(timezone.utc) - connected_at
                logger.info(f"Client disconnected after {duration.total_seconds():.1f}s. "
                           f"Total clients: {len(self.clients)}")
            else:
                logger.info(f"WebSocket client unregistered. Total clients: {len(self.clients)}")
    
    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific WebSocket client.
        
        Args:
            websocket: Target WebSocket connection
            message: Message dictionary to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            # Validate message size
            json_str = json.dumps(message)
            if len(json_str.encode('utf-8')) > self.MAX_MESSAGE_SIZE:
                logger.warning(f"Message too large ({len(json_str)} chars), truncating")
                message = {'type': 'error', 'message': 'Message too large'}
                json_str = json.dumps(message)
            
            # Send message
            await asyncio.wait_for(
                websocket.send_text(json_str),
                timeout=self.CLIENT_TIMEOUT
            )
            
            # Update statistics
            if websocket in self.client_metadata:
                self.client_metadata[websocket]['messages_sent'] += 1
            self.messages_sent += 1
            
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending message to client")
            await self.unregister_client(websocket)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            await self.unregister_client(websocket)
            return False
    
    async def broadcast_status(self) -> None:
        """
        Broadcast current processing status to all connected clients.
        
        This method sends the current processing status and relevant statistics
        to all connected WebSocket clients.
        """
        if not self.clients or self.is_shutdown:
            return
        
        try:
            # Get current status and statistics
            current_status = self.status_manager.get_current_status()
            recent_runs = self.status_manager.get_recent_runs(limit=5)
            statistics = self.status_manager.get_statistics()
            
            # Prepare broadcast message
            message = {
                "type": "status_update",
                "data": {
                    "current_processing": current_status,
                    "recent_runs": recent_runs,
                    "statistics": statistics,
                    "client_count": len(self.clients)
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_time": time.time()
            }
            
            # Broadcast to all clients
            disconnected_clients = set()
            successful_sends = 0
            
            for client in self.clients.copy():
                try:
                    success = await self.send_to_client(client, message)
                    if success:
                        successful_sends += 1
                    else:
                        disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"Unexpected error broadcasting to client: {e}")
                    disconnected_clients.add(client)
            
            # Clean up disconnected clients
            for client in disconnected_clients:
                await self.unregister_client(client)
            
            # Log broadcast statistics
            if disconnected_clients:
                self.broadcast_errors += len(disconnected_clients)
                logger.debug(f"Broadcast completed: {successful_sends} successful, {len(disconnected_clients)} failed")
            
        except Exception as e:
            logger.error(f"Error in broadcast_status: {e}")
            self.broadcast_errors += 1
    
    async def handle_client_message(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """
        Handle incoming messages from WebSocket clients.
        
        Args:
            websocket: WebSocket connection that sent the message
            message: Parsed message dictionary
        """
        try:
            message_type = message.get("type")
            
            if message_type == "get_recent_runs":
                # Send recent processing runs
                limit = message.get("limit", 10)
                limit = max(1, min(100, limit))  # Clamp between 1 and 100
                
                recent_runs = self.status_manager.get_recent_runs(limit=limit)
                response = {
                    "type": "recent_runs",
                    "data": recent_runs,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_to_client(websocket, response)
                
            elif message_type == "get_statistics":
                # Send processing statistics
                statistics = self.status_manager.get_statistics()
                response = {
                    "type": "statistics",
                    "data": statistics,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_to_client(websocket, response)
                
            elif message_type == "ping":
                # Respond to ping with pong
                if websocket in self.client_metadata:
                    self.client_metadata[websocket]['last_ping'] = datetime.now(timezone.utc)
                
                response = {
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "server_time": time.time()
                }
                await self.send_to_client(websocket, response)
                
            elif message_type == "get_current_status":
                # Send current processing status
                current_status = self.status_manager.get_current_status()
                response = {
                    "type": "current_status",
                    "data": current_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_to_client(websocket, response)
                
            else:
                logger.warning(f"Unknown message type from client: {message_type}")
                error_response = {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_to_client(websocket, error_response)
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            error_response = {
                "type": "error", 
                "message": "Internal server error processing message",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self.send_to_client(websocket, error_response)
    
    async def _send_initial_data(self, websocket: WebSocket) -> None:
        """
        Send initial data to a newly connected client.
        
        Args:
            websocket: Newly connected WebSocket client
        """
        try:
            # Send connection confirmation
            welcome_message = {
                "type": "connection_confirmed",
                "message": "Connected to Cat-Emails status updates",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_version": "1.0.0"
            }
            await self.send_to_client(websocket, welcome_message)
            
            # Send current status immediately
            current_status = self.status_manager.get_current_status()
            if current_status:
                status_message = {
                    "type": "status_update",
                    "data": {
                        "current_processing": current_status,
                        "recent_runs": self.status_manager.get_recent_runs(limit=3),
                        "statistics": self.status_manager.get_statistics()
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_to_client(websocket, status_message)
            
        except Exception as e:
            logger.error(f"Error sending initial data to client: {e}")
    
    async def start_broadcasting(self) -> None:
        """
        Start the background broadcasting task.
        
        This method runs continuously and broadcasts status updates to all
        connected clients at regular intervals.
        """
        if self.is_broadcasting:
            logger.warning("Broadcasting is already active")
            return
        
        self.is_broadcasting = True
        logger.info(f"Starting WebSocket broadcasting (interval: {self.BROADCAST_INTERVAL}s)")
        
        try:
            while not self.is_shutdown:
                try:
                    await self.broadcast_status()
                    await asyncio.sleep(self.BROADCAST_INTERVAL)
                except asyncio.CancelledError:
                    logger.info("Broadcasting task was cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in broadcasting loop: {e}")
                    await asyncio.sleep(5.0)  # Wait before retrying
        finally:
            self.is_broadcasting = False
            logger.info("WebSocket broadcasting stopped")
    
    async def start_heartbeat(self) -> None:
        """
        Start the heartbeat task to maintain connections.
        
        This sends periodic ping messages to detect and clean up stale connections.
        """
        logger.info(f"Starting WebSocket heartbeat (interval: {self.HEARTBEAT_INTERVAL}s)")
        
        try:
            while not self.is_shutdown:
                try:
                    # Send heartbeat to all clients
                    if self.clients:
                        heartbeat_message = {
                            "type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "active_clients": len(self.clients)
                        }
                        
                        disconnected = set()
                        for client in self.clients.copy():
                            try:
                                success = await self.send_to_client(client, heartbeat_message)
                                if not success:
                                    disconnected.add(client)
                            except Exception:
                                disconnected.add(client)
                        
                        # Clean up disconnected clients
                        for client in disconnected:
                            await self.unregister_client(client)
                    
                    await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                    
                except asyncio.CancelledError:
                    logger.info("Heartbeat task was cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in heartbeat loop: {e}")
                    await asyncio.sleep(10.0)
        finally:
            logger.info("WebSocket heartbeat stopped")
    
    async def handle_client(self, websocket: WebSocket) -> None:
        """
        Handle a WebSocket client connection lifecycle.
        
        This method manages the complete lifecycle of a WebSocket connection,
        including registration, message handling, and cleanup.
        
        Args:
            websocket: WebSocket connection to handle
            
        Raises:
            ConnectionLimitExceeded: If maximum client limit is exceeded
        """
        client_id = f"{websocket.client.host}:{websocket.client.port}" if hasattr(websocket, 'client') else "unknown"
        logger.info(f"New WebSocket connection from {client_id}")
        
        try:
            # Accept the WebSocket connection
            await websocket.accept()
            
            # Register the client
            await self.register_client(websocket)
            
            # Handle incoming messages
            try:
                while not self.is_shutdown:
                    # Wait for message with timeout
                    try:
                        raw_message = await asyncio.wait_for(
                            websocket.receive_text(),
                            timeout=self.CLIENT_TIMEOUT
                        )
                        
                        # Parse and validate message
                        try:
                            message = json.loads(raw_message)
                            if not isinstance(message, dict):
                                raise ValueError("Message must be a JSON object")
                            
                            # Handle the message
                            await self.handle_client_message(websocket, message)
                            
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Invalid JSON message from client {client_id}: {e}")
                            error_response = {
                                "type": "error",
                                "message": "Invalid JSON format",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                            await self.send_to_client(websocket, error_response)
                            
                    except asyncio.TimeoutError:
                        # No message received within timeout, continue listening
                        continue
                    
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
            except Exception as e:
                logger.error(f"Error handling client {client_id}: {e}")
                
        except ConnectionLimitExceeded:
            # Send error message before closing
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Connection limit exceeded ({self.max_clients} max)",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                await websocket.close(code=1008, reason="Connection limit exceeded")
            except:
                pass
            raise
            
        except Exception as e:
            logger.error(f"Error in WebSocket connection setup for {client_id}: {e}")
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass
                
        finally:
            # Ensure client is unregistered
            await self.unregister_client(websocket)
            logger.debug(f"Connection cleanup completed for {client_id}")
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the WebSocket manager.
        
        This method closes all client connections and stops background tasks.
        """
        logger.info("Starting WebSocket manager shutdown...")
        self.is_shutdown = True
        
        # Cancel background tasks
        if self.broadcast_task and not self.broadcast_task.done():
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        disconnect_tasks = []
        for client in self.clients.copy():
            try:
                # Send shutdown notice
                shutdown_message = {
                    "type": "server_shutdown",
                    "message": "Server is shutting down",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.send_to_client(client, shutdown_message)
                disconnect_tasks.append(client.close(code=1001, reason="Server shutdown"))
            except:
                pass
        
        # Wait for disconnections to complete
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        # Clear client data
        self.clients.clear()
        self.client_metadata.clear()
        
        logger.info("WebSocket manager shutdown completed")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket connection statistics.
        
        Returns:
            dict: Statistics about WebSocket connections and performance
        """
        connected_durations = []
        now = datetime.now(timezone.utc)
        
        for client, metadata in self.client_metadata.items():
            connected_at = metadata.get('connected_at')
            if connected_at:
                duration = (now - connected_at).total_seconds()
                connected_durations.append(duration)
        
        avg_duration = sum(connected_durations) / len(connected_durations) if connected_durations else 0
        
        return {
            "active_connections": len(self.clients),
            "total_connections": self.total_connections,
            "max_clients": self.max_clients,
            "messages_sent": self.messages_sent,
            "broadcast_errors": self.broadcast_errors,
            "is_broadcasting": self.is_broadcasting,
            "average_connection_duration": avg_duration,
            "broadcast_interval": self.BROADCAST_INTERVAL
        }
    
    def __str__(self) -> str:
        """String representation of the WebSocket manager."""
        return (f"StatusWebSocketManager(clients: {len(self.clients)}/{self.max_clients}, "
                f"broadcasting: {self.is_broadcasting})")
    
    def __repr__(self) -> str:
        """Detailed representation of the WebSocket manager."""
        return self.__str__()


@asynccontextmanager
async def websocket_manager_context(status_manager: ProcessingStatusManager, max_clients: int = 50):
    """
    Async context manager for StatusWebSocketManager.
    
    This provides a convenient way to create and properly shutdown a WebSocket manager.
    
    Args:
        status_manager: ProcessingStatusManager instance
        max_clients: Maximum number of concurrent connections
        
    Yields:
        StatusWebSocketManager: Configured and started WebSocket manager
        
    Example:
        async with websocket_manager_context(status_manager) as ws_manager:
            # Start background tasks
            broadcast_task = asyncio.create_task(ws_manager.start_broadcasting())
            heartbeat_task = asyncio.create_task(ws_manager.start_heartbeat())
            
            try:
                # Use the WebSocket manager...
                await ws_manager.handle_client(websocket)
            finally:
                broadcast_task.cancel()
                heartbeat_task.cancel()
    """
    ws_manager = StatusWebSocketManager(status_manager, max_clients)
    
    try:
        # Start background tasks
        broadcast_task = asyncio.create_task(ws_manager.start_broadcasting())
        heartbeat_task = asyncio.create_task(ws_manager.start_heartbeat())
        ws_manager.broadcast_task = broadcast_task
        ws_manager.heartbeat_task = heartbeat_task
        
        yield ws_manager
        
    finally:
        await ws_manager.shutdown()


# Global instance for backward compatibility
_global_ws_manager: Optional[StatusWebSocketManager] = None


def init_websocket_manager(status_manager: ProcessingStatusManager, max_clients: int = 50) -> StatusWebSocketManager:
    """
    Initialize the global WebSocket manager instance.
    
    Args:
        status_manager: ProcessingStatusManager instance
        max_clients: Maximum number of concurrent connections
        
    Returns:
        StatusWebSocketManager: Initialized WebSocket manager
        
    Note:
        This function is provided for backward compatibility. Consider using
        the context manager approach for better resource management.
    """
    global _global_ws_manager
    _global_ws_manager = StatusWebSocketManager(status_manager, max_clients)
    logger.info("Global WebSocket manager initialized")
    return _global_ws_manager


def get_websocket_manager() -> Optional[StatusWebSocketManager]:
    """
    Get the global WebSocket manager instance.
    
    Returns:
        StatusWebSocketManager or None: Global WebSocket manager if initialized
    """
    return _global_ws_manager