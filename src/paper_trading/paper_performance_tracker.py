"""
Paper Trading Performance Tracker
Tracks and reports paper trading performance
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .paper_config import get_paper_config

logger = logging.getLogger(__name__)

class PaperPerformanceTracker:
    """Enhanced paper trading performance tracker with comprehensive monitoring"""

    def __init__(self, config=None):
        self.config = config or get_paper_config()
        self.session_start = datetime.now(timezone.utc)
        self.performance_data = {
            "starting_balance": self.config.starting_balance,
            "current_balance": self.config.starting_balance,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "peak_balance": self.config.starting_balance,
            "trade_history": [],
            "daily_pnl": {},
            "hourly_metrics": {},
            "risk_metrics": {},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        self._load_existing_data()

    def _load_existing_data(self):
        """Load existing performance data if available"""
        try:
            perf_file = self.config.performance_file
            if perf_file and perf_file.exists():
                with open(perf_file) as f:
                    existing_data = json.load(f)
                    self.performance_data.update(existing_data)
                logger.info("Loaded existing performance data")
        except Exception as e:
            logger.warning(f"Could not load existing performance data: {e}")

    def record_trade(self, trade_data: Dict[str, Any]):
        """Record a completed trade"""
        try:
            # Update trade counts
            self.performance_data["total_trades"] += 1

            # Calculate trade P&L
            trade_pnl = trade_data.get("pnl", 0.0)
            self.performance_data["total_pnl"] += trade_pnl
            self.performance_data["current_balance"] += trade_pnl

            # Update win/loss counts
            if trade_pnl > 0:
                self.performance_data["winning_trades"] += 1
            else:
                self.performance_data["losing_trades"] += 1

            # Update peak balance and drawdown
            if self.performance_data["current_balance"] > self.performance_data["peak_balance"]:
                self.performance_data["peak_balance"] = self.performance_data["current_balance"]

            current_drawdown = (self.performance_data["peak_balance"] - self.performance_data["current_balance"]) / self.performance_data["peak_balance"]
            if current_drawdown > self.performance_data["max_drawdown"]:
                self.performance_data["max_drawdown"] = current_drawdown

            # Add to trade history
            trade_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": trade_data.get("symbol"),
                "side": trade_data.get("side"),
                "amount": trade_data.get("amount"),
                "price": trade_data.get("price"),
                "pnl": trade_pnl,
                "balance_after": self.performance_data["current_balance"]
            }
            self.performance_data["trade_history"].append(trade_record)

            # Limit trade history size
            if len(self.performance_data["trade_history"]) > 1000:
                self.performance_data["trade_history"] = self.performance_data["trade_history"][-500:]

            # Update daily P&L tracking
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in self.performance_data["daily_pnl"]:
                self.performance_data["daily_pnl"][today] = 0.0
            self.performance_data["daily_pnl"][today] += trade_pnl

            # Update timestamp and save
            self.performance_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._save_performance_data()

            logger.info(f"Trade recorded: {trade_data.get('symbol')} {trade_pnl:+.4f} USD")

        except Exception as e:
            logger.error(f"Error recording trade: {e}")

    def _save_performance_data(self):
        """Save performance data to file"""
        try:
            if self.config.performance_file:
                with open(self.config.performance_file, 'w') as f:
                    json.dump(self.performance_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        total_trades = self.performance_data["total_trades"]
        winning_trades = self.performance_data["winning_trades"]

        metrics = {
            "starting_balance": self.performance_data["starting_balance"],
            "current_balance": self.performance_data["current_balance"],
            "total_pnl": self.performance_data["total_pnl"],
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": self.performance_data["losing_trades"],
            "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "max_drawdown": self.performance_data["max_drawdown"] * 100,
            "return_percentage": (self.performance_data["total_pnl"] / self.performance_data["starting_balance"]) * 100,
            "last_updated": self.performance_data["last_updated"]
        }

        # Calculate additional metrics
        if total_trades > 0:
            metrics["average_trade_pnl"] = self.performance_data["total_pnl"] / total_trades

            # Calculate Sharpe ratio (simplified)
            trade_returns = [t.get("pnl", 0) for t in self.performance_data["trade_history"]]
            if len(trade_returns) > 1:
                import statistics
                mean_return = statistics.mean(trade_returns)
                std_return = statistics.stdev(trade_returns)
                metrics["sharpe_ratio"] = (mean_return / std_return) if std_return > 0 else 0
            else:
                metrics["sharpe_ratio"] = 0
        else:
            metrics["average_trade_pnl"] = 0
            metrics["sharpe_ratio"] = 0

        return metrics

    def generate_report(self, executor=None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_metrics = self.get_current_metrics()

        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'session_start': self.session_start.isoformat(),
            'session_duration_hours': (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600,
            'paper_trading_config': self.config.to_dict(),
            'performance_metrics': current_metrics,
            'recent_trades': self.performance_data["trade_history"][-10:],  # Last 10 trades
            'daily_pnl': self.performance_data["daily_pnl"],
            'risk_analysis': self._calculate_risk_metrics(),
            'recommendations': self._generate_recommendations(current_metrics)
        }

        # Save report
        if self.config.generate_reports:
            self._save_report(report)

        return report

    def _calculate_risk_metrics(self) -> Dict[str, Any]:
        """Calculate risk-related metrics"""
        try:
            trade_returns = [t.get("pnl", 0) for t in self.performance_data["trade_history"]]

            if len(trade_returns) < 2:
                return {"insufficient_data": True}

            import statistics

            # Calculate VaR (Value at Risk) at 95% confidence
            sorted_returns = sorted(trade_returns)
            var_95_index = int(len(sorted_returns) * 0.05)
            var_95 = sorted_returns[var_95_index] if var_95_index < len(sorted_returns) else sorted_returns[0]

            # Calculate maximum consecutive losses
            consecutive_losses = 0
            max_consecutive_losses = 0
            for trade in self.performance_data["trade_history"]:
                if trade.get("pnl", 0) < 0:
                    consecutive_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                else:
                    consecutive_losses = 0

            return {
                "var_95": var_95,
                "volatility": statistics.stdev(trade_returns),
                "max_consecutive_losses": max_consecutive_losses,
                "current_consecutive_losses": consecutive_losses,
                "worst_trade": min(trade_returns),
                "best_trade": max(trade_returns)
            }
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {"error": str(e)}

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
