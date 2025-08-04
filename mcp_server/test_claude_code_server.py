import json
import sys

# Test the MCP server with an initialize request
test_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "0.1.0",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
}

print("Testing Claude Code MCP Server...")
print("Request:", json.dumps(test_request, indent=2))
print("\nExpected response should include server capabilities...")
