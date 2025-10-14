# tools/moderation_tool.py
import re
import json
from typing import Dict, Any, List

# Enhanced comprehensive keyword lists for better moderation
FLAGGED_KEYWORDS = [
    # Personal Information
    "personal information", "private details", "phone number", "email address", 
    "password", "ssn", "social security number", "credit card", "bank account",
    "home address", "full name", "driver license", "passport number",
    
    # Security/Safety
    "unsafe command", "malicious code", "virus", "malware", "hack", "exploit",
    "delete system32", "rm -rf", "format c:", "sudo rm",
    
    # Inappropriate Content
    "spam", "scam", "phishing", "illegal download", "pirated software",
    "cracked version", "keygen", "serial number", "license crack"
]

# Enhanced profanity list (basic - in production, use a dedicated library)
PROFANE_WORDS = [
    "damn", "hell", "stupid", "idiot", "moron", "dumb", "shit", "crap",
    "fuck", "fucking", "bitch", "bastard", "asshole", "piss"
]

# Enhanced regular expressions for comprehensive PII detection
PII_PATTERNS = {
    "phone_number": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "email_address": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    "ssn": r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "url_with_credentials": r"https?://[^\s]*:[^\s]*@[^\s]+",
    "api_key_pattern": r"\b(?:api[_-]?key|token|secret)[=:\s]['\"]?[a-zA-Z0-9_-]{20,}['\"]?",
    "bitcoin_address": r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
}

def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyzes the given text for potential moderation issues.

    This function performs a series of checks and returns a structured
    report. The checks include profanity, personally identifiable information (PII),
    and a list of flagged keywords.

    Args:
        text (str): The text to be analyzed. May be None or empty.

    Returns:
        Dict[str, Any]: A dictionary containing a summary of the moderation results.
    """
    report = {
        "is_flagged": False,
        "flags": [],
        "safety_score": 1.0
    }

    # Normalize input
    safe_text = text or ""

    # Enhanced profanity checking with context awareness
    check_profanity(safe_text, report)

    check_pii(safe_text, report)
    
    check_keywords(safe_text, report)

    return report

def check_profanity(text: str, report: Dict[str, Any]):
    """
    Enhanced profanity detection with context awareness and severity levels.
    
    Uses word boundaries and context to reduce false positives.
    """
    text_lower = text.lower()
    found_profanity = []
    
    for word in PROFANE_WORDS:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            found_profanity.append(word)
    
    if found_profanity:
        # Assess severity (mild warnings for less severe words)
        severe_words = ["fuck", "shit", "bitch", "asshole"]
        is_severe = any(word in found_profanity for word in severe_words)
        
        severity = "high" if is_severe else "low"
        report["is_flagged"] = True if is_severe else report.get("is_flagged", False)
        report["safety_score"] = 0.3 if is_severe else 0.7  # Lower score for profanity
        report["flags"].append({
            "type": "profanity", 
            "severity": severity,
            "message": f"Contains potentially inappropriate language: {', '.join(found_profanity[:3])}",
            "words_found": len(found_profanity)
        })

def check_pii(text: str, report: Dict[str, Any]):
    """
    Enhanced PII detection with context awareness and confidence scoring.
    
    Includes validation to reduce false positives for common patterns.
    """
    pii_found = []
    
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            matched_text = match.group()
            
            # Context-aware validation to reduce false positives
            confidence = _validate_pii_match(pii_type, matched_text, text)
            
            if confidence > 0.3:  # Only flag if confidence is reasonable
                pii_found.append({
                    "type": pii_type,
                    "match": matched_text,
                    "confidence": confidence
                })
    
    if pii_found:
        # Flag as high priority if high-confidence PII detected
        high_confidence = any(item["confidence"] > 0.7 for item in pii_found)
        report["is_flagged"] = True if high_confidence else report.get("is_flagged", False)
        
        # Update safety score based on PII confidence
        if high_confidence:
            report["safety_score"] = min(report.get("safety_score", 1.0), 0.2)  # Very low for high-confidence PII
        else:
            report["safety_score"] = min(report.get("safety_score", 1.0), 0.6)  # Moderate for low-confidence PII
        
        for item in pii_found:
            report["flags"].append({
                "type": "pii", 
                "subtype": item["type"],
                "confidence": item["confidence"],
                "message": f"Potential {item['type'].replace('_', ' ')} detected (confidence: {item['confidence']:.1%})"
            })

def _validate_pii_match(pii_type: str, matched_text: str, full_text: str) -> float:
    """
    Validate PII matches to reduce false positives.
    Returns confidence score from 0.0 to 1.0
    """
    if pii_type == "phone_number":
        # Check if it looks like a real phone number
        digits_only = re.sub(r'\D', '', matched_text)
        if len(digits_only) == 10 or (len(digits_only) == 11 and digits_only.startswith('1')):
            return 0.8
        return 0.3
    
    elif pii_type == "email_address":
        # Higher confidence for complete email addresses
        if '@' in matched_text and '.' in matched_text.split('@')[1]:
            return 0.9
        return 0.4
    
    elif pii_type == "ssn":
        # SSN pattern validation
        digits_only = re.sub(r'\D', '', matched_text)
        if len(digits_only) == 9 and not digits_only.startswith('000'):
            return 0.9
        return 0.2
    
    elif pii_type == "credit_card":
        # Basic Luhn algorithm check could be added here
        digits_only = re.sub(r'\D', '', matched_text)
        if 13 <= len(digits_only) <= 19:
            return 0.7
        return 0.3
    
    elif pii_type == "api_key_pattern":
        # API keys are usually longer and have mixed case
        try:
            # Extract the value part after = or : and strip quotes/spaces
            key_part = re.sub(r"^(?:.*[=:\s])?['\"]?(.+?)['\"]?$", r"\1", matched_text).strip()
        except Exception:
            key_part = matched_text
        if len(key_part) >= 20 and any(c.isupper() for c in key_part) and any(c.islower() for c in key_part):
            return 0.8
        return 0.4
    
    # Default confidence for other types
    return 0.5
            
def check_keywords(text: str, report: Dict[str, Any]):
    """
    Checks for a list of predefined flagged keywords.
    """
    for keyword in FLAGGED_KEYWORDS:
        if keyword.lower() in text.lower():
            report["is_flagged"] = True
            report["flags"].append({"type": "keyword", "message": f"Contains flagged keyword: '{keyword}'."})

# --- Main function for local testing ---
if __name__ == "__main__":
    test_cases: List[str] = [
        "This is a great library, you guys are awesome!",
        "I need help with a damn stupid issue, this shit is so frustrating.",
        "My phone number is 123-456-7890. Please call me.",
        "Contact me at my_email@example.com for more details.",
        "I found a bug. This is an unsafe command and could break things.",
        "Just some normal text with no issues.",
        "My SSN is 123-45-6789 and credit card is 4532-1234-5678-9012",
        "Here's my API key: api_key=sk_test_abcd1234EFGH5678ijkl9012MNOP",
        "Send Bitcoin to this address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "Visit https://user:password@example.com/secret for more info"
    ]

    print("=" * 60)
    print("ENHANCED MODERATION TOOL TEST")
    print("=" * 60)

    for i, test_text in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: '{test_text}'")
        result = analyze_text(test_text)
        print(f"Flagged: {result['is_flagged']}")
        if result['flags']:
            print("Issues found:")
            for flag in result['flags']:
                print(f"  - {flag['type'].upper()}: {flag['message']}")
        else:
            print("  ✅ No issues detected")
        print("-" * 40)
