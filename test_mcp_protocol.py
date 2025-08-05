#!/usr/bin/env python3
"""
Test script for MCP SSE protocol flow:
1. Connect to /sse endpoint to get session ID
2. Use session ID to call /messages endpoint
3. Send MCP protocol messages to get tools list
"""

import asyncio
import json
import uuid
import aiohttp
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_mcp_protocol(timeout=30):
    """Test the full MCP protocol flow."""
    
    print("🚀 Testing MCP SSE Protocol Flow")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Step 1: Connect to SSE endpoint to get session ID
        print("\n📡 Step 1: Connecting to SSE endpoint...")
        try:
            async with session.get(f"{BASE_URL}/sse") as response:
                print(f"SSE Response Status: {response.status}")
                print(f"SSE Response Headers: {dict(response.headers)}")
                
                # Read the SSE stream to get session ID
                session_id = None
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    print(f"SSE Line: {line_str}")
                    
                    # Look for session ID in the SSE data
                    if "session_id=" in line_str:
                        # Extract session ID from the line
                        import re
                        match = re.search(r'session_id=([a-f0-9]+)', line_str)
                        if match:
                            session_id = match.group(1)
                            print(f"✅ Found Session ID: {session_id}")
                            break
                    
                    # Break after a few lines to avoid hanging
                    if "ping" in line_str.lower():
                        break
                        
        except Exception as e:
            print(f"❌ SSE Connection Error: {e}")
            return False
            
        if not session_id:
            print("❌ Failed to get session ID from SSE endpoint")
            return False
            
        # Step 2: Test the messages endpoint with session ID
        print(f"\n📨 Step 2: Testing messages endpoint with session ID...")
        messages_url = f"{BASE_URL}/messages/?session_id={session_id}"
        print(f"Messages URL: {messages_url}")
        
        # Step 3: Send MCP initialize request
        print(f"\n🔧 Step 3: Sending MCP initialize request...")
        
        initialize_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            async with session.post(
                messages_url,
                json=initialize_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Initialize Response Status: {response.status}")
                if response.status == 202:
                    print("✅ Initialize request accepted (202 Accepted)")
                    init_response = {"status": "accepted"}
                else:
                    try:
                        init_response = await response.json()
                        print(f"Initialize Response: {json.dumps(init_response, indent=2)}")
                    except:
                        init_text = await response.text()
                        print(f"Initialize Response (text): {init_text[:200]}...")
                
        except Exception as e:
            print(f"❌ Initialize Request Error: {e}")
            return False
            
        # Step 4: Send tools/list request to get available tools
        print(f"\n🛠️  Step 4: Requesting tools list...")
        
        tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        
        try:
            async with session.post(
                messages_url,
                json=tools_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Tools List Response Status: {response.status}")
                try:
                    tools_response = await response.json()
                    print(f"Tools List Response: {json.dumps(tools_response, indent=2)}")
                except:
                    tools_text = await response.text()
                    print(f"Tools List Response (text): {tools_text[:200]}...")
                    tools_response = {"result": {"tools": []}}
                
                # Count and display tools
                if "result" in tools_response and "tools" in tools_response["result"]:
                    tools = tools_response["result"]["tools"]
                    print(f"\n✅ Found {len(tools)} tools:")
                    for i, tool in enumerate(tools[:5], 1):  # Show first 5 tools
                        print(f"  {i}. {tool.get('name', 'Unknown')} - {tool.get('description', 'No description')[:60]}...")
                    
                    if len(tools) > 5:
                        print(f"  ... and {len(tools) - 5} more tools")
                        
                    return True
                else:
                    print("❌ No tools found in response")
                    return False
                    
        except Exception as e:
            print(f"❌ Tools List Request Error: {e}")
            return False

async def test_health_endpoint():
    """Test the health endpoint."""
    print("\n🏥 Testing Health Endpoint...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/health") as response:
                print(f"Health Response Status: {response.status}")
                health_text = await response.text()
                print(f"Health Response: {health_text}")
                return response.status == 200
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False

async def main():
    """Main test function."""
    print(f"🧪 MCP Protocol Test Suite")
    print(f"⏰ Started at: {datetime.now()}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Test health endpoint first
    health_ok = await test_health_endpoint()
    if not health_ok:
        print("❌ Health check failed - server may not be running")
        sys.exit(1)
    
    # Wait a moment for the server to be fully ready
    print("⏳ Waiting for server to be fully ready...")
    await asyncio.sleep(2)
    
    # Test full MCP protocol
    protocol_ok = await test_mcp_protocol()
    
    print("\n" + "=" * 50)
    if protocol_ok:
        print("✅ MCP Protocol Test: PASSED")
        print("🎉 Your telegram-mcp server is working correctly!")
    else:
        print("❌ MCP Protocol Test: FAILED")
        print("🔧 Check the server logs for more details")
        sys.exit(1)

if __name__ == "__main__":
    # Install required dependency if not present
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp
        
    # Set longer timeout for aiohttp
    timeout = aiohttp.ClientTimeout(total=30)
    
    asyncio.run(main())
