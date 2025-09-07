#!/usr/bin/env python3
"""
Test script to verify the TaskResponse parsing fix.
"""

import asyncio
from src.agents.common.tool_client import A2AToolClient

async def test_response_parsing():
    """Test that the TaskResponse parsing fix works correctly."""
    
    print("🧪 Testing TaskResponse Parsing Fix")
    print("=" * 50)
    
    client = A2AToolClient()
    
    # Register the orchestration agent
    client.add_remote_agent("http://localhost:10024")
    
    print("🔄 Testing orchestration agent response parsing...")
    
    try:
        result = await client.create_task(
            "http://localhost:10024",
            "What agents are available?"
        )
        
        print(f"✅ Response parsing successful!")
        print(f"   Task ID: {result.id}")
        print(f"   Status: {result.status}")
        print(f"   Artifacts count: {len(result.artifacts)}")
        
        if result.artifacts and result.artifacts[0].parts:
            print(f"   Response preview: {result.artifacts[0].parts[0].text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Response parsing failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_response_parsing())
    if success:
        print("\n🎉 Fix verified successfully!")
    else:
        print("\n💥 Fix needs more work.")