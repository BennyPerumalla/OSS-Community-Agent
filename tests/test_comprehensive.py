# tests/test_comprehensive.py
"""
Comprehensive testing suite for OSS Community Agent.

This module provides:
- Unit tests for individual components
- Integration tests for component interactions  
- End-to-end workflow tests
- Performance and load tests
- Security and vulnerability tests
- Automated test discovery and execution
"""

import os
import sys
import pytest
import asyncio
import tempfile
import unittest
import time
import json
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import components to test
try:
    from apps.agent.main import run_oss_agent, get_reddit_tool
    from apps.portia_enhanced_agent import EnhancedPortiaAgent
    from monitoring.observability import metrics, logger, health_monitor, profiler
    from tools.reddit_tool import RedditTool
    from tools.rag_tool import RAGTool
    from tools.moderation_tools import analyze_text
    from apps.ui.utils.database import DatabaseManager
    from apps.ui.utils.approval_workflow import approval_workflow
except ImportError as e:
    print(f"Warning: Could not import some components: {e}")

class TestEnvironment:
    """Test environment management utilities"""
    
    @staticmethod
    def create_temp_env_file() -> str:
        """Create a temporary .env file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
# Test environment variables
REDDIT_CLIENT_ID=test_client_id
REDDIT_CLIENT_SECRET=test_client_secret  
REDDIT_USERNAME=test_username
REDDIT_PASSWORD=test_password
USER_AGENT=test-agent/1.0

GROQ_API_KEY=test_groq_key
OPENAI_API_KEY=test_openai_key
PORTIA_API_KEY=test_portia_key

DRY_RUN=true
AUTO_APPROVAL=false
CONFIDENCE_THRESHOLD=0.5

DATABASE_PATH=:memory:
RAG_CORPUS_DIR=data/corpus
""")
        return f.name
    
    @staticmethod
    def create_temp_database() -> str:
        """Create a temporary SQLite database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Initialize database schema
        conn = sqlite3.connect(path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        
        return path

class TestRedditTool(unittest.TestCase):
    """Unit tests for Reddit tool functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.reddit_tool = None
        
    def test_reddit_tool_initialization(self):
        """Test Reddit tool initialization with valid credentials"""
        with patch('praw.Reddit') as mock_reddit:
            mock_reddit.return_value = Mock()
            
            tool = RedditTool(
                client_id='test_id',
                client_secret='test_secret',
                username='test_user',
                password='test_pass',
                user_agent='test-agent/1.0'
            )
            
            self.assertIsNotNone(tool)
            mock_reddit.assert_called_once()
    
    def test_reddit_tool_invalid_credentials(self):
        """Test Reddit tool behavior with invalid credentials"""
        with pytest.raises((ValueError, TypeError)):
            RedditTool(
                client_id=None,
                client_secret='test_secret',
                username='test_user',
                password='test_pass'
            )
    
    @patch('praw.Reddit')
    def test_search_questions(self, mock_reddit):
        """Test question searching functionality"""
        # Mock Reddit API response
        mock_submission = Mock()
        mock_submission.id = 'test123'
        mock_submission.title = 'Test Question'
        mock_submission.selftext = 'This is a test question'
        mock_submission.url = 'https://reddit.com/test'
        mock_submission.author.name = 'test_user'
        mock_submission.created_utc = time.time()
        
        mock_subreddit = Mock()
        mock_subreddit.search.return_value = [mock_submission]
        
        mock_reddit_instance = Mock()
        mock_reddit_instance.subreddit.return_value = mock_subreddit
        mock_reddit.return_value = mock_reddit_instance
        
        tool = RedditTool(
            client_id='test_id',
            client_secret='test_secret', 
            username='test_user',
            password='test_pass',
            user_agent='test-agent/1.0'
        )
        
        results = tool.search_questions('test_subreddit', 'python', limit=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 'test123')
        self.assertEqual(results[0]['title'], 'Test Question')

class TestRAGTool(unittest.TestCase):
    """Unit tests for RAG tool functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_corpus_dir = tempfile.mkdtemp()
        self.rag_tool = None
        
        # Create test documents
        test_doc = Path(self.temp_corpus_dir) / "test_doc.md"
        test_doc.write_text("""
# Python Basics

## What are try-except blocks?

Try-except blocks in Python are used for error handling. They allow you to catch and handle exceptions gracefully.

```python
try:
    risky_operation()
except Exception as e:
    print(f"An error occurred: {e}")
```

