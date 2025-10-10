"""
Intelligent caching system for AI agent cost estimations.

This module implements a multi-layered caching strategy that:
1. Generates deterministic cache keys based on ALL relevant factors
2. Supports multiple cache backends (memory, disk, Redis)
3. Implements TTL (Time To Live) with configurable expiration
4. Provides cache invalidation strategies
5. Handles partial caching for intermediate results
6. Monitors cache effectiveness
"""

import hashlib
import json
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict
from decimal import Decimal
import logging

from cachetools import TTLCache, LRUCache
from .config import get_config

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """
    Intelligent cache key generation based on all factors that affect cost estimation.

    Best Practice: Include EVERY factor that could influence the result in the cache key.
    """

    @staticmethod
    def generate_specification_key(spec_dict: Dict[str, Any]) -> str:
        """
        Generate a deterministic hash key from application specification.

        Includes:
        - Application metadata (name, complexity, users, usage patterns)
        - Agent configurations (models, tools, complexity)
        - Infrastructure settings (provider, region, scaling)
        - Data requirements (storage, processing)
        - Cost constraints and preferences
        """
        # Extract all relevant fields in a deterministic order
        key_factors = {
            "application": spec_dict.get("application", {}),
            "agents": spec_dict.get("agents", []),
            "infrastructure": spec_dict.get("infrastructure", {}),
            "data_requirements": spec_dict.get("data_requirements", {}),
            "cost_constraints": spec_dict.get("cost_constraints", {}),
        }

        # Sort all nested dictionaries and lists for determinism
        normalized = CacheKeyGenerator._normalize_for_hashing(key_factors)

        # Generate SHA256 hash
        json_str = json.dumps(normalized, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    @staticmethod
    def generate_pricing_key(provider: str, region: str, service: str, date: str = None) -> str:
        """
        Generate cache key for pricing data.

        Pricing can be cached longer as it changes less frequently,
        but should be tied to provider, region, service, and optionally date.
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        key_data = {
            "provider": provider,
            "region": region,
            "service": service,
            "date": date
        }
        json_str = json.dumps(key_data, sort_keys=True)
        return f"pricing_{hashlib.sha256(json_str.encode()).hexdigest()}"

    @staticmethod
    def generate_llm_analysis_key(
        input_text: str,
        model: str,
        agent_type: str,
        temperature: float = 0.0
    ) -> str:
        """
        Generate cache key for LLM analysis results.

        For deterministic LLM calls (temperature=0), we can cache results.
        Include model version to invalidate when models are updated.
        """
        key_data = {
            "input_hash": hashlib.sha256(input_text.encode()).hexdigest(),
            "model": model,
            "agent_type": agent_type,
            "temperature": temperature
        }
        json_str = json.dumps(key_data, sort_keys=True)
        return f"llm_{hashlib.sha256(json_str.encode()).hexdigest()}"

    @staticmethod
    def _normalize_for_hashing(obj: Any) -> Any:
        """Recursively normalize objects for deterministic hashing."""
        if isinstance(obj, dict):
            return {k: CacheKeyGenerator._normalize_for_hashing(v)
                   for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [CacheKeyGenerator._normalize_for_hashing(item) for item in obj]
        elif isinstance(obj, (Decimal, float)):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj


class CacheBackend:
    """Abstract base for cache backends."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache using cachetools with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.cache = TTLCache(maxsize=max_size, ttl=default_ttl)
        self.metadata = {}  # Track cache metadata

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.cache.get(key)
            if value is not None:
                # Update access stats
                if key in self.metadata:
                    self.metadata[key]["hits"] += 1
                    self.metadata[key]["last_accessed"] = datetime.now().isoformat()
            return value
        except KeyError:
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        self.cache[key] = value
        self.metadata[key] = {
            "created_at": datetime.now().isoformat(),
            "ttl": ttl or self.default_ttl,
            "hits": 0,
            "size_bytes": len(pickle.dumps(value))
        }

    def delete(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]
        if key in self.metadata:
            del self.metadata[key]

    def clear(self) -> None:
        self.cache.clear()
        self.metadata.clear()

    def exists(self, key: str) -> bool:
        return key in self.cache

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_keys": len(self.cache),
            "max_size": self.cache.maxsize,
            "total_size_bytes": sum(m.get("size_bytes", 0) for m in self.metadata.values()),
            "total_hits": sum(m.get("hits", 0) for m in self.metadata.values()),
        }


