"""
Paper Trading Performance Tracker
Tracks and reports paper trading performance
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path

from .paper_config import get_paper_config

logger = logging.getLogger(__name__)

class PaperPerformanceTracker:
    """Tracks paper trading performance and generates reports"""
    
    def __init__(self):
        self.config = get_paper_config()
        self.session_start = datetime.now(timezone.utc)
        
    def generate_report(self, executor) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        performance = executor.get_performance_summary()
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'session_start': self.session_start.isoformat(),
            'session_duration_minutes': (datetime.now(timezone.utc) - self.session_start).total_seconds() / 60,
            'paper_trading_config': self.config.to_dict(),
            'performance': performance,
            'trade_history': executor.trade_history[-10:],  # Last 10 trades
            'recommendations': self._generate_recommendations(performance)
        }
        
        # Save report
        if self.config.generate_reports:
            self._save_report(report)
        
        return report
    
    def _generate_recommendations(self, performance: Dict[str, Any]) -> List[str]:
        """Generate trading recommendations based on performance"""
        recommendations = []
        
        if performance['total_trades'] == 0:
            recommendations.append("No trades executed yet - check signal generation")
        
        if performance['success_rate'] < 50:
            recommendations.append("Low success rate - review position sizing and entry criteria")
        
        if performance['total_return_pct'] < -5:
            recommendations.append("Negative returns - consider risk management adjustments")
        
        if performance['total_trades'] > 0 and performance['total_return_pct'] > 10:
            recommendations.append("Strong performance - consider increasing position sizes")
        
        return recommendations
    
    def _save_report(self, report: Dict[str, Any]):
        """Save report to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.config.reports_dir / f"paper_trading_report_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"📊 Paper trading report saved: {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    def print_summary(self, performance: Dict[str, Any]):
        """Print performance summary to console"""
        print("\n" + "="*80)
        print("🧪 PAPER TRADING PERFORMANCE SUMMARY")
        print("="*80)
        print(f"📊 Total Trades: {performance['total_trades']}")
        print(f"✅ Success Rate: {performance['success_rate']:.1f}%")
        print(f"💰 P&L: ${performance['total_profit_loss']:,.2f}")
        print(f"📈 Return: {performance['total_return_pct']:+.2f}%")
        print(f"💳 Current Balance: ${performance['current_balance']:,.2f}")
        print(f"📋 Open Positions: {len(performance['positions'])}")
        
        if performance['positions']:
            print("\n📊 Current Positions:")
            for symbol, pos in performance['positions'].items():
                pnl_pct = ((pos['value'] / (pos['amount'] * pos['entry_price'])) - 1) * 100
                print(f"   {symbol}: {pos['amount']:.4f} @ ${pos['entry_price']:.4f} ({pnl_pct:+.1f}%)")
        
        print("="*80)
