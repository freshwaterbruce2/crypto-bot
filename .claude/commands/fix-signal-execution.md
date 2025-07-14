# FIX 3: SIGNAL EXECUTION PIPELINE

File: src/bot.py

Update run_once() to properly execute signals:

```python
async def run_once(self):
    """Main loop with signal execution"""
    try:
        all_signals = []
        
        # Get signals from scanner
        if hasattr(self, 'opportunity_scanner'):
            opportunities = await self.opportunity_scanner.scan_opportunities()
            for opp in opportunities:
                if opp.get('symbol', '').endswith('/USDT'):
                    all_signals.append({
                        'symbol': opp['symbol'],
                        'side': opp.get('action', 'buy'),
                        'confidence': opp.get('confidence', 0.5),
                        'strategy': 'scanner',
                        'amount_usdt': 10.0
                    })
        
        # Execute signals
        if all_signals and self.components.trade_executor:
            all_signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            for signal in all_signals[:3]:  # Max 3 per cycle
                if signal['confidence'] > 0.7:
                    await self._execute_signal(signal)
                    await asyncio.sleep(0.5)
                    
    except Exception as e:
        logger.error(f"[RUN] Error: {e}")

async def _execute_signal(self, signal):
    """Execute trading signal"""
    try:
        # Validate minimum $5 USDT
        amount = max(5.0, signal['amount_usdt'])
        
        # Check balance
        balance = await self.components.balance_manager.get_available_balance('USDT')
        if balance < amount:
            return
            
        # Execute
        result = await self.components.trade_executor.execute_trade(
            symbol=signal['symbol'],
            side=signal['side'],
            amount=amount,
            signal=signal
        )
        
        if result.get('success'):
            logger.info(f"[TRADE] Success: {signal['side']} {amount} USDT of {signal['symbol']}")
            
    except Exception as e:
        logger.error(f"[TRADE] Error: {e}")
```