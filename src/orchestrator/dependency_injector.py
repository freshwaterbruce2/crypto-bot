"""
Dependency Injection System

Manages component dependencies, lifecycle, and provides service locator functionality.
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Union
from weakref import WeakValueDictionary

logger = logging.getLogger(__name__)


class ServiceLifetime(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"      # One instance for entire application
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"           # One instance per scope/request


class ServiceState(Enum):
    """Service instance states"""
    NOT_CREATED = "not_created"
    CREATING = "creating"
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    DISPOSING = "disposing"
    DISPOSED = "disposed"


@dataclass
class ServiceDescriptor:
    """Describes a service registration"""
    service_type: type
    implementation: Union[type, Callable, Any]
    lifetime: ServiceLifetime
    dependencies: list[str] = field(default_factory=list)
    init_method: Optional[str] = None
    dispose_method: Optional[str] = None
    factory: Optional[Callable] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceInstance:
    """Tracks a service instance"""
    instance: Any
    descriptor: ServiceDescriptor
    state: ServiceState = ServiceState.NOT_CREATED
    created_at: datetime = field(default_factory=datetime.now)
    scope_id: Optional[str] = None


class ServiceScope:
    """Scoped service container"""

    def __init__(self, scope_id: str, parent: 'DependencyInjector'):
        self.scope_id = scope_id
        self.parent = parent
        self.instances: dict[str, ServiceInstance] = {}
        self._lock = asyncio.Lock()

    async def resolve(self, service_type: Union[str, type]) -> Any:
        """Resolve service within scope"""
        service_name = self._get_service_name(service_type)

        async with self._lock:
            # Check if already in scope
            if service_name in self.instances:
                return self.instances[service_name].instance

            # Create scoped instance
            instance = await self.parent._create_instance(service_name, self.scope_id)
            self.instances[service_name] = ServiceInstance(
                instance=instance,
                descriptor=self.parent.services[service_name],
                state=ServiceState.READY,
                scope_id=self.scope_id
            )

            return instance

    async def dispose(self):
        """Dispose all scoped instances"""
        for instance in self.instances.values():
            await self.parent._dispose_instance(instance)
        self.instances.clear()

    def _get_service_name(self, service_type: Union[str, type]) -> str:
        """Get service name from type"""
        if isinstance(service_type, str):
            return service_type
        return service_type.__name__


class DependencyInjector:
    """Dependency injection container with lifecycle management"""

    def __init__(self):
        self.services: dict[str, ServiceDescriptor] = {}
        self.instances: dict[str, ServiceInstance] = {}
        self.scopes: WeakValueDictionary = WeakValueDictionary()
        self._lock = asyncio.Lock()
        self._initialization_order: list[str] = []
        self._dependency_graph: dict[str, set[str]] = {}

    def register(
        self,
        service_type: type,
        implementation: Union[type, Callable, Any] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        init_method: str = None,
        dispose_method: str = None,
        factory: Callable = None,
        **metadata
    ):
        """Register a service"""
        service_name = service_type.__name__
        implementation = implementation or service_type

        # Auto-detect dependencies from constructor
        dependencies = []
        if inspect.isclass(implementation) and not factory:
            sig = inspect.signature(implementation.__init__)
            for param_name, param in sig.parameters.items():
                if param_name not in ('self', 'args', 'kwargs'):
                    if param.annotation and param.annotation != inspect.Parameter.empty:
                        dep_name = param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)
                        dependencies.append(dep_name)

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=lifetime,
            dependencies=dependencies,
            init_method=init_method or 'initialize' if hasattr(implementation, 'initialize') else None,
            dispose_method=dispose_method or 'shutdown' if hasattr(implementation, 'shutdown') else None,
            factory=factory,
            metadata=metadata
        )

        self.services[service_name] = descriptor
        self._dependency_graph[service_name] = set(dependencies)

        logger.info(f"Registered service: {service_name} (lifetime: {lifetime.value})")

    def register_singleton(self, service_type: type, implementation: Union[type, Any] = None, **kwargs):
        """Register a singleton service"""
        self.register(service_type, implementation, ServiceLifetime.SINGLETON, **kwargs)

    def register_transient(self, service_type: type, implementation: type = None, **kwargs):
        """Register a transient service"""
        self.register(service_type, implementation, ServiceLifetime.TRANSIENT, **kwargs)

    def register_scoped(self, service_type: type, implementation: type = None, **kwargs):
        """Register a scoped service"""
        self.register(service_type, implementation, ServiceLifetime.SCOPED, **kwargs)

    def register_instance(self, service_type: type, instance: Any):
        """Register an existing instance as singleton"""
        service_name = service_type.__name__

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=instance,
            lifetime=ServiceLifetime.SINGLETON
        )

        self.services[service_name] = descriptor
        self.instances[service_name] = ServiceInstance(
            instance=instance,
            descriptor=descriptor,
            state=ServiceState.READY
        )

        logger.info(f"Registered instance: {service_name}")

    async def resolve(self, service_type: Union[str, type]) -> Any:
        """Resolve a service instance"""
        service_name = self._get_service_name(service_type)

        if service_name not in self.services:
            raise ValueError(f"Service not registered: {service_name}")

        descriptor = self.services[service_name]

        # Handle different lifetimes
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return await self._resolve_singleton(service_name)
        elif descriptor.lifetime == ServiceLifetime.TRANSIENT:
            return await self._create_instance(service_name)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            raise ValueError(f"Scoped service {service_name} requires a scope")

    async def _resolve_singleton(self, service_name: str) -> Any:
        """Resolve singleton instance"""
        async with self._lock:
            if service_name in self.instances:
                return self.instances[service_name].instance

            instance = await self._create_instance(service_name)
            self.instances[service_name] = ServiceInstance(
                instance=instance,
                descriptor=self.services[service_name],
                state=ServiceState.READY
            )

            return instance

    async def _create_instance(self, service_name: str, scope_id: str = None) -> Any:
        """Create a service instance"""
        descriptor = self.services[service_name]

        # Check for circular dependencies
        if service_name in self._initialization_order:
            raise ValueError(f"Circular dependency detected for service: {service_name}")

        self._initialization_order.append(service_name)

        try:
            # Resolve dependencies
            resolved_deps = {}
            for dep_name in descriptor.dependencies:
                if dep_name in self.services:
                    if scope_id and self.services[dep_name].lifetime == ServiceLifetime.SCOPED:
                        # Resolve scoped dependency within same scope
                        scope = self.scopes.get(scope_id)
                        if scope:
                            resolved_deps[dep_name.lower()] = await scope.resolve(dep_name)
                    else:
                        resolved_deps[dep_name.lower()] = await self.resolve(dep_name)

            # Create instance
            if descriptor.factory:
                result = descriptor.factory(**resolved_deps)
                if asyncio.iscoroutine(result):
                    instance = await result
                else:
                    instance = result
            elif isinstance(descriptor.implementation, type):
                # Class constructor
                instance = descriptor.implementation(**resolved_deps)
            else:
                # Already an instance
                instance = descriptor.implementation

            # Call initialization method if exists
            if descriptor.init_method and hasattr(instance, descriptor.init_method):
                init_method = getattr(instance, descriptor.init_method)
                if asyncio.iscoroutinefunction(init_method):
                    await init_method()
                else:
                    init_method()

            logger.info(f"Created instance: {service_name}")
            return instance

        finally:
            self._initialization_order.remove(service_name)

    def create_scope(self, scope_id: str = None) -> ServiceScope:
        """Create a new service scope"""
        scope_id = scope_id or f"scope_{id(object())}"
        scope = ServiceScope(scope_id, self)
        self.scopes[scope_id] = scope
        return scope

    async def initialize_all(self):
        """Initialize all singleton services in dependency order"""
        logger.info("Initializing all services")

        # Topological sort for initialization order
        init_order = self._topological_sort()

        for service_name in init_order:
            descriptor = self.services[service_name]
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                await self.resolve(service_name)

        logger.info("All services initialized")

    def _topological_sort(self) -> list[str]:
        """Topological sort of dependency graph"""
        in_degree = dict.fromkeys(self._dependency_graph, 0)

        for node in self._dependency_graph:
            for dep in self._dependency_graph[node]:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for dep in self._dependency_graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        return result

    async def dispose_all(self):
        """Dispose all services in reverse dependency order"""
        logger.info("Disposing all services")

        # Dispose in reverse order
        for service_name in reversed(self._initialization_order):
            if service_name in self.instances:
                await self._dispose_instance(self.instances[service_name])

        self.instances.clear()
        logger.info("All services disposed")

    async def _dispose_instance(self, service_instance: ServiceInstance):
        """Dispose a service instance"""
        if service_instance.state == ServiceState.DISPOSED:
            return

        service_instance.state = ServiceState.DISPOSING

        try:
            descriptor = service_instance.descriptor
            if descriptor.dispose_method and hasattr(service_instance.instance, descriptor.dispose_method):
                dispose_method = getattr(service_instance.instance, descriptor.dispose_method)
                if asyncio.iscoroutinefunction(dispose_method):
                    await dispose_method()
                else:
                    dispose_method()

            service_instance.state = ServiceState.DISPOSED
            logger.info(f"Disposed service: {descriptor.service_type.__name__}")

        except Exception as e:
            logger.error(f"Error disposing service: {e}")

    def _get_service_name(self, service_type: Union[str, type]) -> str:
        """Get service name from type"""
        if isinstance(service_type, str):
            return service_type
        return service_type.__name__

    def get_service_info(self, service_type: Union[str, type]) -> Optional[dict[str, Any]]:
        """Get information about a registered service"""
        service_name = self._get_service_name(service_type)

        if service_name not in self.services:
            return None

        descriptor = self.services[service_name]
        instance_info = self.instances.get(service_name)

        return {
            'name': service_name,
            'lifetime': descriptor.lifetime.value,
            'dependencies': descriptor.dependencies,
            'has_init': descriptor.init_method is not None,
            'has_dispose': descriptor.dispose_method is not None,
            'is_factory': descriptor.factory is not None,
            'metadata': descriptor.metadata,
            'instance_created': instance_info is not None,
            'instance_state': instance_info.state.value if instance_info else None,
            'created_at': instance_info.created_at.isoformat() if instance_info else None
        }

    def get_all_services(self) -> dict[str, dict[str, Any]]:
        """Get information about all registered services"""
        return {
            name: self.get_service_info(name)
            for name in self.services
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Get dependency injection diagnostics"""
        return {
            'registered_services': len(self.services),
            'active_instances': len(self.instances),
            'active_scopes': len(self.scopes),
            'services_by_lifetime': {
                lifetime.value: sum(
                    1 for s in self.services.values()
                    if s.lifetime == lifetime
                )
                for lifetime in ServiceLifetime
            },
            'dependency_graph': {
                name: list(deps)
                for name, deps in self._dependency_graph.items()
            },
            'initialization_order': self._topological_sort()
        }
