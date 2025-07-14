"""
Integration Coordinator - Ensures proper component initialization and connection
==============================================================================

This module provides a centralized coordinator to ensure all components are
properly initialized in the correct order and integrated with each other.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    """Component initialization states"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    FAILED = "failed"


@dataclass
class ComponentInfo:
    """Information about a component"""
    name: str
    state: ComponentState = ComponentState.NOT_INITIALIZED
    dependencies: List[str] = field(default_factory=list)
    error: Optional[str] = None
    instance: Optional[Any] = None


class IntegrationCoordinator:
    """
    Coordinates component initialization and integration.
    
    Ensures components are initialized in the correct order based on
    their dependencies and that all integrations are properly established.
    """
    
    def __init__(self):
        self.components: Dict[str, ComponentInfo] = {}
        self._initialization_order: List[str] = []
        self._initialized = False
        
        # Define component dependencies
        self._define_dependencies()
        
        logger.info("[INTEGRATION] Integration coordinator initialized")
    
    def _define_dependencies(self):
        """Define component dependencies and initialization order"""
        # Core components and their dependencies
        dependencies = {
            'exchange': [],  # No dependencies
            'websocket_manager': ['exchange'],  # Needs exchange for REST client
            'balance_manager': ['exchange', 'websocket_manager'],  # Needs both
            'realtime_balance_manager': ['websocket_manager'],  # Needs WebSocket
            'trade_executor': ['exchange', 'balance_manager'],  # Needs exchange and balance
            'portfolio_scanner': ['balance_manager'],  # Needs balance manager
            'strategy_manager': ['trade_executor'],  # Needs executor
            'opportunity_scanner': ['strategy_manager'],  # Needs strategies
            'learning_system': ['trade_executor'],  # Needs executor for learning
            'minimum_integration': ['exchange', 'balance_manager'],  # Needs both
        }
        
        # Register components with their dependencies
        for name, deps in dependencies.items():
            self.register_component(name, deps)
    
    def register_component(self, name: str, dependencies: List[str] = None):
        """Register a component with its dependencies"""
        if name not in self.components:
            self.components[name] = ComponentInfo(
                name=name,
                dependencies=dependencies or []
            )
            logger.debug(f"[INTEGRATION] Registered component: {name}")
    
    def get_initialization_order(self) -> List[str]:
        """
        Get the order in which components should be initialized.
        
        Uses topological sort to ensure dependencies are initialized first.
        """
        if self._initialization_order:
            return self._initialization_order
            
        # Build dependency graph
        graph = {name: comp.dependencies for name, comp in self.components.items()}
        
        # Topological sort
        visited = set()
        order = []
        
        def visit(node: str):
            if node in visited:
                return
            visited.add(node)
            
            # Visit dependencies first
            for dep in graph.get(node, []):
                if dep in graph:  # Only visit registered components
                    visit(dep)
            
            order.append(node)
        
        # Visit all nodes
        for node in graph:
            visit(node)
        
        self._initialization_order = order
        logger.info(f"[INTEGRATION] Initialization order: {order}")
        return order
    
    async def initialize_component(self, name: str, initializer_func: Any) -> bool:
        """
        Initialize a component using the provided initializer function.
        
        Args:
            name: Component name
            initializer_func: Async function that initializes the component
            
        Returns:
            bool: True if successful, False otherwise
        """
        if name not in self.components:
            logger.error(f"[INTEGRATION] Unknown component: {name}")
            return False
            
        component = self.components[name]
        
        # Check dependencies
        for dep in component.dependencies:
            if dep in self.components:
                dep_state = self.components[dep].state
                if dep_state != ComponentState.INITIALIZED:
                    logger.error(
                        f"[INTEGRATION] Cannot initialize {name}: "
                        f"dependency {dep} is {dep_state.value}"
                    )
                    component.state = ComponentState.FAILED
                    component.error = f"Dependency {dep} not initialized"
                    return False
        
        # Initialize component
        try:
            component.state = ComponentState.INITIALIZING
            logger.info(f"[INTEGRATION] Initializing {name}...")
            
            result = await initializer_func()
            
            component.instance = result
            component.state = ComponentState.INITIALIZED
            logger.info(f"[INTEGRATION] [OK] {name} initialized successfully")
            return True
            
        except Exception as e:
            component.state = ComponentState.FAILED
            component.error = str(e)
            logger.error(f"[INTEGRATION] [ERROR] {name} initialization failed: {e}")
            return False
    
    def get_component(self, name: str) -> Optional[Any]:
        """Get an initialized component instance"""
        if name in self.components:
            component = self.components[name]
            if component.state == ComponentState.INITIALIZED:
                return component.instance
        return None
    
    def is_component_ready(self, name: str) -> bool:
        """Check if a component is initialized and ready"""
        if name in self.components:
            return self.components[name].state == ComponentState.INITIALIZED
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of all components"""
        status = {}
        for name, component in self.components.items():
            status[name] = {
                'state': component.state.value,
                'dependencies': component.dependencies,
                'error': component.error,
                'ready': component.state == ComponentState.INITIALIZED
            }
        return status
    
    async def wait_for_components(self, component_names: List[str], timeout: float = 30) -> bool:
        """
        Wait for specific components to be initialized.
        
        Args:
            component_names: List of component names to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if all components are ready, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            all_ready = all(self.is_component_ready(name) for name in component_names)
            if all_ready:
                return True
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                not_ready = [
                    name for name in component_names 
                    if not self.is_component_ready(name)
                ]
                logger.error(
                    f"[INTEGRATION] Timeout waiting for components: {not_ready}"
                )
                return False
                
            await asyncio.sleep(0.5)
    
    def validate_integrations(self) -> List[str]:
        """
        Validate that all components are properly integrated.
        
        Returns:
            List of integration issues found
        """
        issues = []
        
        # Check WebSocket integration with balance manager
        ws_manager = self.get_component('websocket_manager')
        balance_manager = self.get_component('balance_manager')
        
        if ws_manager and balance_manager:
            if hasattr(balance_manager, 'websocket_manager'):
                if balance_manager.websocket_manager != ws_manager:
                    issues.append("Balance manager not using correct WebSocket instance")
            else:
                issues.append("Balance manager missing WebSocket integration")
        
        # Check real-time balance manager integration
        rt_balance = self.get_component('realtime_balance_manager')
        if rt_balance and ws_manager:
            if hasattr(rt_balance, 'ws_manager'):
                if rt_balance.ws_manager != ws_manager:
                    issues.append("Real-time balance manager not using correct WebSocket")
            else:
                issues.append("Real-time balance manager missing WebSocket")
        
        # Check trade executor integration
        executor = self.get_component('trade_executor')
        if executor and balance_manager:
            if hasattr(executor, 'balance_manager'):
                if executor.balance_manager != balance_manager:
                    issues.append("Trade executor not using correct balance manager")
            else:
                issues.append("Trade executor missing balance manager")
        
        # Check strategy manager integration
        strategy_mgr = self.get_component('strategy_manager')
        if strategy_mgr and executor:
            if hasattr(strategy_mgr, 'trade_executor'):
                if strategy_mgr.trade_executor != executor:
                    issues.append("Strategy manager not using correct trade executor")
        
        return issues


# Global coordinator instance
_coordinator = IntegrationCoordinator()


def get_coordinator() -> IntegrationCoordinator:
    """Get the global integration coordinator"""
    return _coordinator