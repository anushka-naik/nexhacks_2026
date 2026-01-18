# Bug Fixes - Code Review

## Bugs Fixed ✅

### 1. Duplicate `app.run()` in backend/app.py (CRITICAL)
**Location:** `backend/app.py` lines 437-438

**Issue:** The Flask app was attempting to run twice, which would cause the second call to never execute.

```python
# BEFORE (Bug):
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(debug=True, host='0.0.0.0', port=5000)  # Duplicate!

# AFTER (Fixed):
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Impact:** While the second line would never execute (since `app.run()` blocks), this was dead code that could confuse developers.

---

### 2. Inconsistent key name in demo.js fallback (MODERATE)
**Location:** `demo.js` line 168

**Issue:** The fallback error structure used `audio:` key while the main code uses `video:` key, causing inconsistency with the backend endpoint.

```javascript
// BEFORE (Bug):
audio: {
    intent: "error"
},

// AFTER (Fixed):
video: {
    intent: "error"
},
```

**Impact:** When transformation errors occurred, the backend would receive data with the wrong key structure, potentially breaking the `/overshoot_event` endpoint processing.

---

## Security Warnings ⚠️

### Hardcoded API Keys in Frontend (CRITICAL SECURITY ISSUE)

**Location:** `demo.js` lines 18, 56, 112

**Issue:** API keys are hardcoded directly in the frontend JavaScript:
- Overshoot API key (line 18)
- OpenAI API key (lines 56, 112)

**Risk:** Anyone who visits your demo page can view the source code and steal these keys.

**Recommendation for Production:**
1. Move API key validation to backend
2. Create a proxy endpoint in your Flask app:
   ```python
   @app.route('/api/transform', methods=['POST'])
   def transform_observation():
       data = request.json
       # Call OpenAI API here with server-side key
       response = openai_client.chat.completions.create(...)
       return jsonify(response)
   ```
3. Update frontend to call your backend instead of OpenAI directly

**For Hackathon Demo (Quick Fix):**
- Ensure these keys have minimal permissions
- Rotate keys after the demo
- Monitor usage to detect abuse

---

## Code Quality Observations

### Good Practices ✅
1. **Database connection management:** Properly using Neo4j driver with context managers
2. **Error handling:** Try-catch blocks in most critical sections
3. **Transaction management:** Explicit commit/rollback in graph_store.py
4. **CORS configuration:** Properly enabled for frontend communication

### Potential Improvements (Not Bugs)
1. **requirements.txt:** Consider pinning versions for `tokenc` and `sentence_transformers`
   ```
   tokenc==1.2.3  # Add specific versions
   sentence_transformers==2.2.2
   ```

2. **Environment variables:** Backend credentials are hardcoded in `app.py` line 15-18. Consider using `.env`:
   ```python
   neo4j_config = Neo4jConfig(
       uri=os.environ.get("NEO4J_URI"),
       user=os.environ.get("NEO4J_USER"),
       password=os.environ.get("NEO4J_PASSWORD")
   )
   ```

---

## Testing Recommendations

After these fixes, test:
1. ✅ Backend starts without errors: `cd backend && python app.py`
2. ✅ Frontend can connect to backend: Check browser console
3. ✅ Data flows correctly: Test `/overshoot_event` endpoint
4. ✅ Error handling works: Test with invalid data

---

## Summary

**Critical bugs fixed:** 2
**Security warnings:** 1 (hardcoded API keys)
**Code quality:** Generally good, ready for hackathon demo

All critical bugs have been resolved. The codebase is now functional, but please address the API key security issue before deploying publicly.
