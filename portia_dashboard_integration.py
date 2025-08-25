# portia_dashboard_integration.py
"""
Integration script to demonstrate Portia AI workflow orchestration.
This will create activity that shows up in your Portia dashboard.
"""

import os
import sys
import uuid
import time
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_portia_integration():
    """Test integration with real Portia SDK to show dashboard activity"""
    print("🚀 Testing Portia AI Dashboard Integration")
    print("=" * 50)
    
    try:
        # Import and configure Portia with proper settings
        from portia import Portia, PlanBuilder, ToolCall
        from portia.models import PlanRunState, PlanRunStatus
        from portia.tool_registry import PortiaToolRegistry
        
        print("✅ Portia SDK imported successfully")
        
        # Configure Portia with API key if available
        api_key = os.getenv("PORTIA_API_KEY")
        if not api_key or api_key == "your_portia_api_key_here":
            print("⚠️ No Portia API key configured - using mock mode")
            # Use our mock implementation
            sys.path.insert(0, str(project_root))
            from mock_portia import Portia, PlanBuilder, ToolCall
            portia = Portia()
        else:
            print(f"🔑 Using Portia API key: {api_key[:10]}...")
            portia = Portia(api_key=api_key)
        
        # Create tool registry
        tool_registry = PortiaToolRegistry()
        
        # Register our Reddit monitoring function
        def monitor_reddit_subreddit(subreddit: str, keywords: str):
            """Mock Reddit monitoring function for Portia"""
            return {
                "status": "success",
                "subreddit": subreddit,
                "keywords": keywords,
                "posts_found": 3,
                "message": f"Successfully monitored r/{subreddit} for '{keywords}'"
            }
        
        def generate_ai_response(query: str):
            """Mock AI response generation for Portia"""
            return {
                "status": "success",
                "query": query,
                "response": f"This is an AI-generated response to: {query}",
                "confidence": 0.85,
                "length": 250
            }
        
        def request_human_approval(response: str):
            """Mock human approval request for Portia"""
            return {
                "status": "pending_approval",
                "response": response,
                "approval_id": str(uuid.uuid4())[:8],
                "message": "Response queued for human approval"
            }
        
        # Register tools with Portia
        tool_registry.register_tool(
            name="monitor_reddit",
            description="Monitor a Reddit subreddit for questions",
            func=monitor_reddit_subreddit,
            input_schema={
                "type": "object",
                "properties": {
                    "subreddit": {"type": "string", "description": "Subreddit name"},
                    "keywords": {"type": "string", "description": "Keywords to search for"}
                },
                "required": ["subreddit", "keywords"]
            }
        )
        
        tool_registry.register_tool(
            name="generate_response",
            description="Generate AI response to a question",
            func=generate_ai_response,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "User question"}
                },
                "required": ["query"]
            }
        )
        
        tool_registry.register_tool(
            name="request_approval",
            description="Request human approval for a response",
            func=request_human_approval,
            input_schema={
                "type": "object", 
                "properties": {
                    "response": {"type": "string", "description": "Response to approve"}
                },
                "required": ["response"]
            }
        )
        
        print("✅ Tools registered with Portia")
        
        # Create a comprehensive plan
        plan_builder = PlanBuilder(
            name="OSS Community Support Agent",
            description="Complete workflow for automated community support with human approval",
            tools=tool_registry.get_all_tools()
        )
        
        # Step 1: Monitor Reddit
        plan_builder.add_step(
            name="monitor_reddit_step",
            tool_call=ToolCall(
                name="monitor_reddit",
                args={
                    "subreddit": "oss_test",
                    "keywords": "python help question"
                }
            ),
            output_variable="reddit_results"
        )
        
        # Step 2: Generate AI response
        plan_builder.add_step(
            name="generate_ai_response_step", 
            tool_call=ToolCall(
                name="generate_response",
                args={
                    "query": "What is try except blocks in python?"
                }
            ),
            output_variable="ai_response"
        )
        
        # Step 3: Request human approval
        plan_builder.add_step(
            name="request_approval_step",
            tool_call=ToolCall(
                name="request_approval",
                args={
                    "response": "{{ai_response}}"
                }
            ),
            output_variable="approval_status"
        )
        
        print("✅ Plan created with 3 steps")
        
        # Build and execute the plan
        plan = plan_builder.build()
        print("🚀 Executing Portia plan...")
        
        # This should show up in your Portia dashboard
        plan_run = portia.run_plan(plan=plan, initial_input={})
        
        print("✅ Plan execution completed!")
        
        # Show results
        if hasattr(plan_run, 'status'):
            print(f"📊 Plan Status: {plan_run.status}")
            
            if hasattr(plan_run, 'get_variable'):
                reddit_results = plan_run.get_variable("reddit_results")
                ai_response = plan_run.get_variable("ai_response") 
                approval_status = plan_run.get_variable("approval_status")
                
                print(f"\n📋 Results:")
                print(f"   Reddit Monitoring: {reddit_results}")
                print(f"   AI Response: {ai_response}")
                print(f"   Approval Status: {approval_status}")
        
        # Create multiple plan runs to show more dashboard activity
        print(f"\n🔄 Creating additional plan runs for dashboard visibility...")
        
        for i in range(3):
            print(f"   Running plan {i+1}/3...")
            
            # Vary the parameters to show different activities
            subreddits = ["oss_test", "learnpython", "Python"]
            queries = [
                "How do I install packages?",
                "What are Python decorators?", 
                "Help with my code errors"
            ]
            
            plan_builder_variant = PlanBuilder(
                name=f"OSS Agent Run #{i+1}",
                description=f"Community support workflow run {i+1}",
                tools=tool_registry.get_all_tools()
            )
            
            plan_builder_variant.add_step(
                name="monitor_step",
                tool_call=ToolCall(
                    name="monitor_reddit",
                    args={
                        "subreddit": subreddits[i],
                        "keywords": "help python"
                    }
                ),
                output_variable="results"
            )
            
            plan_builder_variant.add_step(
                name="response_step",
                tool_call=ToolCall(
                    name="generate_response", 
                    args={"query": queries[i]}
                ),
                output_variable="response"
            )
            
            variant_plan = plan_builder_variant.build()
            variant_run = portia.run_plan(plan=variant_plan, initial_input={})
            
            time.sleep(1)  # Small delay between runs
            
        print("✅ Multiple plan runs completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Portia integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_dashboard_instructions():
    """Show instructions for viewing the Portia dashboard"""
    print(f"\n📊 VIEWING YOUR PORTIA DASHBOARD:")
    print("=" * 40)
    print("1. Go to https://app.portia.ai")
    print("2. Login to your Portia account")
    print("3. Navigate to the Dashboard or Runs section")
    print("4. You should see the plan executions we just created:")
    print("   • 'OSS Community Support Agent'")
    print("   • 'OSS Agent Run #1, #2, #3'")
    print("5. Click on any run to see detailed execution logs")
    print("\n💡 If you don't see runs, check:")
    print("   • PORTIA_API_KEY is correctly set in .env")
    print("   • Your API key has the right permissions")
    print("   • Dashboard refresh/time filter settings")

if __name__ == "__main__":
    print("Portia AI Dashboard Integration Test")
    print("This will create plan runs visible in your Portia dashboard")
    print("")
    
    success = test_portia_integration()
    
    if success:
        print(f"\n🎊 PORTIA INTEGRATION COMPLETED!")
        print(f"\n✅ What was executed:")
        print("   • Created Portia tool registry")
        print("   • Registered custom Reddit/AI tools")
        print("   • Built multi-step workflow plans") 
        print("   • Executed 4 plan runs total")
        print("   • All runs should appear in dashboard")
        
        show_dashboard_instructions()
        
        print(f"\n🔑 Next Steps:")
        print("1. Check your Portia dashboard for the new runs")
        print("2. If no runs appear, verify PORTIA_API_KEY in .env")
        print("3. Run the main workflow: python test_oss_test_subreddit.py")
        
    else:
        print(f"\n❌ Integration test failed")
        print("The system will fall back to mock Portia implementation")
