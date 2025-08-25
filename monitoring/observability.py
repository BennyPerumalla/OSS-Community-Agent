# monitoring/observability.py
"""
Production-level monitoring and observability system for OSS Community Agent.

This module provides:
- Comprehensive logging with structured format
- Metrics collection and aggregation
- Performance monitoring and profiling
- Health checks and status monitoring
- Error tracking and alerting
- System resource monitoring
- Dashboard-ready data export
"""

import os
import time
import psutil
import logging
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from pathlib import Path
import threading
from contextlib import contextmanager

# Import monitoring libraries
try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ Prometheus client not available - using basic metrics")

class MetricsCollector:
    """
    Centralized metrics collection system with Prometheus integration.
    Tracks system performance, agent operations, and user interactions.
    """
    
    def __init__(self):
        self.enabled = True
        self.start_time = time.time()
        
        # In-memory metrics storage (fallback)
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.gauges = defaultdict(float)
        
        # Prometheus metrics (if available)
        if PROMETHEUS_AVAILABLE:
            self._init_prometheus_metrics()
        
        # System metrics
        self.system_metrics = {}
        self._update_system_metrics()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        
        # Agent operation counters
        self.agent_requests_total = Counter(
            'oss_agent_requests_total',
            'Total number of agent requests',
            ['status', 'subreddit', 'type']
        )
        
        self.reddit_api_calls_total = Counter(
            'oss_reddit_api_calls_total', 
            'Total Reddit API calls',
            ['endpoint', 'status']
        )
        
        self.ai_requests_total = Counter(
            'oss_ai_requests_total',
            'Total AI API requests',
            ['provider', 'model', 'status']
        )
        
        # Performance histograms
        self.request_duration = Histogram(
            'oss_request_duration_seconds',
            'Request processing time',
            ['operation', 'status']
        )
        
        self.response_generation_duration = Histogram(
            'oss_response_generation_seconds',
            'Time to generate responses',
            ['provider', 'model']
        )
        
        # System gauges
        self.system_cpu_usage = Gauge(
            'oss_system_cpu_percent',
            'Current CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'oss_system_memory_percent',
            'Current memory usage percentage'
        )
        
        self.active_connections = Gauge(
            'oss_active_connections',
            'Number of active connections'
        )
        
        self.pending_approvals = Gauge(
            'oss_pending_approvals',
            'Number of pending approval requests'
        )
        
        # Agent info
        self.agent_info = Info(
            'oss_agent_info',
            'Agent version and configuration info'
        )
        
        # Set agent info
        self.agent_info.info({
            'version': '1.0.0',
            'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
            'start_time': datetime.now().isoformat()
        })
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1):
        """Increment a counter metric"""
        if not self.enabled:
            return
            
        # Fallback storage
        key = f"{name}_{labels or {}}"
        self.counters[key] += value
        
        # Prometheus
        if PROMETHEUS_AVAILABLE and hasattr(self, name):
            metric = getattr(self, name)
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        if not self.enabled:
            return
            
        # Fallback storage
        key = f"{name}_{labels or {}}"
        self.histograms[key].append(value)
        
        # Keep only recent values
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-500:]
        
        # Prometheus
        if PROMETHEUS_AVAILABLE and hasattr(self, name):
            metric = getattr(self, name)
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value"""
        if not self.enabled:
            return
            
        # Fallback storage
        key = f"{name}_{labels or {}}"
        self.gauges[key] = value
        
        # Prometheus
        if PROMETHEUS_AVAILABLE and hasattr(self, name):
            metric = getattr(self, name)
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def _update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            self.system_metrics.update({
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
            })
            
            # Update Prometheus gauges
            if PROMETHEUS_AVAILABLE:
                self.system_cpu_usage.set(cpu_percent)
                self.system_memory_usage.set(memory.percent)
            
        except Exception as e:
            logging.error(f"Failed to update system metrics: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics"""
        self._update_system_metrics()
        
        return {
            'uptime_seconds': time.time() - self.start_time,
            'system_metrics': self.system_metrics,
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histogram_counts': {k: len(v) for k, v in self.histograms.items()},
            'timestamp': datetime.now().isoformat()
        }

