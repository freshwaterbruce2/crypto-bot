# Quick Integration Guide - Add to bot.py

# Add this import at the top
from src.kraken_compliance_integrator import integrate_compliance_enhancements

# Add this in your bot's __init__ method
def __init__(self, config=None):
    # ... existing initialization ...
    
    # Add Kraken compliance enhancements
    self.compliance_integrator = integrate_compliance_enhancements(self)
    
    # Initialize enhancements
    asyncio.create_task(self._initialize_compliance())

async def _initialize_compliance(self):
    """Initialize compliance enhancements."""
    try:
        results = await self.compliance_integrator.initialize_enhancements()
        
        # Enable network protection
        await self.compliance_integrator.enable_network_protection(timeout=60)
        
        logger.info(f"[COMPLIANCE] Enhancements initialized: {results}")
        
    except Exception as e:
        logger.warning(f"[COMPLIANCE] Enhancement initialization failed: {e}")
