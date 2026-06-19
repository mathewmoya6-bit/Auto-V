# realtime/supabase_realtime.py – Real-time Event Streaming

import logging
from typing import Callable, Dict, Any
from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

class SupabaseRealtime:
    """Real-time event streaming from Supabase."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.channels = {}
    
    def subscribe_to_payments(
        self,
        user_id: str,
        callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to payment changes for a user.
        
        Args:
            user_id: User ID to listen for
            callback: Function to call on payment update
        """
        channel_id = f"payments-{user_id}"
        
        if channel_id in self.channels:
            return
        
        channel = self.supabase.channel(channel_id)\
            .on(
                'postgres_changes',
                {
                    'event': 'UPDATE',
                    'schema': 'public',
                    'table': 'payments',
                    'filter': f'user_id=eq.{user_id}'
                },
                callback
            )\
            .subscribe()
        
        self.channels[channel_id] = channel
        logger.info(f"📡 Subscribed to payments for user {user_id}")
    
    def unsubscribe(self, user_id: str):
        """Unsubscribe from payment changes."""
        channel_id = f"payments-{user_id}"
        
        if channel_id in self.channels:
            self.channels[channel_id].unsubscribe()
            del self.channels[channel_id]
            logger.info(f"📡 Unsubscribed from payments for user {user_id}")
