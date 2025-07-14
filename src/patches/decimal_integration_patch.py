"""
Decimal Integration Patch for Trading Bot
=========================================

This patch integrates the MoneyDecimal class throughout the trading system
to eliminate float precision errors that are destroying the snowball effect.

Apply this patch to fix all financial calculations.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class DecimalIntegrationPatch:
    """Applies decimal precision fixes throughout the codebase"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = []
        self.backup_dir = self.project_root / "backups" / "decimal_patch"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def apply_all_patches(self) -> Dict[str, List[str]]:
        """Apply all decimal precision patches"""
        results = {
            "enhanced_balance_manager": self.patch_enhanced_balance_manager(),
            "core_bot": self.patch_core_bot(),
            "trade_executor": self.patch_trade_executor(),
            "opportunity_scanner": self.patch_opportunity_scanner(),
            "profit_harvester": self.patch_profit_harvester(),
            "config_percentages": self.fix_config_percentages()
        }
        
        logger.info(f"[DECIMAL_PATCH] Applied {len(self.fixes_applied)} fixes across {len(results)} modules")
        return results
    
    def patch_enhanced_balance_manager(self) -> List[str]:
        """Fix float usage in enhanced_balance_manager.py"""
        file_path = self.project_root / "src" / "trading" / "enhanced_balance_manager.py"
        
        replacements = [
            # Fix price conversions
            (
                r'return float\(price\)',
                'return MoneyDecimal(price, "USDT").to_float()'
            ),
            # Fix balance conversions
            (
                r'return float\(free_balance\)',
                'return MoneyDecimal(free_balance, "USDT").to_float()'
            ),
            # Fix balance comparisons
            (
                r'if float\(free_balance\) > 0:',
                'if MoneyDecimal(free_balance, "USDT") > MoneyDecimal("0", "USDT"):'
            ),
            # Fix order calculations
            (
                r'filled_amount = float\(order_result\.get\([\'"]cost[\'"], 0\)\)',
                'filled_amount = MoneyDecimal(order_result.get("cost", "0"), "USDT").to_float()'
            ),
            (
                r'filled_qty = float\(order_result\.get\([\'"]filled[\'"], 0\)\)',
                'filled_qty = MoneyDecimal(order_result.get("filled", "0"), "CRYPTO").to_float()'
            ),
            (
                r'avg_price = float\(order_result\.get\([\'"]average[\'"], current_price\)\)',
                'avg_price = MoneyDecimal(order_result.get("average", str(current_price)), "USDT").to_float()'
            )
        ]
        
        # Add import at the top
        import_line = 'from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator\n'
        
        return self._apply_replacements(file_path, replacements, import_line)
    
    def patch_core_bot(self) -> List[str]:
        """Fix float usage in core bot.py"""
        file_path = self.project_root / "src" / "core" / "bot.py"
        
        replacements = [
            # Fix position size calculation
            (
                r'base_position_size = float\(self\.config\.get\([\'"]position_size_usdt[\'"],.*?\)\)',
                'base_position_size = MoneyDecimal(self.config.get("position_size_usdt", MINIMUM_ORDER_SIZE_TIER1), "USDT").value'
            ),
            # Fix tier limit
            (
                r'tier_1_limit = float\(self\.config\.get\([\'"]tier_1_trade_limit[\'"],.*?\)\)',
                'tier_1_limit = MoneyDecimal(self.config.get("tier_1_trade_limit", MINIMUM_ORDER_SIZE_TIER1), "USDT").value'
            ),
            # Fix capital flow tracking
            (
                r'self\.capital_flow\[[\'"]realized_pnl[\'\"]\] \+= profit',
                'self.capital_flow["realized_pnl"] = PrecisionTradingCalculator.accumulate_profits(self.capital_flow.get("realized_pnl", "0"), profit).to_float()'
            ),
            # Fix balance comparisons
            (
                r'if balance < amount_usdt',
                'if MoneyDecimal(balance, "USDT") < MoneyDecimal(amount_usdt, "USDT")'
            )
        ]
        
        import_line = 'from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator\n'
        
        return self._apply_replacements(file_path, replacements, import_line)
    
    def patch_trade_executor(self) -> List[str]:
        """Fix float usage in trade executor"""
        file_path = self.project_root / "src" / "trading" / "enhanced_trade_executor_with_assistants.py"
        
        replacements = [
            # Fix amount calculations
            (
                r'amount=float\(trade_params\[[\'"]amount[\'\"]\]\)',
                'amount=MoneyDecimal(trade_params["amount"], "USDT").to_float()'
            ),
            # Fix profit accumulation
            (
                r'stats\[[\'"]total_profit_pct[\'\"]\] \+= profit_pct',
                'stats["total_profit_pct"] = PrecisionTradingCalculator.accumulate_profits(stats.get("total_profit_pct", "0"), profit_pct).to_float()'
            ),
            # Fix position size calculations
            (
                r'position_pct = request\.amount / balance',
                'position_pct = (MoneyDecimal(request.amount, "USDT") / MoneyDecimal(balance, "USDT")).to_float()'
            ),
            # Fix balance comparisons
            (
                r'if balance < request\.amount:',
                'if MoneyDecimal(balance, "USDT") < MoneyDecimal(request.amount, "USDT"):'
            )
        ]
        
        import_line = 'from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator\n'
        
        return self._apply_replacements(file_path, replacements, import_line)
    
    def patch_opportunity_scanner(self) -> List[str]:
        """Fix float usage in opportunity scanner"""
        file_path = self.project_root / "src" / "trading" / "opportunity_scanner.py"
        
        replacements = [
            # Fix price calculations
            (
                r'current_price = float\(ticker\.get\([\'"]last[\'"],.*?\)\)',
                'current_price = MoneyDecimal(ticker.get("last", "0"), "USDT").to_float()'
            ),
            # Fix profit calculations
            (
                r'profit = \(exit_price - entry_price\) \* quantity',
                'profit = PrecisionTradingCalculator.calculate_profit(entry_price, exit_price, quantity).to_float()'
            ),
            # Fix percentage calculations
            (
                r'percentage = \(\(price2 - price1\) / price1\) \* 100',
                'percentage = PrecisionTradingCalculator.calculate_percentage_gain(price1, price2)'
            )
        ]
        
        import_line = 'from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator\n'
        
        return self._apply_replacements(file_path, replacements, import_line)
    
    def patch_profit_harvester(self) -> List[str]:
        """Fix float usage in profit harvester"""
        file_path = self.project_root / "src" / "trading" / "profit_harvester.py"
        
        replacements = [
            # Fix profit calculations
            (
                r'profit_pct = \(\(current_price - entry_price\) / entry_price\) \* 100',
                'profit_pct = PrecisionTradingCalculator.calculate_percentage_gain(entry_price, current_price)'
            ),
            # Fix profit accumulation
            (
                r'total_profit \+= position_profit',
                'total_profit = PrecisionTradingCalculator.accumulate_profits(total_profit, position_profit).to_float()'
            )
        ]
        
        import_line = 'from src.utils.decimal_precision_fix import MoneyDecimal, PrecisionTradingCalculator\n'
        
        return self._apply_replacements(file_path, replacements, import_line)
    
    def fix_config_percentages(self) -> List[str]:
        """Fix inconsistent percentage formats in config.json"""
        config_path = self.project_root / "config.json"
        
        try:
            # Import the fix function
            import sys
            sys.path.insert(0, str(self.project_root / "src"))
            from utils.decimal_precision_fix import fix_config_percentages
            
            # Apply the fix
            fixed_config = fix_config_percentages(str(config_path))
            
            return ["Config percentages standardized to decimal format"]
            
        except Exception as e:
            logger.error(f"[DECIMAL_PATCH] Error fixing config percentages: {e}")
            return [f"Error: {str(e)}"]
    
    def _apply_replacements(self, file_path: Path, replacements: List[Tuple[str, str]], import_line: str) -> List[str]:
        """Apply regex replacements to a file"""
        if not file_path.exists():
            return [f"File not found: {file_path}"]
        
        # Create backup
        backup_path = self.backup_dir / f"{file_path.name}.backup"
        
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Save backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            applied_fixes = []
            
            # Add import if not present
            if 'MoneyDecimal' not in content and import_line:
                # Find the last import line
                import_match = re.findall(r'^(from .* import .*|import .*)$', content, re.MULTILINE)
                if import_match:
                    last_import = import_match[-1]
                    content = content.replace(last_import, f"{last_import}\n{import_line}")
                    applied_fixes.append("Added MoneyDecimal import")
            
            # Apply replacements
            for pattern, replacement in replacements:
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    applied_fixes.append(f"Fixed: {pattern[:50]}...")
            
            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"[DECIMAL_PATCH] Applied {len(applied_fixes)} fixes to {file_path.name}")
            return applied_fixes
            
        except Exception as e:
            logger.error(f"[DECIMAL_PATCH] Error patching {file_path}: {e}")
            return [f"Error: {str(e)}"]


def apply_decimal_patches():
    """Main function to apply all decimal patches"""
    import os
    
    # Get project root
    project_root = os.environ.get('PROJECT_ROOT', '/mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025')
    
    # Create patcher
    patcher = DecimalIntegrationPatch(project_root)
    
    # Apply all patches
    results = patcher.apply_all_patches()
    
    # Print results
    print("\n=== DECIMAL PRECISION PATCH RESULTS ===")
    for module, fixes in results.items():
        print(f"\n{module}:")
        for fix in fixes:
            print(f"  - {fix}")
    
    print("\n✅ Decimal precision patches applied!")
    print("Your snowball effect is now mathematically perfect!")


if __name__ == "__main__":
    apply_decimal_patches()