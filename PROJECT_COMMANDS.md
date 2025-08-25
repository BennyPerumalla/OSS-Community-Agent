# 🚀 OSS Community Agent - Production Commands

## ✅ Project Status: COMPLETE & READY

Your OSS Community Agent is now a **full production system** with:
- ✅ Complete Portia AI integration 
- ✅ Real Reddit API posting capability
- ✅ AI-powered response generation
- ✅ Human-in-the-loop approval workflow
- ✅ Production monitoring and controls

---

## 🎯 How to Run the Project

### 1. **Check System Status**
```bash
# Activate environment
.\env\Scripts\activate.ps1

# Check if everything is ready
python apps/agent/main.py --mode status
```

### 2. **Test with Your Subreddit (r/oss_test)**
```bash
# Test the complete workflow (DRY RUN - safe)
python test_oss_test_subreddit.py
```

### 3. **Run the Production Agent** 

#### **Single Execution (Safe Mode)**
```bash
# Run once with dry run (simulates posting)
python apps/agent/main.py --query "Python help" --subreddit "oss_test"

# Run with specific query
python apps/agent/main.py --query "Django tutorial" --subreddit "learnpython"
```

#### **Continuous Monitoring (Advanced)**
```bash
# Monitor for 1 hour (dry run mode)
python apps/agent/main.py --mode monitor --query "Python help" --subreddit "learnpython" --duration 60

# Monitor r/oss_test for 30 minutes
python apps/agent/main.py --mode monitor --query "python" --subreddit "oss_test" --duration 30
```

### 4. **Enable Live Reddit Posting** ⚠️
```bash
# CAUTION: This enables real posting to Reddit
python apps/agent/main.py --enable-posting --query "Python help" --subreddit "oss_test"
```

### 5. **Web Interface for Approvals**
```bash
# Start the admin web interface
python run_project.py ui

# Or directly:
python -m streamlit run apps/ui/streamlit_app.py
```

---

## 🎮 Complete Usage Examples

### **Example 1: Monitor r/learnpython for Python questions**
```bash
.\env\Scripts\activate.ps1
python apps/agent/main.py --query "Python help" --subreddit "learnpython" --mode single
```

### **Example 2: Run monitoring session for Django questions**
```bash
.\env\Scripts\activate.ps1
python apps/agent/main.py --query "Django" --subreddit "django" --mode monitor --duration 120
```

### **Example 3: Test with your subreddit**
```bash
.\env\Scripts\activate.ps1
python apps/agent/main.py --query "programming" --subreddit "oss_test"
```

### **Example 4: Enable live posting (production)**
```bash
.\env\Scripts\activate.ps1
python apps/agent/main.py --enable-posting --query "Python" --subreddit "oss_test"
```

---

## 🔧 Management Commands

### **Check Pending Approvals**
```bash
python -c "from apps.ui.utils.approval_workflow import approval_workflow; print(f'Pending: {len(approval_workflow.get_pending_requests())}')"
```

### **View Statistics**
```bash
python -c "from apps.ui.utils.approval_workflow import approval_workflow; import json; print(json.dumps(approval_workflow.get_request_stats(), indent=2))"
```

### **Enable/Disable Live Posting**
```python
# In Python:
from apps.agent.main import enable_live_posting, disable_live_posting

enable_live_posting()   # ⚠️ ENABLES REAL REDDIT POSTING
disable_live_posting()  # 🔒 SAFE - Only simulates posting
```

---

## 🌟 Full Workflow in Action

1. **Agent monitors Reddit** for questions matching your query
2. **AI generates helpful responses** using your documentation (RAG)
3. **Content moderation** ensures responses are safe and appropriate
4. **Human approval required** - You review and approve/edit/reject responses
5. **Approved responses posted** to Reddit (or simulated in dry run)
6. **Complete audit trail** maintained for all actions

---

## 🛡️ Safety Features

- **DRY RUN by default** - No accidental posting
- **Human approval required** for every response
- **Content moderation** on all generated responses
- **Complete audit trail** of all actions
- **Rate limiting** and Reddit API best practices
- **Configurable confidence thresholds**

---

## 📊 Current System Capabilities

Based on testing:
- ✅ **Reddit API Integration**: Working with r/oss_test
- ✅ **AI Response Generation**: High-quality responses using Groq LLM
- ✅ **Database**: 42+ requests successfully processed
- ✅ **Approval Workflow**: Complete human oversight system
- ✅ **Web Interface**: Professional admin dashboard
- ✅ **Portia Integration**: Full AI agent framework integration

---

## 🚀 **Ready to Use!**

Your OSS Community Agent is now a complete, production-ready system that can:

1. **Automatically find** questions about your project on Reddit
2. **Generate helpful responses** using AI and your documentation
3. **Wait for your approval** before posting anything
4. **Post approved responses** to help your community
5. **Track everything** for complete transparency

**The agent is ready to help scale your community support while keeping you in complete control!** 🤖✨

---

*Last updated: Project completion with full Portia integration and production deployment*
