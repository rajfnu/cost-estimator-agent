# Intelligent Caching System for Cost Estimator Agent

## Overview

The Cost Estimator Agent now includes an **intelligent multi-layered caching system** that automatically determines when to use cached results vs. making new LLM/API calls. This dramatically reduces costs and improves performance for repeated estimations.

## 🎯 Key Features

### 1. **Intelligent Cache Key Generation**
- Generates deterministic hash keys based on **ALL factors** that affect cost estimation
- Includes: application specs, agent configs, infrastructure settings, data requirements, cost constraints
- Uses SHA-256 hashing for uniqueness and security
- Automatically invalidates cache when ANY relevant factor changes

### 2. **Multi-Layered Caching**
- **L1 Cache (Memory)**: Fast, in-process cache with 1-hour TTL
- **L2 Cache (Disk)**: Persistent cache across runs with 24-hour TTL
- **L3 Cache (Optional Redis)**: Distributed caching for multi-instance deployments (coming soon)

### 3. **Granular Caching Options**
Cache different types of data with different TTLs:
- **Full Estimations**: 24 hours (configurable)
- **LLM Analysis Results**: 30 days (for deterministic calls)
- **Pricing Data**: 7 days (pricing changes infrequently)

### 4. **Smart Cache Invalidation**
- Automatic cache expiration based on TTL
- Manual cache clearing via CLI
- Version-based invalidation
- Factor-based invalidation (any spec change invalidates)

## 📊 Performance Impact

### Test Results (minimal_example.json):

| Run | Time | API Calls | Cost | Status |
|-----|------|-----------|------|--------|
| **First Run** | ~41 seconds | 3 OpenAI calls | ~$0.003 | Cache MISS |
| **Second Run** | ~1 second | 0 API calls | $0.00 | ✅ Cache HIT |
| **Third Run** | ~1 second | 0 API calls | $0.00 | ✅ Cache HIT |

**Performance Improvement: 40x faster, 100% cost savings on cached runs!**

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Enable/Disable Caching
CACHE_ENABLED=true                    # Master switch
CACHE_FULL_ESTIMATIONS=true          # Cache complete estimations
CACHE_LLM_RESULTS=true               # Cache LLM analysis
CACHE_PRICING_DATA=true              # Cache pricing lookups

# Memory Cache Settings
MEMORY_CACHE_SIZE=100                # Max items in memory
MEMORY_CACHE_TTL=3600                # 1 hour (seconds)

# Disk Cache Settings
DISK_CACHE_TTL=86400                 # 24 hours (seconds)
CACHE_DIRECTORY=.cache/cost_estimator

# Specific TTLs
ESTIMATION_CACHE_TTL=86400           # 24 hours for full estimations
PRICING_CACHE_TTL=604800             # 7 days for pricing data
LLM_CACHE_TTL=2592000                # 30 days for LLM results

# Cache Versioning
CACHE_VERSION=1.0                     # Increment to invalidate all caches
AUTO_INVALIDATE_ON_VERSION_CHANGE=true
```

## 🚀 Usage

### Running Cost Estimations (Automatic Caching)

```bash
# First run - will make API calls and cache result
./run_estimator.sh estimate examples/minimal_example.json

# Second run - uses cached result (no API calls!)
./run_estimator.sh estimate examples/minimal_example.json

# Force refresh (bypass cache)
./run_estimator.sh estimate examples/minimal_example.json --force-refresh
```

### Cache Management Commands

#### View Cache Statistics
```bash
./run_estimator.sh cache stats
```

Output:
```
📊 Cache Statistics

 Overall Cache Performance
