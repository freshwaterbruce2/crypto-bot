#!/usr/bin/env python3
"""
Non-interactive runner for master automated finisher
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from master_automated_finisher import MasterProjectFinisher
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run master finisher without interaction"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║           MASTER AUTOMATED PROJECT FINISHER                    ║
║                                                                ║
║  Running automated project completion...                       ║
║                                                                ║
║  • Web search verification for solutions                      ║
║  • Market analysis and strategy optimization                  ║
║  • Automated issue detection and resolution                   ║
║  • Continuous profit monitoring                               ║
║  • Risk management validation                                 ║
║                                                                ║
║  Estimated completion time: 30-60 minutes                     ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n🚀 Starting automated process...")
    
    master = MasterProjectFinisher()
    
    try:
        await master.run()
        print("\n✅ Master finishing process completed!")
        print("Check the logs and completion report for details.")
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Master finisher failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())