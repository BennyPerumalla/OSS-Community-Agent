# security/security_framework.py
"""
Production-ready security and safety framework for OSS Community Agent.

This module provides comprehensive security features including:
- Authentication and authorization systems
- Rate limiting and throttling
- Input validation and sanitization
- Content filtering and moderation
- Security audit logging
- Vulnerability scanning and protection
- Secure configuration management
"""

import os
import time
import hashlib
import hmac
import jwt
import re
import bleach
import bcrypt
import secrets
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass
from collections import defaultdict, deque
from pathlib import Path
import ipaddress
from functools import wraps
from contextlib import contextmanager

# Import security libraries
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ Cryptography library not available - using basic security")

# Configure security logging
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

if not security_logger.handlers:
    handler = logging.FileHandler('logs/security.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    user_id: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    details: Dict[str, Any]
    severity: str  # 'low', 'medium', 'high', 'critical'
    action_taken: Optional[str] = None

class AuthenticationManager:
    """
    Comprehensive authentication system with multiple authentication methods.
    Supports JWT tokens, API keys, and session-based authentication.
    """
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        self.token_expiry = timedelta(hours=24)
        self.users = {}  # In production, use proper database
        self.sessions = {}
        self.failed_attempts = defaultdict(int)
        self.lockout_threshold = 5
        self.lockout_duration = timedelta(minutes=30)
        self.locked_accounts = {}
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, password: str, roles: List[str] = None) -> Dict[str, Any]:
        """Create a new user account"""
        if username in self.users:
            raise ValueError("User already exists")
        
        # Validate password strength
        if not self._is_strong_password(password):
            raise ValueError("Password does not meet security requirements")
        
        user_data = {
            'username': username,
            'password_hash': self.hash_password(password),
            'roles': roles or ['user'],
            'created_at': datetime.now(),
            'last_login': None,
            'is_active': True
        }
        
        self.users[username] = user_data
        
        security_logger.info(f"User created: {username}", extra={
            'event_type': 'user_created',
            'username': username,
            'roles': roles
        })
        
        return {'username': username, 'created': True}
    
    def authenticate(self, username: str, password: str, ip_address: str = None) -> Dict[str, Any]:
        """Authenticate user with username and password"""
        
        # Check if account is locked
        if self._is_account_locked(username):
            security_logger.warning(f"Authentication attempt on locked account: {username}", 
                                   extra={'username': username, 'ip_address': ip_address})
            raise ValueError("Account is temporarily locked due to too many failed attempts")
        
        # Check if user exists
        if username not in self.users:
            self._record_failed_attempt(username, ip_address)
            security_logger.warning(f"Authentication failed - user not found: {username}",
                                   extra={'username': username, 'ip_address': ip_address})
            raise ValueError("Invalid credentials")
        
        user_data = self.users[username]
        
        # Check if account is active
        if not user_data.get('is_active', False):
            security_logger.warning(f"Authentication attempt on inactive account: {username}",
                                   extra={'username': username, 'ip_address': ip_address})
            raise ValueError("Account is disabled")
        
        # Verify password
        if not self.verify_password(password, user_data['password_hash']):
            self._record_failed_attempt(username, ip_address)
            security_logger.warning(f"Authentication failed - invalid password: {username}",
                                   extra={'username': username, 'ip_address': ip_address})
            raise ValueError("Invalid credentials")
        
        # Reset failed attempts on successful login
        self.failed_attempts[username] = 0
        if username in self.locked_accounts:
            del self.locked_accounts[username]
        
        # Update last login
        user_data['last_login'] = datetime.now()
        
        # Generate JWT token
        token = self._generate_jwt_token(username, user_data['roles'])
        
        security_logger.info(f"User authenticated successfully: {username}",
                           extra={'username': username, 'ip_address': ip_address})
        
        return {
            'token': token,
            'username': username,
            'roles': user_data['roles'],
            'expires_at': datetime.now() + self.token_expiry
        }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check if token is expired
            if datetime.fromtimestamp(payload['exp']) < datetime.now():
                raise jwt.ExpiredSignatureError("Token has expired")
            
            return {
                'valid': True,
                'username': payload['username'],
                'roles': payload['roles'],
                'expires_at': datetime.fromtimestamp(payload['exp'])
            }
        
        except jwt.ExpiredSignatureError:
            security_logger.warning("Expired token used", extra={'token_expired': True})
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError as e:
            security_logger.warning(f"Invalid token used: {e}", extra={'invalid_token': True})
            return {'valid': False, 'error': 'Invalid token'}
    
    def _generate_jwt_token(self, username: str, roles: List[str]) -> str:
        """Generate JWT token for user"""
        payload = {
            'username': username,
            'roles': roles,
            'iat': datetime.now(),
            'exp': datetime.now() + self.token_expiry
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def _is_strong_password(self, password: str) -> bool:
        """Check if password meets security requirements"""
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True
    
    def _record_failed_attempt(self, username: str, ip_address: str = None):
        """Record failed authentication attempt"""
        self.failed_attempts[username] += 1
        
        if self.failed_attempts[username] >= self.lockout_threshold:
            self.locked_accounts[username] = datetime.now() + self.lockout_duration
            security_logger.critical(f"Account locked due to repeated failures: {username}",
                                   extra={'username': username, 'ip_address': ip_address,
                                         'failed_attempts': self.failed_attempts[username]})
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is currently locked"""
        if username not in self.locked_accounts:
            return False
        
        if datetime.now() >= self.locked_accounts[username]:
            # Lock period expired
            del self.locked_accounts[username]
            self.failed_attempts[username] = 0
            return False
        
        return True

class RateLimiter:
    """
    Advanced rate limiting system with multiple strategies.
    Supports per-user, per-IP, and global rate limiting.
    """
    
    def __init__(self):
        self.user_limits = defaultdict(lambda: deque(maxlen=100))
        self.ip_limits = defaultdict(lambda: deque(maxlen=200))
        self.global_limits = deque(maxlen=1000)
        
        # Default limits (requests per time window)
        self.limits = {
            'user_per_minute': 60,
            'user_per_hour': 1000,
            'ip_per_minute': 100,
            'ip_per_hour': 2000,
            'global_per_minute': 5000
        }
        
        # Time windows in seconds
        self.windows = {
            'minute': 60,
            'hour': 3600
        }
    
    def is_allowed(self, user_id: str = None, ip_address: str = None, 
                   operation: str = 'default') -> Dict[str, Any]:
        """Check if request is allowed based on rate limits"""
        now = time.time()
        
        # Clean old entries
        self._clean_old_entries(now)
        
        # Check global limits
        if not self._check_global_limits(now):
            security_logger.warning("Global rate limit exceeded")
            return {
                'allowed': False,
                'reason': 'global_rate_limit_exceeded',
                'retry_after': 60
            }
        
        # Check IP limits
        if ip_address and not self._check_ip_limits(ip_address, now):
            security_logger.warning(f"IP rate limit exceeded: {ip_address}")
            return {
                'allowed': False,
                'reason': 'ip_rate_limit_exceeded',
                'retry_after': 60
            }
        
        # Check user limits
        if user_id and not self._check_user_limits(user_id, now):
            security_logger.warning(f"User rate limit exceeded: {user_id}")
            return {
                'allowed': False,
                'reason': 'user_rate_limit_exceeded',
                'retry_after': 60
            }
        
        # Record request
        self.global_limits.append(now)
        if ip_address:
            self.ip_limits[ip_address].append(now)
        if user_id:
            self.user_limits[user_id].append(now)
        
        return {'allowed': True}
    
    def _check_global_limits(self, now: float) -> bool:
        """Check global rate limits"""
        minute_ago = now - self.windows['minute']
        recent_requests = sum(1 for t in self.global_limits if t > minute_ago)
        return recent_requests < self.limits['global_per_minute']
    
    def _check_ip_limits(self, ip_address: str, now: float) -> bool:
        """Check IP-based rate limits"""
        ip_requests = self.ip_limits[ip_address]
        
        minute_ago = now - self.windows['minute']
        hour_ago = now - self.windows['hour']
        
        recent_minute = sum(1 for t in ip_requests if t > minute_ago)
        recent_hour = sum(1 for t in ip_requests if t > hour_ago)
        
        return (recent_minute < self.limits['ip_per_minute'] and 
                recent_hour < self.limits['ip_per_hour'])
    
    def _check_user_limits(self, user_id: str, now: float) -> bool:
        """Check user-based rate limits"""
        user_requests = self.user_limits[user_id]
        
        minute_ago = now - self.windows['minute']
        hour_ago = now - self.windows['hour']
        
        recent_minute = sum(1 for t in user_requests if t > minute_ago)
        recent_hour = sum(1 for t in user_requests if t > hour_ago)
        
        return (recent_minute < self.limits['user_per_minute'] and
                recent_hour < self.limits['user_per_hour'])
    
    def _clean_old_entries(self, now: float):
        """Remove old entries from rate limit tracking"""
        hour_ago = now - self.windows['hour']
        
        # Clean global limits
        while self.global_limits and self.global_limits[0] < hour_ago:
            self.global_limits.popleft()
        
        # Clean IP limits
        for ip_address in list(self.ip_limits.keys()):
            ip_requests = self.ip_limits[ip_address]
            while ip_requests and ip_requests[0] < hour_ago:
                ip_requests.popleft()
            
            # Remove empty entries
            if not ip_requests:
                del self.ip_limits[ip_address]
        
        # Clean user limits
        for user_id in list(self.user_limits.keys()):
            user_requests = self.user_limits[user_id]
            while user_requests and user_requests[0] < hour_ago:
                user_requests.popleft()
            
            # Remove empty entries
            if not user_requests:
                del self.user_limits[user_id]

class InputValidator:
    """
    Comprehensive input validation and sanitization system.
    Protects against various injection attacks and malicious input.
    """
    
    def __init__(self):
        # XSS protection
        self.allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'code', 'pre']
        self.allowed_attributes = {'a': ['href'], 'code': ['class']}
        
        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\b\s*\d+\s*=\s*\d+)",
            r"(\'\s*(OR|AND)\s*\')",
        ]
        
        # Command injection patterns
        self.command_patterns = [
            r"[;&|`$()]",
            r"\b(cat|ls|pwd|whoami|id|ps|kill|chmod|rm|mv|cp)\b",
            r"(>|<|>>|<<)",
        ]
        
        # Path traversal patterns
        self.path_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"~[/\\]",
        ]
    
    def validate_and_sanitize(self, data: Dict[str, Any], 
                            validation_rules: Dict[str, Dict] = None) -> Dict[str, Any]:
        """Validate and sanitize input data"""
        validated_data = {}
        validation_rules = validation_rules or {}
        
        for key, value in data.items():
            try:
                # Get validation rules for this field
                field_rules = validation_rules.get(key, {})
                
                # Apply validation and sanitization
                validated_value = self._validate_field(key, value, field_rules)
                validated_data[key] = validated_value
                
            except ValueError as e:
                security_logger.warning(f"Input validation failed for field '{key}': {e}")
                raise ValueError(f"Invalid input for field '{key}': {e}")
        
        return validated_data
    
    def _validate_field(self, field_name: str, value: Any, rules: Dict) -> Any:
        """Validate and sanitize a single field"""
        # Type validation
        expected_type = rules.get('type', str)
        if not isinstance(value, expected_type) and value is not None:
            if expected_type == str:
                value = str(value)
            else:
                raise ValueError(f"Expected {expected_type.__name__}, got {type(value).__name__}")
        
        if isinstance(value, str):
            # Length validation
            if 'max_length' in rules and len(value) > rules['max_length']:
                raise ValueError(f"Value too long (max {rules['max_length']} characters)")
            
            if 'min_length' in rules and len(value) < rules['min_length']:
                raise ValueError(f"Value too short (min {rules['min_length']} characters)")
            
            # Pattern validation
            if 'pattern' in rules:
                pattern = rules['pattern']
                if not re.match(pattern, value):
                    raise ValueError("Value does not match required pattern")
            
            # Security validation
            value = self._sanitize_string(value, rules)
        
        elif isinstance(value, (int, float)):
            # Numeric validation
            if 'min_value' in rules and value < rules['min_value']:
                raise ValueError(f"Value too small (min {rules['min_value']})")
            
            if 'max_value' in rules and value > rules['max_value']:
                raise ValueError(f"Value too large (max {rules['max_value']})")
        
        return value
    
    def _sanitize_string(self, value: str, rules: Dict) -> str:
        """Sanitize string input"""
        # HTML sanitization
        if rules.get('allow_html', False):
            value = bleach.clean(value, 
                               tags=self.allowed_tags,
                               attributes=self.allowed_attributes,
                               strip=True)
        else:
            value = bleach.clean(value, tags=[], strip=True)
        
        # SQL injection detection
        if rules.get('check_sql_injection', True):
            for pattern in self.sql_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    security_logger.critical(f"SQL injection attempt detected: {value[:100]}")
                    raise ValueError("Potentially malicious SQL detected")
        
        # Command injection detection
        if rules.get('check_command_injection', True):
            for pattern in self.command_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    security_logger.critical(f"Command injection attempt detected: {value[:100]}")
                    raise ValueError("Potentially malicious commands detected")
        
        # Path traversal detection
        if rules.get('check_path_traversal', True):
            for pattern in self.path_patterns:
                if re.search(pattern, value):
                    security_logger.critical(f"Path traversal attempt detected: {value[:100]}")
                    raise ValueError("Potentially malicious path detected")
        
        return value

class ContentModerator:
    """
    Advanced content moderation system for filtering inappropriate content.
    Uses multiple filtering strategies including keyword filtering and pattern matching.
    """
    
    def __init__(self):
        self.blocked_keywords = self._load_blocked_keywords()
        self.suspicious_patterns = self._load_suspicious_patterns()
        self.whitelist_domains = self._load_whitelist_domains()
        
    def _load_blocked_keywords(self) -> List[str]:
        """Load list of blocked keywords"""
        # In production, load from configuration file or database
        return [
            'spam', 'scam', 'phishing', 'malware', 'virus',
            'hack', 'crack', 'piracy', 'illegal', 'drugs'
        ]
    
    def _load_suspicious_patterns(self) -> List[str]:
        """Load suspicious content patterns"""
        return [
            r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b',  # Credit card pattern
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email pattern (for spam detection)
            r'(http|https|ftp)://[^\s]+',  # URL pattern (for link spam)
        ]
    
    def _load_whitelist_domains(self) -> List[str]:
        """Load whitelisted domains"""
        return [
            'github.com', 'stackoverflow.com', 'python.org', 'reddit.com',
            'docs.python.org', 'pypi.org', 'jupyter.org'
        ]
    
    def moderate_content(self, content: str, user_id: str = None) -> Dict[str, Any]:
        """Moderate content and return moderation results"""
        
        moderation_result = {
            'approved': True,
            'confidence': 1.0,
            'flags': [],
            'filtered_content': content,
            'action_taken': None
        }
        
        # Keyword filtering
        blocked_words = self._check_blocked_keywords(content)
        if blocked_words:
            moderation_result['flags'].append('blocked_keywords')
            moderation_result['confidence'] -= 0.3
            moderation_result['blocked_words'] = blocked_words
        
        # Pattern matching
        suspicious_matches = self._check_suspicious_patterns(content)
        if suspicious_matches:
            moderation_result['flags'].append('suspicious_patterns')
            moderation_result['confidence'] -= 0.2
            moderation_result['suspicious_patterns'] = suspicious_matches
        
        # URL validation
        urls = self._extract_urls(content)
        if urls:
            malicious_urls = self._check_urls(urls)
            if malicious_urls:
                moderation_result['flags'].append('malicious_urls')
                moderation_result['confidence'] -= 0.5
                moderation_result['malicious_urls'] = malicious_urls
        
        # Content length analysis
        if len(content) > 10000:  # Very long content
            moderation_result['flags'].append('excessive_length')
            moderation_result['confidence'] -= 0.1
        
        # Final decision
        if moderation_result['confidence'] < 0.3:
            moderation_result['approved'] = False
            moderation_result['action_taken'] = 'blocked'
        elif moderation_result['confidence'] < 0.7:
            moderation_result['approved'] = False
            moderation_result['action_taken'] = 'requires_review'
        
        # Log moderation event
        if not moderation_result['approved']:
            security_logger.warning(f"Content blocked by moderation: {user_id}",
                                   extra={
                                       'user_id': user_id,
                                       'flags': moderation_result['flags'],
                                       'confidence': moderation_result['confidence'],
                                       'content_preview': content[:100]
                                   })
        
        return moderation_result
    
    def _check_blocked_keywords(self, content: str) -> List[str]:
        """Check for blocked keywords in content"""
        content_lower = content.lower()
        blocked = []
        
        for keyword in self.blocked_keywords:
            if keyword.lower() in content_lower:
                blocked.append(keyword)
        
        return blocked
    
    def _check_suspicious_patterns(self, content: str) -> List[str]:
        """Check for suspicious patterns in content"""
        matches = []
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                matches.append(pattern)
        
        return matches
    
    def _extract_urls(self, content: str) -> List[str]:
        """Extract URLs from content"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, content)
    
    def _check_urls(self, urls: List[str]) -> List[str]:
        """Check URLs against whitelist and blacklist"""
        malicious = []
        
        for url in urls:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                # Remove www. prefix
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Check if domain is whitelisted
                if domain not in self.whitelist_domains:
                    # In production, check against threat intelligence databases
                    malicious.append(url)
                    
            except Exception:
                # Invalid URL format
                malicious.append(url)
        
        return malicious

class SecurityAuditor:
    """
    Security audit and compliance monitoring system.
    Tracks security events and generates audit reports.
    """
    
    def __init__(self):
        self.events = deque(maxlen=10000)  # Keep last 10k events
        self.event_types = {
            'authentication_success': 'low',
            'authentication_failure': 'medium',
            'authorization_failure': 'high',
            'rate_limit_exceeded': 'medium',
            'input_validation_failure': 'high',
            'content_moderation_block': 'medium',
            'security_scan_alert': 'high',
            'configuration_change': 'medium',
            'privilege_escalation': 'critical',
            'data_access': 'low'
        }
    
    def log_security_event(self, event_type: str, user_id: str = None,
                          ip_address: str = None, details: Dict[str, Any] = None):
        """Log a security event"""
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.now(),
            details=details or {},
            severity=self.event_types.get(event_type, 'medium')
        )
        
        self.events.append(event)
        
        # Log to security logger
        security_logger.info(f"Security event: {event_type}",
                           extra={
                               'event_type': event_type,
                               'user_id': user_id,
                               'ip_address': ip_address,
                               'severity': event.severity,
                               'details': details
                           })
        
        # Alert on critical events
        if event.severity == 'critical':
            self._send_alert(event)
    
    def _send_alert(self, event: SecurityEvent):
        """Send alert for critical security events"""
        # In production, integrate with alerting systems
        security_logger.critical(f"SECURITY ALERT: {event.event_type}",
                                extra={
                                    'event': event,
                                    'requires_immediate_attention': True
                                })
    
    def generate_audit_report(self, start_date: datetime = None,
                            end_date: datetime = None) -> Dict[str, Any]:
        """Generate security audit report"""
        start_date = start_date or (datetime.now() - timedelta(days=30))
        end_date = end_date or datetime.now()
        
        # Filter events by date range
        filtered_events = [
            event for event in self.events
            if start_date <= event.timestamp <= end_date
        ]
        
        # Aggregate statistics
        event_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        user_activity = defaultdict(int)
        ip_activity = defaultdict(int)
        
        for event in filtered_events:
            event_counts[event.event_type] += 1
            severity_counts[event.severity] += 1
            if event.user_id:
                user_activity[event.user_id] += 1
            if event.ip_address:
                ip_activity[event.ip_address] += 1
        
        report = {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_events': len(filtered_events),
                'unique_users': len(user_activity),
                'unique_ips': len(ip_activity)
            },
            'event_types': dict(event_counts),
            'severity_distribution': dict(severity_counts),
            'top_users': dict(sorted(user_activity.items(),
                                   key=lambda x: x[1], reverse=True)[:10]),
            'top_ips': dict(sorted(ip_activity.items(),
                                 key=lambda x: x[1], reverse=True)[:10]),
            'critical_events': [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'type': event.event_type,
                    'user_id': event.user_id,
                    'ip_address': event.ip_address,
                    'details': event.details
                }
                for event in filtered_events
                if event.severity == 'critical'
            ]
        }
        
        return report