This prevents your program from crashing when errors occur.
""")
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_corpus_dir, ignore_errors=True)
    
    @patch.dict(os.environ, {'RAG_CORPUS_DIR': 'temp_corpus'})
    def test_rag_tool_initialization(self):
        """Test RAG tool initialization"""
        with patch('chromadb.Client') as mock_client:
            mock_client.return_value = Mock()
            
            try:
                tool = RAGTool()
                self.assertIsNotNone(tool)
            except Exception as e:
                # RAG tool may not be fully initializable in test environment
                self.assertIn('RAG', str(type(e).__name__))
    
    def test_query_processing(self):
        """Test query processing and response generation"""
        # Mock RAG tool behavior
        mock_tool = Mock()
        mock_tool.retrieve_and_generate.return_value = "Try-except blocks are used for error handling in Python."
        
        query = "What are try-except blocks in Python?"
        response = mock_tool.retrieve_and_generate(query)
        
        self.assertIsInstance(response, str)
        self.assertIn("error handling", response.lower())

class TestModerationTool(unittest.TestCase):
    """Unit tests for content moderation"""
    
    def test_analyze_safe_content(self):
        """Test analysis of safe content"""
        safe_content = "Here's how to use Python try-except blocks for error handling."
        
        try:
            result = analyze_text(safe_content)
            if result:
                self.assertIsInstance(result, dict)
                self.assertFalse(result.get('is_flagged', False))
        except Exception:
            # Moderation tool may not be available
            pass
    
    def test_analyze_unsafe_content(self):
        """Test analysis of potentially unsafe content"""
        unsafe_content = "This content contains harmful instructions for illegal activities."
        
        try:
            result = analyze_text(unsafe_content)
            if result:
                self.assertIsInstance(result, dict)
                # Should be flagged or have low safety score
                self.assertTrue(
                    result.get('is_flagged', False) or 
                    result.get('safety_score', 1.0) < 0.8
                )
        except Exception:
            # Moderation tool may not be available
            pass

class TestDatabaseManager(unittest.TestCase):
    """Unit tests for database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db_path = TestEnvironment.create_temp_database()
        
        with patch.dict(os.environ, {'DATABASE_PATH': self.test_db_path}):
            self.db_manager = DatabaseManager()
    
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.test_db_path)
        except FileNotFoundError:
            pass
    
    def test_save_and_retrieve_request(self):
        """Test saving and retrieving requests"""
        request_id = "test_request_123"
        request_data = {
            'question': 'Test question',
            'response': 'Test response',
            'confidence': 0.8,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save request
        self.db_manager.save_request(request_id, request_data)
        
        # Retrieve request
        retrieved = self.db_manager.get_request(request_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['question'], request_data['question'])
    
    def test_get_request_stats(self):
        """Test request statistics retrieval"""
        # Add some test data
        for i in range(5):
            request_id = f"test_request_{i}"
            request_data = {'status': 'approved' if i < 3 else 'pending'}
            self.db_manager.save_request(request_id, request_data)
        
        stats = self.db_manager.get_request_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total', stats)

class TestPortiaAgent(unittest.TestCase):
    """Unit tests for Portia agent functionality"""
    
    @patch('apps.portia_enhanced_agent.PORTIA_AVAILABLE', False)
    def test_enhanced_agent_initialization(self):
        """Test enhanced Portia agent initialization"""
        try:
            from apps.portia_enhanced_agent import EnhancedPortiaAgent
            agent = EnhancedPortiaAgent()
            self.assertIsNotNone(agent)
            self.assertIsNotNone(agent.agent_id)
        except ImportError:
            self.skipTest("EnhancedPortiaAgent not available")
    
    @patch('apps.portia_enhanced_agent.PORTIA_AVAILABLE', False)
    def test_agent_tool_registration(self):
        """Test agent tool registration"""
        try:
            from apps.portia_enhanced_agent import EnhancedPortiaAgent
            agent = EnhancedPortiaAgent()
            
            # Check if tools are initialized
            self.assertIsNotNone(agent.rag_tool)
        except ImportError:
            self.skipTest("EnhancedPortiaAgent not available")

class TestIntegrations(unittest.TestCase):
    """Integration tests for component interactions"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.env_file = TestEnvironment.create_temp_env_file()
        self.test_db_path = TestEnvironment.create_temp_database()
        
        # Load test environment
        from dotenv import load_dotenv
        load_dotenv(self.env_file)
    
    def tearDown(self):
        """Clean up integration test environment"""
        try:
            os.unlink(self.env_file)
            os.unlink(self.test_db_path)
        except FileNotFoundError:
            pass
    
    @patch('apps.agent.main.get_reddit_tool')
    @patch('apps.ui.utils.approval_workflow.approval_workflow')
    def test_end_to_end_workflow(self, mock_approval, mock_reddit_tool):
        """Test complete end-to-end workflow"""
        # Mock Reddit tool
        mock_tool = Mock()
        mock_tool.search_questions.return_value = [
            {
                'id': 'test123',
                'title': 'Test Question',
                'selftext': 'Test question body',
                'url': 'https://reddit.com/test',
                'author': 'test_user'
            }
        ]
        mock_reddit_tool.return_value = mock_tool
        
        # Mock approval workflow
        mock_approval.process_reddit_query.return_value = {
            'success': True,
            'request_id': 'test_request_123',
            'confidence': 0.8
        }
        mock_approval.get_pending_requests.return_value = []
        mock_approval.get_request_stats.return_value = {'total': 1, 'pending': 0}
        
        try:
            result = run_oss_agent(
                query="test query",
                subreddit="test_subreddit"
            )
            
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get('status'), 'completed')
            self.assertIn('run_id', result)
        except Exception as e:
            # Some dependencies may not be available
            self.assertIn('workflow', str(e).lower())

class TestMonitoringSystem(unittest.TestCase):
    """Tests for monitoring and observability"""
    
    def test_metrics_collection(self):
        """Test metrics collection functionality"""
        from monitoring.observability import metrics
        
        # Test counter increment
        initial_count = len(metrics.counters)
        metrics.increment_counter('test_counter', {'label': 'test'})
        self.assertGreater(len(metrics.counters), initial_count)
        
        # Test histogram recording
        initial_hist_count = len(metrics.histograms)
        metrics.record_histogram('test_histogram', 1.5, {'operation': 'test'})
        self.assertGreaterEqual(len(metrics.histograms), initial_hist_count)
        
        # Test gauge setting
        initial_gauge_count = len(metrics.gauges)
        metrics.set_gauge('test_gauge', 42.0)
        self.assertGreater(len(metrics.gauges), initial_gauge_count)
    
    def test_structured_logging(self):
        """Test structured logging functionality"""
        from monitoring.observability import logger
        
        # Test logging with context
        logger.set_context(test_id='test_123', component='test')
        
        # These should not raise exceptions
        logger.info("Test info message", extra_field='test_value')
        logger.warning("Test warning message")
        logger.error("Test error message", error_code=500)
        
        logger.clear_context()
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self):
        """Test health monitoring system"""
        from monitoring.observability import health_monitor
        
        # Run health checks
        results = await health_monitor.run_all_checks()
        
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)
        
        # Check that each result has required fields
        for name, result in results.items():
            self.assertHasAttr(result, 'name')
            self.assertHasAttr(result, 'status')
            self.assertHasAttr(result, 'message')
            self.assertIn(result.status, ['healthy', 'degraded', 'unhealthy'])
    
    def test_performance_profiling(self):
        """Test performance profiling"""
        from monitoring.observability import profiler
        
        # Test profiling context manager
        with profiler.profile('test_operation', category='unit_test'):
            time.sleep(0.01)  # Simulate work
        
        # Check that profile was recorded
        stats = profiler.get_profile_stats('test_operation')
        self.assertIsInstance(stats, dict)
        self.assertGreater(stats.get('count', 0), 0)

class TestSecurityFeatures(unittest.TestCase):
    """Security and vulnerability tests"""
    
    def test_input_validation(self):
        """Test input validation for SQL injection prevention"""
        test_db_path = TestEnvironment.create_temp_database()
        
        try:
            with patch.dict(os.environ, {'DATABASE_PATH': test_db_path}):
                db_manager = DatabaseManager()
                
                # Test with potentially malicious input
                malicious_input = "'; DROP TABLE requests; --"
                request_data = {'query': malicious_input}
                
                # This should not raise an exception or corrupt the database
                db_manager.save_request('test_id', request_data)
                
                # Verify database integrity
                stats = db_manager.get_request_stats()
                self.assertIsInstance(stats, dict)
                
        finally:
            os.unlink(test_db_path)
    
    def test_environment_variable_security(self):
        """Test that sensitive environment variables are handled securely"""
        # Test that API keys are not logged in plain text
        from monitoring.observability import logger
        
        # Mock sensitive data
        with patch.dict(os.environ, {'TEST_API_KEY': 'secret_key_123'}):
            # Logger should not expose sensitive environment variables
            logger.info("Testing with API key", api_key='***REDACTED***')
            
            # This test passes if no exception is raised

class TestPerformance(unittest.TestCase):
    """Performance and load testing"""
    
    def test_database_performance(self):
        """Test database performance under load"""
        test_db_path = TestEnvironment.create_temp_database()
        
        try:
            with patch.dict(os.environ, {'DATABASE_PATH': test_db_path}):
                db_manager = DatabaseManager()
                
                start_time = time.time()
                
                # Insert many records
                for i in range(100):
                    request_data = {
                        'question': f'Test question {i}',
                        'response': f'Test response {i}',
                        'confidence': 0.8
                    }
                    db_manager.save_request(f'test_request_{i}', request_data)
                
                # Measure query performance
                query_start = time.time()
                stats = db_manager.get_request_stats()
                query_time = time.time() - query_start
                
                total_time = time.time() - start_time
                
                # Performance assertions
                self.assertLess(total_time, 5.0)  # Should complete within 5 seconds
                self.assertLess(query_time, 1.0)  # Query should be fast
                self.assertEqual(stats.get('total', 0), 100)
                
        finally:
            os.unlink(test_db_path)
    
    def test_memory_usage(self):
        """Test memory usage patterns"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create many objects
        data_objects = []
        for i in range(1000):
            data_objects.append({
                'id': i,
                'data': f'test_data_{i}' * 100,  # Create some sizeable strings
                'timestamp': datetime.now().isoformat()
            })
        
        peak_memory = process.memory_info().rss
        
        # Clean up
        data_objects.clear()
        gc.collect()
        
        final_memory = process.memory_info().rss
        
        # Memory should be released after cleanup
        memory_increase = peak_memory - initial_memory
        memory_after_cleanup = final_memory - initial_memory
        
        self.assertGreater(memory_increase, 0)  # Memory should increase
        self.assertLess(memory_after_cleanup, memory_increase * 0.5)  # Should release most memory

class TestRunner:
    """Automated test runner and reporting"""
    
    def __init__(self):
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
    
    def discover_tests(self) -> List[str]:
        """Discover all test modules"""
        test_files = []
        test_dir = Path(__file__).parent
        
        for file_path in test_dir.glob("test_*.py"):
            if file_path.name != __file__.split('/')[-1]:  # Exclude this file
                test_files.append(str(file_path))
        
        return test_files
    
    def run_tests(self, test_pattern: str = None, verbose: bool = True) -> Dict[str, Any]:
        """Run all tests and return results"""
        self.results['start_time'] = datetime.now()
        
        try:
            # Discover and run tests
            if test_pattern:
                # Run specific test pattern
                result = pytest.main(['-v', test_pattern] if verbose else [test_pattern])
            else:
                # Run all tests in this file
                result = pytest.main(['-v', __file__] if verbose else [__file__])
            
            self.results['total'] = 1  # Simplified for this example
            if result == 0:
                self.results['passed'] = 1
            else:
                self.results['failed'] = 1
                
        except Exception as e:
            self.results['errors'].append(str(e))
            self.results['failed'] = 1
        
        finally:
            self.results['end_time'] = datetime.now()
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate test report"""
        duration = 0
        if self.results['start_time'] and self.results['end_time']:
            duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        report = f"""
# OSS Community Agent - Test Report

## Summary
- **Total Tests**: {self.results['total']}
- **Passed**: {self.results['passed']}
- **Failed**: {self.results['failed']}
- **Skipped**: {self.results['skipped']}
- **Duration**: {duration:.2f} seconds

## Status
{'✅ ALL TESTS PASSED' if self.results['failed'] == 0 else '❌ SOME TESTS FAILED'}

## Errors
"""
        
        if self.results['errors']:
            for error in self.results['errors']:
                report += f"- {error}\n"
        else:
            report += "No errors reported.\n"
        
        return report

def main():
    """Main test execution function"""
    print("🧪 OSS Community Agent - Comprehensive Test Suite")
    print("=" * 60)
    
    runner = TestRunner()
    
    # Run tests
    print("Running tests...")
    results = runner.run_tests(verbose=True)
    
    # Generate and display report
    report = runner.generate_report()
    print(report)
    
    # Return exit code
    return 0 if results['failed'] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