class DiskCacheBackend(CacheBackend):
    """Persistent disk-based cache for longer-term storage."""

    def __init__(self, cache_dir: Path, default_ttl: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_metadata(self) -> None:
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.cache"

    def _is_expired(self, key: str) -> bool:
        if key not in self.metadata:
            return True

        created_at = datetime.fromisoformat(self.metadata[key]["created_at"])
        ttl = self.metadata[key].get("ttl", self.default_ttl)
        expiry_time = created_at + timedelta(seconds=ttl)

        return datetime.now() > expiry_time

    def get(self, key: str) -> Optional[Any]:
        if self._is_expired(key):
            self.delete(key)
            return None

        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'rb') as f:
                value = pickle.load(f)

            # Update access stats
            if key in self.metadata:
                self.metadata[key]["hits"] += 1
                self.metadata[key]["last_accessed"] = datetime.now().isoformat()
                self._save_metadata()

            return value
        except Exception as e:
            logger.warning(f"Failed to load cache for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)

            self.metadata[key] = {
                "created_at": datetime.now().isoformat(),
                "ttl": ttl or self.default_ttl,
                "hits": 0,
                "file_path": str(cache_path)
            }
            self._save_metadata()

        except Exception as e:
            logger.error(f"Failed to save cache for key {key}: {e}")

    def delete(self, key: str) -> None:
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
        if key in self.metadata:
            del self.metadata[key]
            self._save_metadata()

    def clear(self) -> None:
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        self.metadata.clear()
        self._save_metadata()

    def exists(self, key: str) -> bool:
        return not self._is_expired(key) and self._get_cache_path(key).exists()


class IntelligentCacheManager:
    """
    Multi-layered intelligent cache manager for AI cost estimation.

    Implements a tiered caching strategy:
    - L1: Memory cache (fast, small, short TTL)
    - L2: Disk cache (persistent, larger, longer TTL)
    - L3: Optional Redis cache (distributed, shared across instances)
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()

        # Initialize cache backends
        self.memory_cache = MemoryCacheBackend(
            max_size=self.config.get("memory_max_size", 100),
            default_ttl=self.config.get("memory_ttl", 3600)  # 1 hour
        )

        cache_dir = Path(self.config.get("cache_dir", ".cache"))
        self.disk_cache = DiskCacheBackend(
            cache_dir=cache_dir,
            default_ttl=self.config.get("disk_ttl", 86400)  # 24 hours
        )

        self.key_generator = CacheKeyGenerator()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "llm_calls_saved": 0,
            "api_calls_saved": 0
        }

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default cache configuration."""
        app_config = get_config()
        return {
            "enabled": True,
            "memory_max_size": 100,
            "memory_ttl": 3600,  # 1 hour
            "disk_ttl": 86400,  # 24 hours
            "pricing_ttl": 86400 * 7,  # 1 week for pricing data
            "llm_ttl": 86400 * 30,  # 30 days for LLM analysis (if deterministic)
            "cache_dir": ".cache/cost_estimator",
            "cache_llm_results": True,  # Cache LLM analysis results
            "cache_pricing": True,  # Cache pricing data
            "cache_full_estimations": True,  # Cache complete estimations
        }

    def get_estimation(self, spec_dict: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached cost estimation if available.

        Returns the full estimation state if found in cache.
        """
        if not self.config.get("cache_full_estimations", True):
            return None

        key = self.key_generator.generate_specification_key(spec_dict)

        # Try L1 cache (memory) first
        result = self.memory_cache.get(key)
        if result is not None:
            self.stats["hits"] += 1
            logger.info(f"Cache HIT (memory) for estimation key: {key[:16]}...")
            return result

        # Try L2 cache (disk)
        result = self.disk_cache.get(key)
        if result is not None:
            self.stats["hits"] += 1
            # Promote to L1 cache
            self.memory_cache.set(key, result)
            logger.info(f"Cache HIT (disk) for estimation key: {key[:16]}...")
            return result

        self.stats["misses"] += 1
        logger.info(f"Cache MISS for estimation key: {key[:16]}...")
        return None

    def set_estimation(self, spec_dict: Dict[str, Any], result: Any, ttl: int = None) -> None:
        """Cache a cost estimation result."""
        if not self.config.get("cache_full_estimations", True):
            return

        key = self.key_generator.generate_specification_key(spec_dict)
        ttl = ttl or self.config.get("disk_ttl", 86400)

        # Store in both caches
        self.memory_cache.set(key, result)
        self.disk_cache.set(key, result, ttl=ttl)

        logger.info(f"Cached estimation result for key: {key[:16]}... (TTL: {ttl}s)")

    def get_llm_analysis(self, input_text: str, model: str, agent_type: str) -> Optional[str]:
        """Get cached LLM analysis result."""
        if not self.config.get("cache_llm_results", True):
            return None

        key = self.key_generator.generate_llm_analysis_key(input_text, model, agent_type)

        result = self.memory_cache.get(key) or self.disk_cache.get(key)
        if result:
            self.stats["llm_calls_saved"] += 1
            logger.info(f"LLM cache HIT for agent: {agent_type}")

        return result

    def set_llm_analysis(
        self,
        input_text: str,
        model: str,
        agent_type: str,
        result: str
    ) -> None:
        """Cache an LLM analysis result."""
        if not self.config.get("cache_llm_results", True):
            return

        key = self.key_generator.generate_llm_analysis_key(input_text, model, agent_type)
        ttl = self.config.get("llm_ttl", 86400 * 30)

        self.memory_cache.set(key, result)
        self.disk_cache.set(key, result, ttl=ttl)

    def get_pricing(self, provider: str, region: str, service: str) -> Optional[Any]:
        """Get cached pricing data."""
        if not self.config.get("cache_pricing", True):
            return None

        key = self.key_generator.generate_pricing_key(provider, region, service)

        result = self.memory_cache.get(key) or self.disk_cache.get(key)
        if result:
            self.stats["api_calls_saved"] += 1
            logger.info(f"Pricing cache HIT for {provider}/{region}/{service}")

        return result

    def set_pricing(
        self,
        provider: str,
        region: str,
        service: str,
        pricing_data: Any
    ) -> None:
        """Cache pricing data."""
        if not self.config.get("cache_pricing", True):
            return

        key = self.key_generator.generate_pricing_key(provider, region, service)
        ttl = self.config.get("pricing_ttl", 86400 * 7)

        self.memory_cache.set(key, pricing_data)
        self.disk_cache.set(key, pricing_data, ttl=ttl)

    def invalidate_estimation(self, spec_dict: Dict[str, Any]) -> None:
        """Invalidate a specific estimation cache."""
        key = self.key_generator.generate_specification_key(spec_dict)
        self.memory_cache.delete(key)
        self.disk_cache.delete(key)
        logger.info(f"Invalidated cache for key: {key[:16]}...")

    def invalidate_all(self) -> None:
        """Clear all caches."""
        self.memory_cache.clear()
        self.disk_cache.clear()
        logger.info("Cleared all caches")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "overall": self.stats,
            "memory_cache": self.memory_cache.get_stats(),
            "hit_rate": (
                self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
            ),
            "config": self.config
        }


# Global cache instance
_cache_manager: Optional[IntelligentCacheManager] = None


def get_cache_manager() -> IntelligentCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = IntelligentCacheManager()
    return _cache_manager


def invalidate_cache():
    """Invalidate all caches."""
    cache_manager = get_cache_manager()
    cache_manager.invalidate_all()