┌─────────────────┬───────┐
│ Metric          │ Value │
├─────────────────┼───────┤
│ Cache Hits      │ 5     │
│ Cache Misses    │ 2     │
│ Hit Rate        │ 71.4% │
│ LLM Calls Saved │ 15    │
│ API Calls Saved │ 10    │
└─────────────────┴───────┘
```

#### View Cache Configuration
```bash
./run_estimator.sh cache info
```

#### Clear All Caches
```bash
./run_estimator.sh cache clear
```

## 🔍 How It Works

### Cache Key Generation

The system generates a unique cache key based on ALL factors that affect estimation:

```python
Cache Key = SHA256({
    "application": {
        "name": "...",
        "complexity": "...",
        "expected_users": ...,
        "usage_patterns": {...}
    },
    "agents": [{...}],
    "infrastructure": {...},
    "data_requirements": {...},
    "cost_constraints": {...}
})
```

**Result**: `672c5e601ba35200a88b5fc6fec2cd0641ed41c60670ec9381675bedf5750c52`

### Cache Lookup Flow

```
1. User runs estimation
2. System generates cache key from specification
3. Check L1 (Memory) cache → HIT? Return result
4. Check L2 (Disk) cache → HIT? Return result + promote to L1
5. MISS → Execute full estimation with LLM calls
6. Cache result in both L1 and L2
7. Return result to user
```

### When Cache is Invalidated

The cache is automatically invalidated when:

1. **Specification Changes**: Any modification to the JSON spec
   - Different user count → New cache key
   - Different model → New cache key
   - Different region → New cache key
   - etc.

2. **TTL Expires**:
   - Memory cache: 1 hour
   - Disk cache: 24 hours
   - Pricing data: 7 days
   - LLM results: 30 days

3. **Manual Invalidation**:
   ```bash
   ./run_estimator.sh cache clear
   ```

4. **Version Change**: Update `CACHE_VERSION` in .env

## 🎨 Best Practices

### 1. **For Development**
```bash
# Shorter TTLs for frequent changes
MEMORY_CACHE_TTL=300      # 5 minutes
DISK_CACHE_TTL=3600       # 1 hour
```

### 2. **For Production**
```bash
# Longer TTLs for stable estimates
MEMORY_CACHE_TTL=3600     # 1 hour
DISK_CACHE_TTL=86400      # 24 hours
PRICING_CACHE_TTL=604800  # 7 days
```

### 3. **For Cost Optimization**
- Enable all caching options
- Use longer TTLs for stable specs
- Cache pricing data separately (changes infrequently)
- Monitor cache hit rate with `cache stats`

### 4. **For Accuracy**
- Shorter TTLs ensure fresh pricing
- Use `--force-refresh` for critical estimates
- Clear cache when pricing models change
- Monitor cache confidence in reports

## 📈 Monitoring

### Cache Effectiveness Metrics

The system tracks:
- **Hit Rate**: % of requests served from cache
- **LLM Calls Saved**: Number of expensive LLM API calls avoided
- **API Calls Saved**: Number of pricing API calls avoided
- **Cache Size**: Memory and disk usage
- **TTL Status**: Time until expiration

### Example Monitoring
```bash
# Check cache effectiveness
./run_estimator.sh cache stats

# View cache files
ls -lah .cache/cost_estimator/

# Monitor cache hits in real-time
./run_estimator.sh estimate examples/minimal_example.json 2>&1 | grep -i cache
```

## 🔒 Security Considerations

1. **Cache Keys**: SHA-256 hashed, no sensitive data exposed
2. **Storage**: Cached data stored locally in `.cache/` directory
3. **Permissions**: Cache files use standard file permissions
4. **API Keys**: Never cached, always loaded from environment

## 🐛 Troubleshooting

### Cache Not Working?

1. **Check if caching is enabled**
   ```bash
   ./run_estimator.sh cache info
   ```

2. **Verify .env configuration**
   ```bash
   grep CACHE .env
   ```

3. **Check cache directory permissions**
   ```bash
   ls -la .cache/cost_estimator/
   ```

4. **Clear cache and retry**
   ```bash
   ./run_estimator.sh cache clear
   ./run_estimator.sh estimate examples/minimal_example.json
   ```

### Getting Different Results?

If you're getting cached results when you expect new ones:

1. **Verify specification changed**
   - Cache key is generated from ALL fields
   - Even minor changes create new cache key

2. **Force refresh**
   ```bash
   ./run_estimator.sh estimate <file> --force-refresh
   ```

3. **Check TTL hasn't expired**
   - View cache metadata: `cat .cache/cost_estimator/metadata.json`

## 🚀 Advanced Usage

### Programmatic Cache Control

```python
from cost_estimator.cache import get_cache_manager

cache = get_cache_manager()

# Check cache
result = cache.get_estimation(spec_dict)

# Force cache update
cache.set_estimation(spec_dict, result, ttl=3600)

# Invalidate specific estimation
cache.invalidate_estimation(spec_dict)

# Get statistics
stats = cache.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

### Custom TTLs per Estimation

```python
# Cache this estimation for 1 week (critical baseline)
cache.set_estimation(spec_dict, result, ttl=604800)

# Cache this estimation for 1 hour (rapidly changing)
cache.set_estimation(spec_dict, result, ttl=3600)
```

## 📚 Related Documentation

- [Configuration Guide](CONFIGURATION.md)
- [Testing Guide](TESTING.md)
- [Deployment Guide](DEPLOYMENT.md)

## 🤝 Contributing

To improve caching:
1. Add new cache backends (Redis, Memcached)
2. Implement cache warming strategies
3. Add cache analytics dashboard
4. Optimize cache key generation

---

**Questions or Issues?**
- GitHub Issues: https://github.com/your-org/cost-estimator-agent/issues
- Documentation: https://docs.cost-estimator.ai
