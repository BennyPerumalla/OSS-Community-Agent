# Contributing to OSS Community Agent 🤖

Thank you for your interest in contributing to the OSS Community Agent! This document provides guidelines and instructions for contributing to our project.

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Getting Started](#-getting-started)
- [Development Setup](#-development-setup)
- [Types of Contributions](#-types-of-contributions)
- [Development Workflow](#-development-workflow)
- [Code Standards](#-code-standards)
- [Testing Guidelines](#-testing-guidelines)
- [Documentation](#-documentation)
- [Pull Request Process](#-pull-request-process)
- [Issue Guidelines](#-issue-guidelines)
- [Community Guidelines](#-community-guidelines)
- [Getting Help](#-getting-help)

## 🤝 Code of Conduct

This project follows a [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming and inclusive environment for all contributors. Please read and follow it in all your interactions with the project.

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (required for Portia AI SDK)
- **Git** for version control
- **Reddit API credentials** (for testing Reddit integration)
- **Groq API key** (for testing AI features)
- Basic knowledge of:
  - Python programming
  - Git/GitHub workflow
  - AI/ML concepts (helpful but not required)

### First Time Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/oss-community-agent.git
   cd oss-community-agent
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/BennyPerumalla/oss-community-agent.git
   ```
4. **Set up development environment** (see [Development Setup](#-development-setup))

## 🛠️ Development Setup

### Method 1: Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r infra/requirements.txt
uv pip install -r infra/requirements-dev.txt  # Development dependencies
```

### Method 2: Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r infra/requirements.txt
pip install -r infra/requirements-dev.txt
```

### Method 3: Using Poetry

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
poetry shell
```

### Environment Configuration

1. **Copy environment template**:

   ```bash
   cp .env.example .env
   ```

2. **Configure your `.env` file**:

   ```bash
   # Reddit API (required for testing)
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USERNAME=your_reddit_username
   REDDIT_PASSWORD=your_reddit_password

   # AI/LLM (required for testing)
   GROQ_API_KEY=your_groq_api_key
   LLM_PROVIDER=groq

   # Safety settings (keep these for development)
   DRY_RUN=true
   AUTO_APPROVAL=false
   ```

3. **Verify setup**:
   ```bash
   python apps/agent/main.py --mode status
   ```

## 🎯 Types of Contributions

We welcome various types of contributions:

### 🐛 Bug Fixes

- Fix bugs in existing functionality
- Improve error handling and resilience
- Optimize performance issues

### ✨ New Features

- Add new tools or integrations
- Enhance the UI/UX
- Implement new AI capabilities
- Add platform integrations (Discord, Slack, etc.)

### 📚 Documentation

- Improve existing documentation
- Add code examples and tutorials
- Create video guides or demos
- Translate documentation

### 🧪 Testing

- Add unit tests for new features
- Improve test coverage
- Add integration tests
- Performance testing

### 🎨 UI/UX Improvements

- Enhance the Streamlit interface
- Improve user experience
- Add new dashboard features
- Mobile responsiveness

### 🔧 DevOps & Infrastructure

- CI/CD improvements
- Docker containerization
- Deployment automation
- Monitoring and logging

## 🔄 Development Workflow

### 1. Choose an Issue

- Look for issues labeled `good first issue` for beginners
- Check `help wanted` for more complex tasks
- Create a new issue if you have an idea

### 2. Create a Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create a new branch for your feature
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Write your code following our [Code Standards](#-code-standards)
- Add tests for new functionality
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run all tests
python run_tests.py

# Run specific test suites
python test_workflow.py
python test_reddit_posting.py
python test_rag_simple.py

# Test the UI
python run_ui.py
```

### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add Discord integration support

- Add Discord bot tool for platform integration
- Implement message monitoring and response posting
- Add Discord-specific configuration options
- Include comprehensive error handling

Fixes #123"
```

### 6. Push and Create PR

```bash
# Push your branch
git push origin feature/your-feature-name

# Create a pull request on GitHub
```

## 📝 Code Standards

### Python Style Guide

- Follow **PEP 8** guidelines
- Use **type hints** for function parameters and return values
- Write **comprehensive docstrings** for all functions and classes
- Keep line length under **88 characters** (Black formatter standard)

### Code Formatting

We use **Black** for code formatting and **isort** for import sorting:

```bash
# Format code
black .

# Sort imports
isort .

# Check formatting
black --check .
isort --check-only .
```

### Type Hints

Always use type hints for better code clarity:

```python
from typing import Dict, List, Optional, Any

def process_reddit_query(
    post_data: Dict[str, Any],
    confidence_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Process a Reddit query through the approval workflow.

    Args:
        post_data: Dictionary containing Reddit post information
        confidence_threshold: Minimum confidence score for processing

    Returns:
        Dictionary with processing results and request ID
    """
    # Implementation here
    pass
```

### Docstring Format

Use Google-style docstrings:

```python
def search_questions(
    self,
    subreddit_name: str,
    keywords: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search a subreddit for posts matching given keywords.

    Args:
        subreddit_name: Name of the subreddit to search
        keywords: Search keywords
        limit: Maximum number of posts to retrieve

    Returns:
        List of dictionaries containing post information

    Raises:
        RedditAPIException: If Reddit API request fails
        ValueError: If invalid parameters provided

    Example:
        >>> reddit_tool = RedditTool(...)
        >>> posts = reddit_tool.search_questions("learnpython", "Python help", 5)
        >>> print(f"Found {len(posts)} posts")
    """
```

### Error Handling

Always include proper error handling:

```python
def safe_api_call(self, func, *args, **kwargs):
    """Execute API call with proper error handling."""
    try:
        return func(*args, **kwargs)
    except RedditAPIException as e:
        logger.error(f"Reddit API error: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"status": "error", "message": "Internal error occurred"}
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions and methods
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows
- **Performance tests**: Test system performance under load

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch
from tools.reddit_tool import RedditTool

class TestRedditTool:
    """Test suite for RedditTool class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reddit_tool = RedditTool(
            client_id="test_id",
            client_secret="test_secret",
            username="test_user",
            password="test_pass",
            user_agent="test_agent"
        )

    def test_search_questions_success(self):
        """Test successful question search."""
        # Mock Reddit API response
        mock_submission = Mock()
        mock_submission.id = "test_id"
        mock_submission.title = "Test Question"
        mock_submission.selftext = "Test content"

        with patch.object(self.reddit_tool.reddit.subreddit, 'search') as mock_search:
            mock_search.return_value = [mock_submission]

            result = self.reddit_tool.search_questions("test_subreddit", "test", 1)

            assert len(result) == 1
            assert result[0]["id"] == "test_id"
            assert result[0]["title"] == "Test Question"

    def test_search_questions_api_error(self):
        """Test handling of Reddit API errors."""
        with patch.object(self.reddit_tool.reddit.subreddit, 'search') as mock_search:
            mock_search.side_effect = RedditAPIException("API Error")

            result = self.reddit_tool.search_questions("test_subreddit", "test", 1)

            assert result == []
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_reddit_tool.py -v

# Run with coverage
python -m pytest --cov=tools tests/

# Run specific test
python -m pytest tests/test_reddit_tool.py::TestRedditTool::test_search_questions_success -v
```

### Test Coverage

- Aim for **80%+ test coverage** for new code
- Test both **success and failure** scenarios
- Include **edge cases** and **boundary conditions**
- Mock external dependencies (APIs, databases)

## 📚 Documentation

### Code Documentation

- **Docstrings**: Every function, class, and module should have docstrings
- **Comments**: Explain complex logic and business rules
- **Type hints**: Use type annotations for better code clarity

### User Documentation

- **README updates**: Update README.md for new features
- **API documentation**: Document new APIs and endpoints
- **Tutorials**: Create step-by-step guides for complex features
- **Examples**: Provide code examples for common use cases

### Documentation Standards

```python
"""
Reddit Tool Module.

This module provides integration with the Reddit API for monitoring
subreddits and posting responses. It includes rate limiting, error
handling, and retry logic for robust operation.

Example:
    >>> reddit_tool = RedditTool(
    ...     client_id="your_id",
    ...     client_secret="your_secret",
    ...     username="your_username",
    ...     password="your_password",
    ...     user_agent="your_agent"
    ... )
    >>> posts = reddit_tool.search_questions("learnpython", "Python help")
"""

class RedditTool:
    """
    Reddit API integration tool with rate limiting and error handling.

    This class provides methods for searching Reddit posts and posting
    replies with automatic rate limiting and retry logic.

    Attributes:
        reddit: PRAW Reddit instance
        _max_retries: Maximum number of retry attempts
        _base_sleep: Base sleep time for exponential backoff
    """
```

## 🔀 Pull Request Process

### Before Submitting

1. **Update your branch** with the latest main:

   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Run all tests** and ensure they pass:

   ```bash
   python run_tests.py
   ```

3. **Check code formatting**:

   ```bash
   black --check .
   isort --check-only .
   ```

4. **Update documentation** if needed

### PR Template

Use this template for your pull request:

```markdown
## Description

Brief description of changes and motivation.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All existing tests pass

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Ready for review

## Related Issues

Fixes #(issue number)

## Screenshots (if applicable)

Add screenshots for UI changes.

## Additional Notes

Any additional information for reviewers.
```

### Review Process

1. **Automated checks** must pass (tests, formatting, linting)
2. **Code review** by at least one maintainer
3. **Testing** by maintainers on their systems
4. **Approval** and merge by maintainers

## 🐛 Issue Guidelines

### Bug Reports

Use this template for bug reports:

```markdown
**Bug Description**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**

- OS: [e.g., Windows 10, macOS 12.0, Ubuntu 20.04]
- Python Version: [e.g., 3.11.0]
- Project Version: [e.g., 1.0.0]

**Screenshots/Logs**
Add screenshots or error logs if applicable.

**Additional Context**
Any other context about the problem.
```

### Feature Requests

Use this template for feature requests:

```markdown
**Feature Description**
A clear description of the feature you'd like to see.

**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
Describe your proposed solution.

**Alternatives Considered**
Describe any alternative solutions you've considered.

**Additional Context**
Add any other context or screenshots about the feature request.
```

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on

## 👥 Community Guidelines

### Communication

- **Be respectful** and constructive in all interactions
- **Ask questions** if you're unsure about anything
- **Help others** when you can
- **Be patient** with maintainers and other contributors

### Getting Help

- **GitHub Discussions**: For general questions and discussions
- **GitHub Issues**: For bug reports and feature requests
- **Email**: For sensitive issues or direct contact with maintainers

### Recognition

Contributors will be recognized in:

- **README.md** contributors section
- **Release notes** for significant contributions
- **GitHub contributors** page

## 🆘 Getting Help

### Resources

- **Documentation**: Check the [docs/](docs/) directory
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **GitHub Discussions**: [Project Discussions](https://github.com/BennyPerumalla/oss-community-agent/discussions)
- **Issues**: [GitHub Issues](https://github.com/BennyPerumalla/oss-community-agent/issues)

### Contact Maintainers

- **Benny Perumalla**: [benny01r@gmail.com](mailto:benny01r@gmail.com)
- **Md. Irshad Siddi**: [mohammadirshadsiddi@gmail.com](mailto:mohammadirshadsiddi@gmail.com)
- **Sukesh Reddy**: [lyricsofsongs96@gmail.com](mailto:lyricsofsongs96@gmail.com)
- **Hareeswar Reddy**: [ahreddy05@gmail.com](mailto:ahreddy05@gmail.com)

### Common Questions

**Q: How do I get started contributing?**
A: Start with issues labeled `good first issue` or `help wanted`. Set up your development environment and run the tests to make sure everything works.

**Q: What if I'm new to AI/ML?**
A: That's perfectly fine! We have many non-AI contributions like documentation, UI improvements, and testing. The AI components are well-documented and you can learn as you go.

**Q: How do I test Reddit integration without posting?**
A: The system has a `DRY_RUN=true` mode that simulates posting without actually posting to Reddit. This is perfect for development and testing.

**Q: Can I work on multiple issues at once?**
A: It's better to focus on one issue at a time to avoid conflicts and ensure quality. Complete one PR before starting another.

**Q: What if my PR is taking a long time to review?**
A: Maintainers are volunteers and may be busy. Feel free to ping after a week or ask in GitHub Discussions for status updates.

---

## 🎉 Thank You!

Thank you for contributing to the OSS Community Agent! Your contributions help make open-source maintenance more sustainable and reduce maintainer burnout. Together, we can build tools that benefit the entire open-source ecosystem.

**Happy Contributing!** 🚀

---

<div align="center">

**Need help?** [Open a Discussion](https://github.com/BennyPerumalla/oss-community-agent/discussions) | [Report a Bug](https://github.com/BennyPerumalla/oss-community-agent/issues) | [Request a Feature](https://github.com/BennyPerumalla/oss-community-agent/issues)

</div>
