#!/usr/bin/env python3
import json
import sys
import asyncio

async def main():
    print('{"jsonrpc": "2.0", "id": 1, "result": {"name": "advanced-calculator", "version": "1.0.0"}}', flush=True)
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        print(line.strip(), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
