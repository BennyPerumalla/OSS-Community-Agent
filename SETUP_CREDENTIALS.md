# 🔑 Setting Up API Credentials for OSS Community Agent

Your OSS Community Agent is **98% ready**! You just need to configure API credentials to enable live Reddit posting and AI responses.

## ✅ What's Already Working

- 🔄 **Approval Workflow System** - Complete human-in-the-loop process
- 📝 **Draft Generation** - RAG-based response creation
- 🛡️ **Safety & Moderation** - Content filtering and safety checks  
- 📊 **Database & Tracking** - Full audit trail and statistics
- 🌐 **Web UI** - Streamlit admin interface
- 📱 **Reddit Posting** - Ready to post (in dry-run mode)
- 🤖 **Portia Integration** - AI orchestration framework

## 🚀 Quick Start (5 minutes)

### 1. Get Reddit API Credentials

1. **Go to Reddit Apps**: https://www.reddit.com/prefs/apps
2. **Click "Create App"** (or "Create Another App")
3. **Fill out the form**:
   - **Name**: `OSS Community Agent`
   - **App type**: Select **"script"**
   - **Description**: `AI assistant for community support`
   - **About URL**: `https://github.com/your-username/oss-community-agent`
   - **Redirect URI**: `http://localhost:8000` (required but not used)
4. **Click "Create app"**
5. **Copy your credentials**:
   - **Client ID**: The string under your app name (looks like: `abc123XYZ`)
   - **Client Secret**: The "secret" string (looks like: `xyz789ABC-def456GHI`)

### 2. Get Groq API Key (Free!)

1. **Go to Groq Console**: https://console.groq.com/
2. **Sign up/Login** with Google or GitHub
3. **Go to API Keys**: https://console.groq.com/keys
4. **Create New Key**: Click "Create API Key"
5. **Copy the key** (starts with `gsk_...`)

### 3. Update Your .env File

Open `.env` in your project root and update these values:

```bash
# Reddit API
REDDIT_CLIENT_ID=your_client_id_from_step_1
REDDIT_CLIENT_SECRET=your_client_secret_from_step_1  
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Groq AI (Free)
GROQ_API_KEY=your_groq_api_key_from_step_2
```

### 4. Test Your Setup

```bash
# Activate your virtual environment
.\env\Scripts\Activate.ps1

# Run the comprehensive test
python test_reddit_posting.py
```

You should see: **5/5 tests passed** ✅

## 🛡️ Safety Features

- **DRY_RUN=true** by default (simulates posting without actually posting)
- **Human approval required** for every response
- **Content moderation** checks all generated content
- **Rate limiting** prevents spam
- **Full audit trail** of all actions

## 🎯 Ready to Go Live?

Once you've tested everything:

1. **Choose your target subreddit** (start with a test subreddit you moderate)
2. **Add your documentation** to `data/corpus/` folder
3. **Set DRY_RUN=false** in `.env` when ready for live posting
4. **Start the system**: `python run_full_system.py`

## 📊 System Status After Setup

```bash
🎉 All systems working! Your OSS Community Agent is ready!

✅ Reddit API Integration
✅ AI Response Generation  
✅ Human Approval Workflow
✅ Safe Posting System
✅ Web Admin Interface
✅ Complete Audit Trail
```

## 🔧 Alternative APIs

### If you prefer OpenAI instead of Groq:

```bash
# In .env file:
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
```

### If you want to use local AI models:

```bash
# In .env file:
LLM_PROVIDER=ollama
EMBED_PROVIDER=ollama
# Then install Ollama and run: ollama pull gemma:2b
```

## 🚨 Important Notes

- **Start with DRY_RUN=true** to test safely
- **Use a test subreddit first** (like r/test)
- **Review all generated responses** before posting
- **Reddit API has rate limits** - the agent respects them
- **Keep your credentials secure** - never commit them to git

## 🎊 You're All Set!

Your OSS Community Agent is now ready to help scale your community support while maintaining complete human oversight and control.

**Next Steps:**
1. Configure credentials (above)
2. Test with `python test_reddit_posting.py`
3. Add your docs to `data/corpus/`
4. Start the UI with `python run_ui.py`
5. Go live when ready!

---

**Need Help?** Check the existing documentation or create an issue on GitHub.