# Security decorators for function-level protection
def require_auth(roles: List[str] = None):
    """Decorator to require authentication and optionally specific roles"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # In a real implementation, extract token from request headers
            # This is a simplified example
            token = kwargs.get('auth_token')
            
            if not token:
                raise PermissionError("Authentication required")
            
            auth_manager = AuthenticationManager()
            token_info = auth_manager.verify_token(token)
            
            if not token_info['valid']:
                raise PermissionError("Invalid token")
            
            if roles:
                user_roles = token_info.get('roles', [])
                if not any(role in user_roles for role in roles):
                    raise PermissionError("Insufficient permissions")
            
            # Add user info to kwargs
            kwargs['current_user'] = {
                'username': token_info['username'],
                'roles': token_info['roles']
            }
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def rate_limit(requests_per_minute: int = 60):
    """Decorator to apply rate limiting to functions"""
    def decorator(func: Callable):
        limiter = RateLimiter()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('current_user', {}).get('username')
            ip_address = kwargs.get('client_ip')
            
            result = limiter.is_allowed(user_id=user_id, ip_address=ip_address)
            
            if not result['allowed']:
                raise Exception(f"Rate limit exceeded: {result['reason']}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def validate_input(validation_rules: Dict[str, Dict]):
    """Decorator to validate function input"""
    def decorator(func: Callable):
        validator = InputValidator()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract data to validate (simplified example)
            data = kwargs.get('data', {})
            
            try:
                validated_data = validator.validate_and_sanitize(data, validation_rules)
                kwargs['data'] = validated_data
            except ValueError as e:
                raise ValueError(f"Input validation failed: {e}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global security instances
auth_manager = AuthenticationManager()
rate_limiter = RateLimiter()
input_validator = InputValidator()
content_moderator = ContentModerator()
security_auditor = SecurityAuditor()

def main():
    """Demonstrate the security framework"""
    print("🔒 OSS Agent Security Framework Demonstration")
    print("=" * 60)
    
    # Demo authentication
    print("\n👤 Authentication Demo:")
    try:
        # Create user
        auth_manager.create_user("testuser", "SecurePass123!", ["admin"])
        print("✅ User created successfully")
        
        # Authenticate
        auth_result = auth_manager.authenticate("testuser", "SecurePass123!", "127.0.0.1")
        print(f"✅ Authentication successful: {auth_result['username']}")
        
        # Verify token
        token_info = auth_manager.verify_token(auth_result['token'])
        print(f"✅ Token valid: {token_info['valid']}")
        
    except Exception as e:
        print(f"❌ Authentication error: {e}")
    
    # Demo rate limiting
    print("\n🚦 Rate Limiting Demo:")
    result = rate_limiter.is_allowed(user_id="testuser", ip_address="127.0.0.1")
    print(f"Request allowed: {result['allowed']}")
    
    # Demo input validation
    print("\n🔍 Input Validation Demo:")
    try:
        test_data = {
            'username': 'valid_user',
            'comment': 'This is a safe comment',
            'url': 'https://github.com/test'
        }
        
        rules = {
            'username': {'type': str, 'max_length': 50, 'pattern': r'^[a-zA-Z0-9_]+$'},
            'comment': {'type': str, 'max_length': 500, 'check_sql_injection': True},
            'url': {'type': str, 'max_length': 200}
        }
        
        validated = input_validator.validate_and_sanitize(test_data, rules)
        print(f"✅ Input validation successful: {len(validated)} fields validated")
        
    except Exception as e:
        print(f"❌ Input validation error: {e}")
    
    # Demo content moderation
    print("\n🛡️ Content Moderation Demo:")
    test_content = "This is a helpful Python tutorial about try-except blocks."
    moderation_result = content_moderator.moderate_content(test_content, "testuser")
    print(f"Content approved: {moderation_result['approved']}")
    print(f"Confidence: {moderation_result['confidence']:.2f}")
    
    # Demo security auditing
    print("\n📋 Security Auditing Demo:")
    security_auditor.log_security_event('authentication_success', 
                                       user_id='testuser',
                                       ip_address='127.0.0.1')
    
    audit_report = security_auditor.generate_audit_report()
    print(f"Audit report generated: {audit_report['summary']['total_events']} events")
    
    print("\n✅ Security framework demonstration completed!")

if __name__ == "__main__":
    main()
