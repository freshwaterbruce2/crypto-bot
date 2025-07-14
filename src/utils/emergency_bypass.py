"""
Emergency Circuit Breaker Bypass Helper
======================================
Use this for critical trades that must go through
"""

from src.utils.circuit_breaker import circuit_breaker_manager

async def emergency_call(circuit_name: str, func, *args, **kwargs):
    """
    Execute a function with emergency bypass enabled
    
    Args:
        circuit_name: Name of the circuit breaker
        func: Async function to call
        *args, **kwargs: Arguments for the function
    """
    cb = circuit_breaker_manager.get_or_create(circuit_name)
    # Force emergency bypass
    kwargs['emergency_bypass'] = True
    return await cb.call(func, *args, **kwargs)

def force_reset_all():
    """Force reset all circuit breakers immediately"""
    circuit_breaker_manager.reset_all()
    return circuit_breaker_manager.get_summary()
