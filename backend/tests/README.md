# Backend Tests

This directory contains unit tests for the Leadership Mode implementation.

## Test Files

- `test_intent_leadership.py` - Tests for IntentClassifier leadership detection
- `test_search_leadership.py` - Tests for SearchAgent leadership mode behavior
- `test_icp_profile_fallback.py` - Tests for ICPProfileAgent leadership fallback scraping

## Running Tests

### Using unittest (built-in)

```bash
cd gpt-newspaper/backend
python3 -m unittest discover tests
```

### Using pytest (recommended)

```bash
cd gpt-newspaper
pytest backend/tests/
```

### Running specific test files

```bash
# IntentClassifier tests
python3 -m unittest backend.tests.test_intent_leadership

# SearchAgent tests
python3 -m unittest backend.tests.test_search_leadership

# ICPProfileAgent tests
python3 -m unittest backend.tests.test_icp_profile_fallback
```

## Test Coverage

The tests cover:

1. **IntentClassifier Leadership Detection**
   - Detection of leadership queries with company names
   - Various leadership keywords (CEO, board, executive team, etc.)
   - Non-leadership queries should not trigger leadership mode

2. **SearchAgent Leadership Mode**
   - Uses max_results=20 for leadership queries
   - Removes US-only restriction (changes region to GLOBAL)
   - Query rewriting with leadership keywords
   - Time range defaults to "year" for leadership
   - Source prioritization (company domains first, then Wikipedia, etc.)
   - Minimum 15 results for leadership queries

3. **ICPProfileAgent Fallback**
   - Triggers HTML scraping fallback when no leaders found
   - Does NOT trigger when leaders already exist
   - Correctly sets `is_icp_title` based on buying role keywords
   - Preserves existing leaders when fallback is not needed

## Notes

- Tests use mocking to avoid actual API calls to Tavily, LLM services, etc.
- Some tests require environment variables (TAVILY_API_KEY, GROQ_API_KEY) but will skip if not available
- Tests are designed to run quickly without external dependencies

