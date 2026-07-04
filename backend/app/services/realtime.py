"""
Supabase Realtime Integration for AUTO-V (FastAPI Version)
Handles real-time event streaming for payments, valuations, inspections, mileage, and more
Production hardened with proper error handling and connection management
"""

import os
import logging
import json
import time
import asyncio
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from threading import Thread, Event, Lock
from contextlib import asynccontextmanager

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────

REALTIME_ENABLED = os.getenv('REALTIME_ENABLED', 'true').lower() == 'true'
REALTIME_HEARTBEAT_INTERVAL = int(os.getenv('REALTIME_HEARTBEAT_INTERVAL', '30'))
REALTIME_RETRY_ATTEMPTS = int(os.getenv('REALTIME_RETRY_ATTEMPTS', '3'))
REALTIME_RETRY_DELAY = int(os.getenv('REALTIME_RETRY_DELAY', '2'))
REALTIME_MAX_CHANNELS = int(os.getenv('REALTIME_MAX_CHANNELS', '100'))


class SupabaseRealtime:
    """
    Real-time event streaming from Supabase.
    
    Supports:
    - Payment status updates
    - Service request updates
    - Valuation completions
    - Inspection completions
    - Assessment completions
    - Mileage rate calculations and updates
    - Mileage claims and approvals
    - User profile updates
    - System notifications
    """
    
    def __init__(self):
        self._client = None
        self._client_initialized = False
        self._lock = Lock()
        self._init_client()
        
        self.channels = {}
        self.listeners = {}
        self._stop_events = {}
        self._threads = {}
        self._heartbeat_interval = REALTIME_HEARTBEAT_INTERVAL
        self._enabled = REALTIME_ENABLED
        self._max_channels = REALTIME_MAX_CHANNELS
        
        if not self._enabled:
            logger.warning("⚠️ Realtime is disabled (REALTIME_ENABLED=false)")
    
    def _init_client(self):
        """Initialize Supabase client safely."""
        if self._client_initialized:
            return
        
        with self._lock:
            if self._client_initialized:
                return
            
            try:
                self._client = get_supabase()
                self._client_initialized = True
                logger.info("✅ Supabase client initialized for realtime")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase client: {e}")
                self._client = None
                self._client_initialized = False
    
    def _get_client(self):
        """Get Supabase client with lazy initialization."""
        if not self._client_initialized:
            self._init_client()
        return self._client
    
    def _safe_channel(self, channel_id: str):
        """Safely create a channel with error handling."""
        if not self._enabled:
            logger.warning(f"⚠️ Realtime disabled, not creating channel: {channel_id}")
            return None
        
        if len(self.channels) >= self._max_channels:
            logger.error(f"❌ Max channels reached ({self._max_channels})")
            return None
        
        client = self._get_client()
        if not client:
            logger.error(f"❌ No Supabase client for channel: {channel_id}")
            return None
        
        try:
            # Check if client has realtime attribute
            if hasattr(client, 'realtime'):
                return client.realtime.channel(channel_id)
            elif hasattr(client, 'channel'):
                return client.channel(channel_id)
            else:
                logger.error(f"❌ Client has no realtime or channel method")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to create channel {channel_id}: {e}")
            return None
    
    # ─── Payment Events ──────────────────────────────────────────
    
    def subscribe_to_payments(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE']
    ) -> Optional[str]:
        """Subscribe to payment changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"payments-{user_id}"
        
        if channel_id in self.channels:
            logger.warning(f"Already subscribed to payments for user {user_id}")
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'payments',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Payment callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'payments',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'payments',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to payments for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to payments for user {user_id}: {e}")
            return None
    
    # ─── Service Request Events ──────────────────────────────────
    
    def subscribe_to_service_requests(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE', 'DELETE']
    ) -> Optional[str]:
        """Subscribe to service request changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"service_requests-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'service_requests',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Service request callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'service_requests',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'service_requests',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to service requests for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to service requests for user {user_id}: {e}")
            return None
    
    # ─── Valuation Events ────────────────────────────────────────
    
    def subscribe_to_valuations(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE']
    ) -> Optional[str]:
        """Subscribe to valuation changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"valuations-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'valuations',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Valuation callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'valuations',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'valuations',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to valuations for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to valuations for user {user_id}: {e}")
            return None
    
    # ─── Inspection Events ────────────────────────────────────────
    
    def subscribe_to_inspections(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE']
    ) -> Optional[str]:
        """Subscribe to inspection changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"inspections-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'inspections',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Inspection callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'inspections',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'inspections',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to inspections for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to inspections for user {user_id}: {e}")
            return None
    
    # ─── Assessment Events ────────────────────────────────────────
    
    def subscribe_to_assessments(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE']
    ) -> Optional[str]:
        """Subscribe to assessment changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"assessments-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'assessments',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Assessment callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'assessments',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'assessments',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to assessments for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to assessments for user {user_id}: {e}")
            return None
    
    # ─── Mileage Rate Events ──────────────────────────────────────
    
    def subscribe_to_mileage_rates(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE', 'DELETE']
    ) -> Optional[str]:
        """Subscribe to mileage rate changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"mileage_rates-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'mileage_rates',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Mileage rate callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'mileage_rates',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'mileage_rates',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to mileage rates for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to mileage rates for user {user_id}: {e}")
            return None
    
    # ─── Mileage Claim Events ─────────────────────────────────────
    
    def subscribe_to_mileage_claims(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['INSERT', 'UPDATE', 'DELETE']
    ) -> Optional[str]:
        """Subscribe to mileage claim changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"mileage_claims-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'mileage_claims',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Mileage claim callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'mileage_claims',
                        'filter': f'user_id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'mileage_claims',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to mileage claims for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to mileage claims for user {user_id}: {e}")
            return None
    
    # ─── Notification Events ──────────────────────────────────────
    
    def subscribe_to_notifications(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> Optional[str]:
        """Subscribe to notification changes for a user."""
        if not self._enabled:
            return None
        
        channel_id = f"notifications-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'notifications',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Notification callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            channel = channel.on(
                'postgres_changes',
                {
                    'event': 'INSERT',
                    'schema': 'public',
                    'table': 'notifications',
                    'filter': f'user_id=eq.{user_id}'
                },
                handler
            )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'notifications',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to notifications for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to notifications for user {user_id}: {e}")
            return None
    
    # ─── User Profile Events ──────────────────────────────────────
    
    def subscribe_to_user_profiles(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['UPDATE']
    ) -> Optional[str]:
        """Subscribe to user profile changes."""
        if not self._enabled:
            return None
        
        channel_id = f"user_profiles-{user_id}"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                
                callback({
                    'event': event_type,
                    'table': 'user_profiles',
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"User profile callback error: {e}")
        
        try:
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for event_type in event_types:
                channel = channel.on(
                    'postgres_changes',
                    {
                        'event': event_type,
                        'schema': 'public',
                        'table': 'user_profiles',
                        'filter': f'id=eq.{user_id}'
                    },
                    handler
                )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'user_profiles',
                'user_id': user_id,
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to user profile for user {user_id} (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to user profile for user {user_id}: {e}")
            return None
    
    # ─── System Events ────────────────────────────────────────────
    
    def subscribe_to_system_events(
        self,
        callback: Callable[[Dict[str, Any]], None],
        event_types: List[str] = ['UPDATE', 'INSERT']
    ) -> Optional[str]:
        """Subscribe to system-wide events (admin use)."""
        if not self._enabled:
            return None
        
        channel_id = "system-events"
        
        if channel_id in self.channels:
            return channel_id
        
        def handler(payload):
            try:
                event_type = payload.get('event_type') or payload.get('type')
                new_data = payload.get('new', {}) or payload.get('data', {})
                old_data = payload.get('old') or payload.get('old_data')
                table = payload.get('table') or payload.get('schema')
                
                callback({
                    'event': event_type,
                    'table': table,
                    'data': new_data,
                    'old_data': old_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"System event callback error: {e}")
        
        try:
            tables = [
                'payments', 
                'service_requests', 
                'valuations', 
                'inspections', 
                'assessments',
                'mileage_rates',
                'mileage_claims',
                'user_profiles'
            ]
            
            channel = self._safe_channel(channel_id)
            if not channel:
                return None
            
            for table in tables:
                for event_type in event_types:
                    channel = channel.on(
                        'postgres_changes',
                        {
                            'event': event_type,
                            'schema': 'public',
                            'table': table
                        },
                        handler
                    )
            
            channel.subscribe()
            self.channels[channel_id] = channel
            self.listeners[channel_id] = {
                'type': 'system',
                'callback': callback,
                'started_at': datetime.now().isoformat()
            }
            
            self.start_heartbeat(channel_id)
            logger.info(f"📡 Subscribed to system events (channel: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to system events: {e}")
            return None
    
    # ─── Combined Events ────────────────────────────────────────
    
    def subscribe_to_all_user_events(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None]
    ) -> List[str]:
        """Subscribe to all events for a user."""
        if not self._enabled:
            return []
        
        channel_ids = []
        
        subscriptions = [
            (self.subscribe_to_payments, 'payments'),
            (self.subscribe_to_service_requests, 'service_requests'),
            (self.subscribe_to_valuations, 'valuations'),
            (self.subscribe_to_inspections, 'inspections'),
            (self.subscribe_to_assessments, 'assessments'),
            (self.subscribe_to_mileage_rates, 'mileage_rates'),
            (self.subscribe_to_mileage_claims, 'mileage_claims'),
            (self.subscribe_to_notifications, 'notifications'),
            (self.subscribe_to_user_profiles, 'user_profiles')
        ]
        
        for subscribe_func, name in subscriptions:
            try:
                channel_id = subscribe_func(user_id, callback)
                if channel_id:
                    channel_ids.append(channel_id)
                    logger.info(f"✅ Subscribed to {name} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {name} for user {user_id}: {e}")
        
        return channel_ids
    
    # ─── Heartbeat ──────────────────────────────────────────────────
    
    def _heartbeat(self, channel_id: str):
        """Send periodic heartbeat to keep channel alive."""
        if not self._enabled:
            return
        
        if channel_id in self.channels:
            try:
                channel = self.channels[channel_id]
                if hasattr(channel, 'is_connected') and not channel.is_connected:
                    logger.warning(f"Channel {channel_id} disconnected, reconnecting...")
                    self.reconnect(channel_id)
            except Exception as e:
                logger.error(f"Heartbeat error for {channel_id}: {e}")
    
    def start_heartbeat(self, channel_id: str):
        """Start heartbeat for a channel."""
        if not self._enabled:
            return
        
        if channel_id in self._stop_events:
            return
        
        stop_event = Event()
        self._stop_events[channel_id] = stop_event
        
        def heartbeat_loop():
            while not stop_event.is_set():
                time.sleep(self._heartbeat_interval)
                self._heartbeat(channel_id)
        
        thread = Thread(target=heartbeat_loop, daemon=True)
        thread.start()
        self._threads[channel_id] = thread
        logger.debug(f"💓 Heartbeat started for {channel_id}")
    
    def stop_heartbeat(self, channel_id: str):
        """Stop heartbeat for a channel."""
        if channel_id in self._stop_events:
            self._stop_events[channel_id].set()
            del self._stop_events[channel_id]
            logger.debug(f"💓 Heartbeat stopped for {channel_id}")
    
    # ─── Reconnection ─────────────────────────────────────────────
    
    def reconnect(self, channel_id: str) -> bool:
        """Reconnect a channel."""
        if not self._enabled:
            return False
        
        if channel_id not in self.channels:
            logger.warning(f"Channel {channel_id} not found for reconnection")
            return False
        
        try:
            channel = self.channels[channel_id]
            try:
                channel.unsubscribe()
            except:
                pass
            
            del self.channels[channel_id]
            
            listener = self.listeners.get(channel_id)
            if not listener:
                logger.warning(f"No listener found for {channel_id}")
                return False
            
            listener_type = listener.get('type')
            user_id = listener.get('user_id')
            callback = listener.get('callback')
            
            type_map = {
                'payments': self.subscribe_to_payments,
                'service_requests': self.subscribe_to_service_requests,
                'valuations': self.subscribe_to_valuations,
                'inspections': self.subscribe_to_inspections,
                'assessments': self.subscribe_to_assessments,
                'mileage_rates': self.subscribe_to_mileage_rates,
                'mileage_claims': self.subscribe_to_mileage_claims,
                'notifications': self.subscribe_to_notifications,
                'user_profiles': self.subscribe_to_user_profiles,
                'system': self.subscribe_to_system_events
            }
            
            subscribe_func = type_map.get(listener_type)
            if not subscribe_func:
                logger.error(f"Unknown listener type: {listener_type}")
                return False
            
            if listener_type == 'system':
                subscribe_func(callback)
            elif user_id:
                subscribe_func(user_id, callback)
            else:
                logger.error(f"No user_id for listener type: {listener_type}")
                return False
            
            logger.info(f"✅ Channel {channel_id} reconnected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reconnect {channel_id}: {e}")
            return False
    
    # ─── Unsubscribe ──────────────────────────────────────────────
    
    def unsubscribe(self, user_id: str = None, channel_id: str = None):
        """Unsubscribe from a channel."""
        if channel_id:
            self._unsubscribe_channel(channel_id)
        elif user_id:
            to_remove = [
                cid for cid, data in self.listeners.items()
                if data.get('user_id') == user_id
            ]
            for cid in to_remove:
                self._unsubscribe_channel(cid)
            logger.info(f"📡 Unsubscribed all channels for user {user_id}")
    
    def unsubscribe_all(self):
        """Unsubscribe from all channels."""
        for channel_id in list(self.channels.keys()):
            self._unsubscribe_channel(channel_id)
        logger.info("📡 Unsubscribed from all channels")
    
    def _unsubscribe_channel(self, channel_id: str):
        """Unsubscribe a specific channel."""
        if channel_id not in self.channels:
            return
        
        try:
            self.stop_heartbeat(channel_id)
            self.channels[channel_id].unsubscribe()
            del self.channels[channel_id]
            
            if channel_id in self.listeners:
                del self.listeners[channel_id]
            
            logger.info(f"📡 Unsubscribed from channel: {channel_id}")
        except Exception as e:
            logger.error(f"Error unsubscribing {channel_id}: {e}")
    
    # ─── Status ────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get real-time service status."""
        return {
            'enabled': self._enabled,
            'active_channels': len(self.channels),
            'listeners': [
                {
                    'channel_id': cid,
                    'type': data.get('type'),
                    'user_id': data.get('user_id'),
                    'started_at': data.get('started_at')
                }
                for cid, data in self.listeners.items()
            ],
            'threads': len(self._threads),
            'max_channels': self._max_channels,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_active_channels(self) -> List[str]:
        """Get list of active channel IDs."""
        return list(self.channels.keys())
    
    def get_listener_count(self) -> int:
        """Get number of active listeners."""
        return len(self.listeners)
    
    def get_listener_types(self) -> Dict[str, int]:
        """Get count of each listener type."""
        type_counts = {}
        for data in self.listeners.values():
            listener_type = data.get('type', 'unknown')
            type_counts[listener_type] = type_counts.get(listener_type, 0) + 1
        return type_counts
    
    def is_connected(self, channel_id: str) -> bool:
        """Check if a channel is connected."""
        if not self._enabled:
            return False
        if channel_id not in self.channels:
            return False
        try:
            channel = self.channels[channel_id]
            return hasattr(channel, 'is_connected') and channel.is_connected
        except:
            return False
    
    # ─── Cleanup ───────────────────────────────────────────────────
    
    def cleanup(self):
        """Clean up all channels and threads."""
        for channel_id in list(self.channels.keys()):
            self._unsubscribe_channel(channel_id)
        
        for thread in self._threads.values():
            try:
                thread.join(timeout=5)
            except:
                pass
        
        self._threads.clear()
        self._stop_events.clear()
        logger.info("🧹 Real-time service cleaned up")


# ─── Singleton Instance ──────────────────────────────────────────

_realtime_instance = None
_realtime_lock = Lock()


def get_realtime() -> SupabaseRealtime:
    """Get real-time service instance (singleton)."""
    global _realtime_instance
    if _realtime_instance is None:
        with _realtime_lock:
            if _realtime_instance is None:
                _realtime_instance = SupabaseRealtime()
    return _realtime_instance


# ─── FastAPI Dependency ──────────────────────────────────────────

async def get_realtime_client() -> SupabaseRealtime:
    """FastAPI dependency for realtime client."""
    return get_realtime()


# ─── Context Manager ────────────────────────────────────────────

@asynccontextmanager
async def realtime_context():
    """Async context manager for realtime service."""
    realtime = get_realtime()
    try:
        yield realtime
    finally:
        # Don't cleanup on context exit - let the singleton manage lifecycle
        pass


# ─── Quick Test ──────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 Testing Supabase Realtime...")
    
    realtime = get_realtime()
    
    def on_mileage_update(data):
        print(f"📏 Mileage update: {data}")
    
    try:
        realtime.subscribe_to_mileage_rates('test-user', on_mileage_update)
        print("✅ Subscribed to mileage rates")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    def on_all_events(data):
        print(f"📡 Event: {data.get('table')} - {data.get('event')}")
    
    try:
        channels = realtime.subscribe_to_all_user_events('test-user', on_all_events)
        print(f"✅ Subscribed to {len(channels)} user channels")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    status = realtime.get_status()
    print(f"📊 Status: {status}")
    
    types = realtime.get_listener_types()
    print(f"📋 Listener types: {types}")
    
    realtime.cleanup()
    print("✅ Test complete")
