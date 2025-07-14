"""
WebSocket authentication manager for Kraken private feeds.
"""

import asyncio
import json
import logging
import hashlib
import hmac
import base64
import time
from typing import Dict, Optional, Any, Callable
from datetime import datetime
from .websocket_manager import KrakenWebSocketManager, WebSocketStatus, WebSocketMessage

logger = logging.getLogger(__name__)


class WebSocketAuthManager:
    """
    WebSocket authentication manager for Kraken private data feeds.
    Handles authentication and private channel subscriptions.
    """
    
    def __init__(self, 
                 api_key: str,
                 api_secret: str,
                 websocket_manager: KrakenWebSocketManager,
                 auth_endpoint: str = "wss://ws-auth.kraken.com"):
        """
        Initialize the WebSocket authentication manager.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            websocket_manager: WebSocket manager instance
            auth_endpoint: Authenticated WebSocket endpoint
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.websocket_manager = websocket_manager
        self.auth_endpoint = auth_endpoint
        
        # Authentication state
        self.authenticated = False
        self.auth_token = None
        self.auth_expiry = None
        
        # Private subscriptions
        self.private_subscriptions = {}
        
        # Message handlers for private channels
        self.private_handlers = {}
        
        logger.info("WebSocketAuthManager initialized")
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the WebSocket API.
        
        Returns:
            True if authentication successful
        """
        try:
            # Get authentication token from REST API
            auth_token = await self._get_auth_token()
            
            if not auth_token:
                logger.error("Failed to get authentication token")
                return False
            
            self.auth_token = auth_token
            self.authenticated = True
            
            logger.info("WebSocket authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def _get_auth_token(self) -> Optional[str]:
        """
        Get authentication token from Kraken REST API.
        
        Returns:
            Authentication token or None if failed
        """
        try:
            # This would typically make a REST API call to get the auth token
            # For now, we'll simulate the token generation process
            
            # In a real implementation, you would:
            # 1. Make a POST request to the Kraken API
            # 2. Sign the request with your API credentials
            # 3. Return the token from the response
            
            # Placeholder implementation
            nonce = str(int(time.time() * 1000))
            
            # Create message to sign
            message = nonce + "GetWebSocketsToken"
            
            # Sign the message
            signature = self._sign_message(message, "/0/private/GetWebSocketsToken")
            
            # In a real implementation, you would send this to the API
            # For now, we'll return a placeholder token
            return f"auth_token_{nonce}"
            
        except Exception as e:
            logger.error(f"Error getting auth token: {e}")
            return None
    
    def _sign_message(self, message: str, path: str) -> str:
        """
        Sign a message with the API secret.
        
        Args:
            message: Message to sign
            path: API path
            
        Returns:
            Base64 encoded signature
        """
        try:
            # Decode the API secret
            secret = base64.b64decode(self.api_secret)
            
            # Create the message hash
            message_hash = hashlib.sha256(message.encode()).digest()
            
            # Create the signature
            signature = hmac.new(secret, path.encode() + message_hash, hashlib.sha512)
            
            # Return base64 encoded signature
            return base64.b64encode(signature.digest()).decode()
            
        except Exception as e:
            logger.error(f"Error signing message: {e}")
            return ""
    
    async def subscribe_private(self, subscription_name: str, **kwargs) -> bool:
        """
        Subscribe to a private WebSocket channel.
        
        Args:
            subscription_name: Name of the private subscription
            **kwargs: Additional subscription parameters
            
        Returns:
            True if subscription successful
        """
        try:
            if not self.authenticated:
                logger.error("Not authenticated - cannot subscribe to private channels")
                return False
            
            # Create subscription message
            subscription_msg = {
                "event": "subscribe",
                "subscription": {
                    "name": subscription_name,
                    "token": self.auth_token,
                    **kwargs
                }
            }
            
            # Send subscription through WebSocket manager
            await self.websocket_manager._send_message(subscription_msg)
            
            # Store subscription
            self.private_subscriptions[subscription_name] = subscription_msg
            
            logger.info(f"Subscribed to private channel: {subscription_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to private channel {subscription_name}: {e}")
            return False
    
    async def unsubscribe_private(self, subscription_name: str) -> bool:
        """
        Unsubscribe from a private WebSocket channel.
        
        Args:
            subscription_name: Name of the private subscription
            
        Returns:
            True if unsubscription successful
        """
        try:
            if not self.authenticated:
                logger.warning("Not authenticated - cannot unsubscribe from private channels")
                return False
            
            # Create unsubscription message
            unsubscribe_msg = {
                "event": "unsubscribe",
                "subscription": {
                    "name": subscription_name,
                    "token": self.auth_token
                }
            }
            
            # Send unsubscription through WebSocket manager
            await self.websocket_manager._send_message(unsubscribe_msg)
            
            # Remove from stored subscriptions
            if subscription_name in self.private_subscriptions:
                del self.private_subscriptions[subscription_name]
            
            logger.info(f"Unsubscribed from private channel: {subscription_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from private channel {subscription_name}: {e}")
            return False
    
    def add_private_handler(self, channel: str, handler: Callable[[WebSocketMessage], None]) -> None:
        """
        Add a message handler for a private channel.
        
        Args:
            channel: Private channel name
            handler: Handler function
        """
        self.private_handlers[channel] = handler
        
        # Also add to the main WebSocket manager
        self.websocket_manager.add_message_handler(channel, handler)
        
        logger.info(f"Added private handler for channel: {channel}")
    
    async def handle_private_message(self, message: WebSocketMessage) -> None:
        """
        Handle private channel messages.
        
        Args:
            message: WebSocket message
        """
        try:
            channel = message.channel
            
            if channel in self.private_handlers:
                handler = self.private_handlers[channel]
                
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            else:
                logger.debug(f"No handler for private channel: {channel}")
                
        except Exception as e:
            logger.error(f"Error handling private message: {e}")
    
    async def subscribe_to_orders(self) -> bool:
        """
        Subscribe to order updates.
        
        Returns:
            True if subscription successful
        """
        return await self.subscribe_private("openOrders")
    
    async def subscribe_to_trades(self) -> bool:
        """
        Subscribe to trade updates.
        
        Returns:
            True if subscription successful
        """
        return await self.subscribe_private("ownTrades")
    
    async def subscribe_to_balances(self) -> bool:
        """
        Subscribe to balance updates.
        
        Returns:
            True if subscription successful
        """
        return await self.subscribe_private("balances")
    
    def setup_order_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Set up handler for order updates.
        
        Args:
            handler: Function to handle order updates
        """
        def order_message_handler(message: WebSocketMessage):
            try:
                # Parse order data from message
                if isinstance(message.data, list) and len(message.data) > 0:
                    order_data = message.data[0]
                    handler(order_data)
                elif isinstance(message.data, dict):
                    handler(message.data)
            except Exception as e:
                logger.error(f"Error in order handler: {e}")
        
        self.add_private_handler("openOrders", order_message_handler)
        logger.info("Order handler set up")
    
    def setup_trade_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Set up handler for trade updates.
        
        Args:
            handler: Function to handle trade updates
        """
        def trade_message_handler(message: WebSocketMessage):
            try:
                # Parse trade data from message
                if isinstance(message.data, list) and len(message.data) > 0:
                    trade_data = message.data[0]
                    handler(trade_data)
                elif isinstance(message.data, dict):
                    handler(message.data)
            except Exception as e:
                logger.error(f"Error in trade handler: {e}")
        
        self.add_private_handler("ownTrades", trade_message_handler)
        logger.info("Trade handler set up")
    
    def setup_balance_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Set up handler for balance updates.
        
        Args:
            handler: Function to handle balance updates
        """
        def balance_message_handler(message: WebSocketMessage):
            try:
                # Parse balance data from message
                if isinstance(message.data, list) and len(message.data) > 0:
                    balance_data = message.data[0]
                    handler(balance_data)
                elif isinstance(message.data, dict):
                    handler(message.data)
            except Exception as e:
                logger.error(f"Error in balance handler: {e}")
        
        self.add_private_handler("balances", balance_message_handler)
        logger.info("Balance handler set up")
    
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self.authenticated
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status."""
        return {
            'authenticated': self.authenticated,
            'auth_token': self.auth_token is not None,
            'auth_expiry': self.auth_expiry.isoformat() if self.auth_expiry else None,
            'private_subscriptions': len(self.private_subscriptions),
            'subscription_names': list(self.private_subscriptions.keys())
        }
    
    async def refresh_authentication(self) -> bool:
        """
        Refresh authentication token.
        
        Returns:
            True if refresh successful
        """
        try:
            # Get new auth token
            new_token = await self._get_auth_token()
            
            if not new_token:
                logger.error("Failed to refresh authentication token")
                return False
            
            # Update token
            old_token = self.auth_token
            self.auth_token = new_token
            
            # Resubscribe to all private channels with new token
            for subscription_name, subscription_msg in self.private_subscriptions.items():
                subscription_msg['subscription']['token'] = new_token
                await self.websocket_manager._send_message(subscription_msg)
            
            logger.info("Authentication token refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing authentication: {e}")
            return False
    
    def get_private_subscriptions(self) -> Dict[str, Any]:
        """Get all private subscriptions."""
        return self.private_subscriptions.copy()
    
    def clear_private_subscriptions(self) -> None:
        """Clear all private subscriptions."""
        self.private_subscriptions.clear()
        self.private_handlers.clear()
        logger.info("Cleared all private subscriptions")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get authentication manager statistics."""
        return {
            'authenticated': self.authenticated,
            'private_subscriptions': len(self.private_subscriptions),
            'private_handlers': len(self.private_handlers),
            'auth_token_available': self.auth_token is not None,
            'subscription_names': list(self.private_subscriptions.keys()),
            'handler_channels': list(self.private_handlers.keys())
        }