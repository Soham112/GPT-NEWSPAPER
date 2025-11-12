"""
Caching utility for research results.
Supports file-based caching (default) with S3 structure ready.
"""
import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.config import ENABLE_CACHE, CACHE_TTL_HOURS

CACHE_DIR = "cache/research"
S3_BUCKET = os.getenv("S3_BUCKET", None)  # Set if using S3
S3_PREFIX = "knowledge-agent/on-demand/research"


def _hash_key(topic: str, domains: list = None, time_range: str = "week", k: int = 5) -> str:
    """Generate cache key hash."""
    key_str = f"{topic}:{sorted(domains or [])}:{time_range}:{k}"
    return hashlib.sha256(key_str.encode()).hexdigest()


def _get_cache_path(key: str) -> str:
    """Get file path for cache key."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def _is_cache_valid(cache_data: Dict[str, Any]) -> bool:
    """Check if cache entry is still valid."""
    if not cache_data:
        return False
    
    cached_time = cache_data.get("cached_at")
    if not cached_time:
        return False
    
    try:
        cached_dt = datetime.fromisoformat(cached_time)
        age = datetime.now() - cached_dt
        return age < timedelta(hours=CACHE_TTL_HOURS)
    except:
        return False


def get_cache(topic: str, domains: list = None, time_range: str = "week", k: int = 5) -> Optional[Dict[str, Any]]:
    """Get cached result if available and valid."""
    if not ENABLE_CACHE:
        return None
    
    key = _hash_key(topic, domains, time_range, k)
    
    # File-based cache
    cache_path = _get_cache_path(key)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)
            
            if _is_cache_valid(cache_data):
                print(f"Cache hit for topic: {topic}")
                return cache_data.get("data")
            else:
                # Remove stale cache
                os.remove(cache_path)
        except Exception as e:
            print(f"Cache read error: {e}")
    
    # TODO: S3 cache implementation
    # if S3_BUCKET:
    #     s3_key = f"{S3_PREFIX}/{key}.json"
    #     # Implement S3 get logic here
    
    return None


def set_cache(topic: str, data: Dict[str, Any], domains: list = None, time_range: str = "week", k: int = 5):
    """Cache result."""
    if not ENABLE_CACHE:
        return
    
    key = _hash_key(topic, domains, time_range, k)
    cache_path = _get_cache_path(key)
    
    cache_data = {
        "cached_at": datetime.now().isoformat(),
        "data": data,
    }
    
    try:
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
        print(f"Cached result for topic: {topic}")
    except Exception as e:
        print(f"Cache write error: {e}")
    
    # TODO: S3 cache implementation
    # if S3_BUCKET:
    #     s3_key = f"{S3_PREFIX}/{key}.json"
    #     # Implement S3 put logic here

