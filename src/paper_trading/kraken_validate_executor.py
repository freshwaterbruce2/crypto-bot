"""
Enhanced Paper Trading with Kraken Validate Parameter
Combines paper trading with Kraken's validate parameter for comprehensive testing
"""

import logging
from typing import Any, Dict

from .paper_executor import PaperTradeExecutor

logger = logging.getLogger(__name__)

class KrakenValidateIntegratedExecutor(PaperTradeExecutor):
    """Paper trading executor that also tests Kraken's validate parameter"""

    def __init__(self, real_executor=None, exchange=None):
        super().__init__(real_executor, exchange)
        self.validate_tests = 0
        self.validate_successes = 0
        self.validate_failures = 0

    async def execute(self, request) -> Dict[str, Any]:
        """Execute paper trade AND test Kraken validate parameter"""

        # First run the paper trade simulation
        paper_result = await super().execute(request)

        # Additionally test Kraken's validate parameter if real executor available
        validate_result = None
        if self.real_executor and hasattr(self.real_executor, 'exchange'):
            validate_result = await self._test_kraken_validate(request)

        # Combine results
        combined_result = paper_result.copy()
        combined_result['validate_test'] = validate_result

        return combined_result

    async def _test_kraken_validate(self, request) -> Dict[str, Any]:
        """Test order using Kraken's validate parameter"""
        try:
            self.validate_tests += 1

            # Prepare order with validate=true
            order_params = {
                'pair': request.symbol.replace('/', ''),  # Remove slash for Kraken
                'type': request.side.lower(),
                'ordertype': 'market',  # or 'limit'
                'volume': str(request.amount),
                'validate': True  # This prevents actual execution
            }

            # If limit order, add price
            if hasattr(request, 'price') and request.price:
                order_params['ordertype'] = 'limit'
                order_params['price'] = str(request.price)

            # Call Kraken API with validate parameter
            if hasattr(self.real_executor.exchange, 'add_order'):
                response = await self.real_executor.exchange.add_order(**order_params)

                # Kraken validate response won't have order ID
                if response.get('error'):
                    self.validate_failures += 1
                    return {
                        'success': False,
                        'error': response['error'],
                        'kraken_validation': 'failed'
                    }
                else:
                    self.validate_successes += 1
                    return {
                        'success': True,
                        'kraken_validation': 'passed',
                        'order_description': response.get('result', {}).get('descr', {})
                    }
            else:
                return {
                    'success': False,
                    'error': 'Exchange does not support validate parameter',
                    'kraken_validation': 'unavailable'
                }

        except Exception as e:
            self.validate_failures += 1
            logger.error(f"Kraken validate test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'kraken_validation': 'error'
            }

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get Kraken validation test statistics"""
        success_rate = (self.validate_successes / self.validate_tests * 100) if self.validate_tests > 0 else 0

        return {
            'total_validate_tests': self.validate_tests,
            'validate_successes': self.validate_successes,
            'validate_failures': self.validate_failures,
            'validate_success_rate': success_rate
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Enhanced performance summary with validation stats"""
        summary = super().get_performance_summary()
        summary['kraken_validation'] = self.get_validation_stats()
        return summary
