# Custom Detector Alert Storage - Fix Summary

## Problem

Custom detector alerts were firing and triggering callbacks, but weren't being stored:
- `get_all_alerts()` returned empty list
- `export_alerts()` exported empty JSON
- Callbacks fired correctly (48+ alerts)

## Root Cause

**Two bugs were found and fixed:**

### Bug 1: Missing storage for custom alerts
`get_all_alerts()` only checked `detector.alerts` for `BaseDetector` instances. Custom detectors are plain functions, not `BaseDetector` instances.

### Bug 2: `reset()` was clearing historical alerts
After fixing Bug 1, alerts were stored during episodes but cleared when `reset()` was called (at episode end). The `reset()` method should only clear per-episode state (buffers), not historical alerts.

## Solution

### Fix 1: Add storage for custom detector alerts

**File:** `reward_scope/core/detectors.py`

1. **Added `_custom_alerts` list** (line 895):
   ```python
   self._custom_alerts: List[HackingAlert] = []
   ```

2. **Store alerts when custom detectors fire** (line 1057):
   ```python
   self._custom_alerts.append(alert)
   ```

3. **Include in `get_all_alerts()`** (lines 1341-1342):
   ```python
   # Include custom detector alerts
   alerts.extend(self._custom_alerts)
   ```

### Fix 2: Preserve alerts across `reset()`

**File:** `reward_scope/core/detectors.py`

**Removed** the incorrect clear operation (line 1396):
```python
# REMOVED: self._custom_alerts.clear()
# Note: We intentionally do NOT reset _custom_alerts here because
# historical alerts should persist (same as detector.alerts).
```

## Verification

All tests pass with alerts properly stored and persisting:

```
Callbacks fired:                50 alerts  ✅
env.get_alerts():              50 alerts  ✅
suite.get_all_alerts():        50 alerts  ✅
suite._custom_alerts:          50 alerts  ✅
Export working:                Yes        ✅
Persists across episodes:      Yes        ✅
```

## Commits

1. **941b783** - Fix custom detector alert storage (initial fix)
2. **21782bb** - Fix reset() clearing custom detector alerts (critical fix)

## Testing

Run the verification script:
```bash
python test_final_verification.py
```

Expected output: All tests pass with matching alert counts.