class StructuredLogger:
    """
    Advanced structured logging system with multiple outputs and formats.
    Provides JSON logging, file rotation, and integration with monitoring systems.
    """
    
    def __init__(self, name: str = "oss-agent", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
        
        self.extra_context = {}
    
    def _setup_handlers(self):
        """Set up logging handlers with different formats"""
        
        # Console handler with colored output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler with JSON format
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "agent.log")
        file_handler.setLevel(logging.DEBUG)
        
        json_formatter = JsonFormatter()
        file_handler.setFormatter(json_formatter)
        
        # Error file handler
        error_handler = logging.FileHandler(log_dir / "errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def set_context(self, **kwargs):
        """Set additional context for all log messages"""
        self.extra_context.update(kwargs)
    
    def clear_context(self):
        """Clear additional context"""
        self.extra_context.clear()
    
    def _log_with_context(self, level: str, message: str, **kwargs):
        """Log with additional context"""
        extra = {**self.extra_context, **kwargs}
        
        # Add standard fields
        extra.update({
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'pid': os.getpid(),
            'thread_id': threading.current_thread().ident
        })
        
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        self._log_with_context('INFO', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context('DEBUG', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context('CRITICAL', message, **kwargs)

class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 
                              'exc_text', 'stack_info', 'message']:
                    log_data[key] = value
        
        return json.dumps(log_data, default=str)

@dataclass
class HealthCheckResult:
    """Health check result data structure"""
    name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    message: str
    duration_ms: float
    timestamp: datetime
    details: Dict[str, Any] = None

class HealthMonitor:
    """
    Comprehensive health monitoring system.
    Checks various system components and provides status reports.
    """
    
    def __init__(self):
        self.checks = {}
        self.history = deque(maxlen=100)  # Keep last 100 health checks
        self.logger = StructuredLogger("health-monitor")
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        
        self.register_check("system_resources", self._check_system_resources)
        self.register_check("database", self._check_database)
        self.register_check("reddit_api", self._check_reddit_api)
        self.register_check("ai_service", self._check_ai_service)
        self.register_check("disk_space", self._check_disk_space)
    
    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self.checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status='unhealthy',
                message=f'Health check {name} not found',
                duration_ms=0,
                timestamp=datetime.now()
            )
        
        start_time = time.time()
        
        try:
            check_func = self.checks[name]
            
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.duration_ms = duration_ms
                return result
            else:
                return HealthCheckResult(
                    name=name,
                    status='healthy' if result else 'unhealthy',
                    message=str(result),
                    duration_ms=duration_ms,
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Health check {name} failed", error=str(e))
            
            return HealthCheckResult(
                name=name,
                status='unhealthy',
                message=f'Health check failed: {str(e)}',
                duration_ms=duration_ms,
                timestamp=datetime.now()
            )
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        for name in self.checks:
            results[name] = await self.run_check(name)
        
        # Store in history
        overall_status = self._calculate_overall_status(results)
        self.history.append({
            'timestamp': datetime.now(),
            'overall_status': overall_status,
            'results': results
        })
        
        return results
    
    def _calculate_overall_status(self, results: Dict[str, HealthCheckResult]) -> str:
        """Calculate overall system health status"""
        if not results:
            return 'unknown'
        
        statuses = [result.status for result in results.values()]
        
        if all(status == 'healthy' for status in statuses):
            return 'healthy'
        elif any(status == 'unhealthy' for status in statuses):
            return 'unhealthy'
        else:
            return 'degraded'
    
    def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3)
            }
            
            # Determine status based on thresholds
            if cpu_percent > 90 or memory.percent > 90:
                status = 'unhealthy'
                message = f'High resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%'
            elif cpu_percent > 70 or memory.percent > 70:
                status = 'degraded'
                message = f'Moderate resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%'
            else:
                status = 'healthy'
                message = f'Resource usage normal: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%'
            
            return HealthCheckResult(
                name='system_resources',
                status=status,
                message=message,
                duration_ms=0,  # Will be set by caller
                timestamp=datetime.now(),
                details=details
            )
        
        except Exception as e:
            return HealthCheckResult(
                name='system_resources',
                status='unhealthy',
                message=f'Failed to check system resources: {str(e)}',
                duration_ms=0,
                timestamp=datetime.now()
            )
    
    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity and health"""
        try:
            from apps.ui.utils.database import DatabaseManager
            
            db = DatabaseManager()
            # Try a simple query
            stats = db.get_request_stats()
            
            return HealthCheckResult(
                name='database',
                status='healthy',
                message=f'Database operational, {stats.get("total", 0)} total requests',
                duration_ms=0,
                timestamp=datetime.now(),
                details={'stats': stats}
            )
        
        except Exception as e:
            return HealthCheckResult(
                name='database',
                status='unhealthy',
                message=f'Database check failed: {str(e)}',
                duration_ms=0,
                timestamp=datetime.now()
            )
    
    def _check_reddit_api(self) -> HealthCheckResult:
        """Check Reddit API connectivity"""
        try:
            # Check if credentials are configured
            required_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                return HealthCheckResult(
                    name='reddit_api',
                    status='degraded',
                    message=f'Reddit API credentials not fully configured: missing {missing_vars}',
                    duration_ms=0,
                    timestamp=datetime.now(),
                    details={'missing_credentials': missing_vars}
                )
            
            # TODO: Add actual API connectivity test
            return HealthCheckResult(
                name='reddit_api',
                status='healthy',
                message='Reddit API credentials configured',
                duration_ms=0,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return HealthCheckResult(
                name='reddit_api',
                status='unhealthy',
                message=f'Reddit API check failed: {str(e)}',
                duration_ms=0,
                timestamp=datetime.now()
            )
    
    def _check_ai_service(self) -> HealthCheckResult:
        """Check AI service availability"""
        try:
            groq_key = os.getenv('GROQ_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')
            portia_key = os.getenv('PORTIA_API_KEY')
            
            available_services = []
            if groq_key and groq_key != 'your_groq_api_key_here':
                available_services.append('Groq')
            if openai_key and openai_key != 'your_openai_api_key_here':
                available_services.append('OpenAI')
            if portia_key and portia_key != 'your_portia_api_key_here':
                available_services.append('Portia')
            
            if available_services:
                return HealthCheckResult(
                    name='ai_service',
                    status='healthy',
                    message=f'AI services configured: {", ".join(available_services)}',
                    duration_ms=0,
                    timestamp=datetime.now(),
                    details={'available_services': available_services}
                )
            else:
                return HealthCheckResult(
                    name='ai_service',
                    status='unhealthy',
                    message='No AI services configured',
                    duration_ms=0,
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return HealthCheckResult(
                name='ai_service',
                status='unhealthy',
                message=f'AI service check failed: {str(e)}',
                duration_ms=0,
                timestamp=datetime.now()
            )
    
    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space"""
        try:
            if os.name == 'nt':  # Windows
                disk_usage = psutil.disk_usage('C:')
            else:  # Unix-like
                disk_usage = psutil.disk_usage('/')
            
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            details = {
                'total_gb': disk_usage.total / (1024**3),
                'free_gb': disk_usage.free / (1024**3),
                'used_gb': disk_usage.used / (1024**3),
                'free_percent': free_percent
            }
            
            if free_percent < 5:
                status = 'unhealthy'
                message = f'Critical disk space: {free_percent:.1f}% free'
            elif free_percent < 10:
                status = 'degraded'
                message = f'Low disk space: {free_percent:.1f}% free'
            else:
                status = 'healthy'
                message = f'Disk space healthy: {free_percent:.1f}% free'
            
            return HealthCheckResult(
                name='disk_space',
                status=status,
                message=message,
                duration_ms=0,
                timestamp=datetime.now(),
                details=details
            )
        
        except Exception as e:
            return HealthCheckResult(
                name='disk_space',
                status='unhealthy',
                message=f'Disk space check failed: {str(e)}',
                duration_ms=0,
                timestamp=datetime.now()
            )
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health"""
        if not self.history:
            return {'status': 'unknown', 'message': 'No health checks performed yet'}
        
        latest = self.history[-1]
        results = latest['results']
        
        summary = {
            'overall_status': latest['overall_status'],
            'timestamp': latest['timestamp'].isoformat(),
            'checks': {}
        }
        
        for name, result in results.items():
            summary['checks'][name] = {
                'status': result.status,
                'message': result.message,
                'duration_ms': result.duration_ms
            }
        
        return summary

class PerformanceProfiler:
    """
    Performance profiling and monitoring utility.
    Tracks function execution times and identifies bottlenecks.
    """
    
    def __init__(self):
        self.profiles = defaultdict(list)
        self.active_profiles = {}
        self.logger = StructuredLogger("profiler")
    
    @contextmanager
    def profile(self, name: str, **metadata):
        """Context manager for profiling code blocks"""
        profile_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        self.active_profiles[profile_id] = {
            'name': name,
            'start_time': start_time,
            'metadata': metadata
        }
        
        try:
            yield profile_id
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            profile_data = {
                'name': name,
                'duration': duration,
                'memory_delta_mb': memory_delta / (1024 * 1024),
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            self.profiles[name].append(profile_data)
            
            # Keep only recent profiles
            if len(self.profiles[name]) > 1000:
                self.profiles[name] = self.profiles[name][-500:]
            
            # Clean up
            if profile_id in self.active_profiles:
                del self.active_profiles[profile_id]
            
            # Log slow operations
            if duration > 1.0:  # Slower than 1 second
                self.logger.warning(
                    f"Slow operation detected: {name}",
                    duration=duration,
                    memory_delta_mb=memory_delta / (1024 * 1024),
                    **metadata
                )
    
    def get_profile_stats(self, name: str = None) -> Dict[str, Any]:
        """Get profiling statistics"""
        if name:
            if name not in self.profiles:
                return {}
            
            durations = [p['duration'] for p in self.profiles[name]]
            return {
                'name': name,
                'count': len(durations),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'total_duration': sum(durations)
            }
        else:
            stats = {}
            for profile_name in self.profiles:
                stats[profile_name] = self.get_profile_stats(profile_name)
            return stats

# Global instances
metrics = MetricsCollector()
logger = StructuredLogger()
health_monitor = HealthMonitor()
profiler = PerformanceProfiler()

# Initialize Prometheus HTTP server if available
if PROMETHEUS_AVAILABLE:
    try:
        # Start Prometheus metrics server on port 8000
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")
    except Exception as e:
        logger.warning(f"Failed to start Prometheus server: {e}")

async def main():
    """Demonstrate the monitoring and observability system"""
    
    print("🔍 OSS Agent Monitoring & Observability System")
    print("=" * 60)
    
    # Set logging context
    logger.set_context(component="demo", version="1.0.0")
    logger.info("Starting monitoring demonstration")
    
    # Test metrics collection
    print("\n📊 Testing Metrics Collection...")
    metrics.increment_counter('agent_requests_total', {'status': 'success', 'subreddit': 'test'})
    metrics.record_histogram('request_duration', 0.5, {'operation': 'reddit_search'})
    metrics.set_gauge('pending_approvals', 3)
    
    # Test performance profiling
    print("⏱️ Testing Performance Profiling...")
    with profiler.profile('demo_operation', operation_type='test'):
        await asyncio.sleep(0.1)  # Simulate work
    
    # Test health monitoring
    print("🏥 Running Health Checks...")
    health_results = await health_monitor.run_all_checks()
    
    # Display results
    print("\n📈 Metrics Summary:")
    print("-" * 30)
    summary = metrics.get_metrics_summary()
    print(f"Uptime: {summary['uptime_seconds']:.2f}s")
    print(f"CPU Usage: {summary['system_metrics']['cpu_percent']:.1f}%")
    print(f"Memory Usage: {summary['system_metrics']['memory_percent']:.1f}%")
    
    print("\n🏥 Health Check Results:")
    print("-" * 30)
    for name, result in health_results.items():
        status_icon = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(result.status, "❓")
        print(f"{status_icon} {name}: {result.message}")
    
    print("\n⏱️ Performance Profile:")
    print("-" * 30)
    profile_stats = profiler.get_profile_stats()
    for name, stats in profile_stats.items():
        print(f"{name}: {stats['avg_duration']:.3f}s avg ({stats['count']} calls)")
    
    print(f"\n✅ Monitoring system demonstration completed!")
    
    if PROMETHEUS_AVAILABLE:
        print("\n📊 Prometheus metrics available at: http://localhost:8000/metrics")

if __name__ == "__main__":
    asyncio.run(main())
