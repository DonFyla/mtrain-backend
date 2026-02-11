# Testing Guide for Chess Academy Questionnaire

This document explains how to run tests and interpret results for the Chess Academy Questionnaire backend.

---

## Quick Start

```bash
# Run all tests
python run_tests.py

# Run with verbose output (shows test names)
python run_tests.py --verbose

# Run the critical 20-attempts test
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts
```

---

## Test Suite Structure

### Test Classes

| Class | Purpose |
|-------|---------|
| `QtakerCreationTests` | Quiz taker creation and validation |
| `QuizFlowTests` | Question retrieval and answer submission |
| `ScoringAndResultsTests` | Score calculation and pass/fail logic |
| `SkillProgressionTests` | Level progression (beginner → intermediate → expert) |
| `MultipleAttemptsTests` | **Critical**: Same user taking test 20 times |
| `EdgeCaseTests` | Error handling and edge cases |
| `PerformanceTests` | Query optimization and load handling |
| `ModelTests` | Model methods and string representations |
| `IntegrationTests` | End-to-end workflows |

---

## Critical Tests

### 1. Same User 20 Consecutive Attempts

```bash
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts
```

**What it tests:**
- User can take the quiz 20 times in a row without errors
- Each session is isolated (no state pollution)
- Scores reset properly between attempts
- Question sets are randomized each time
- All 20 qtaker records are unique

**Expected output:**
```
✓ Successfully completed 20 consecutive attempts
  - Passed: 10
  - Failed: 10
```

### 2. Rapid Fire Same User

```bash
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_rapid_fire_same_user_no_state_leak
```

**What it tests:**
- 10 qtakers created rapidly with same user info
- Each has independent question set
- No state leakage between sessions

### 3. Progression Chain 20 Levels

```bash
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_progression_chain_20_levels
```

**What it tests:**
- User keeps passing and progressing
- Properly cycles through beginner → intermediate → expert → stays at expert

---

## Running Tests

### Using the Test Runner (Recommended)

```bash
# Run all tests
python run_tests.py

# Verbose mode (shows test names and docstrings)
python run_tests.py --verbose

# Stop on first failure (for debugging)
python run_tests.py --failfast

# Run in parallel (faster)
python run_tests.py --parallel

# List available tests
python run_tests.py --list
```

### Using Django's Test Runner

```bash
# Run all tests
python manage.py test questionnaire.tests

# Run specific test class
python manage.py test questionnaire.tests.MultipleAttemptsTests

# Run specific test method
python manage.py test questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts

# Verbose mode
python manage.py test questionnaire.tests --verbosity=2
```

### Using pytest (if installed)

```bash
# Run all tests
pytest

# Run specific test
pytest questionnaire/tests.py::MultipleAttemptsTests::test_same_user_20_consecutive_attempts

# With coverage report
pytest --cov=questionnaire --cov-report=html
```

---

## Test Data Setup

Tests automatically create:

1. **Admin user** - For creating test data
2. **3 Questionnaires** - beginner, intermediate, expert
3. **30 Questions** - Mix of radio and text types:
   - 10 beginner (radio only)
   - 10 intermediate (mixed)
   - 10 expert (text only)

Each test runs in isolation with a fresh database transaction.

---

## Interpreting Test Results

### Success Output

```
======================================================================
CHESS ACADEMY QUESTIONNAIRE - TEST SUITE
======================================================================

Running tests: questionnaire.tests
Verbosity: 2
Failfast: False
Parallel: False
======================================================================
test_create_qtaker_success (questionnaire.tests.QtakerCreationTests) ... ok
test_same_user_20_consecutive_attempts (questionnaire.tests.MultipleAttemptsTests) ... ok
...
----------------------------------------------------------------------
Ran 40 tests in 12.345s

OK
======================================================================
✅ ALL TESTS PASSED
======================================================================
```

### Failure Output

```
======================================================================
FAIL: test_same_user_20_consecutive_attempts (questionnaire.tests.MultipleAttemptsTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: Failed to create qtaker on attempt 15

======================================================================
❌ TESTS FAILED: 1 failure(s)
======================================================================
```

---

## Debugging Failed Tests

### 1. Run Specific Failing Test

```bash
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts --verbose
```

### 2. Use Django Shell

```bash
python manage.py shell
```

```python
from questionnaire.models import *
from django.contrib.auth.models import User

# Check state
Qtaker.objects.count()
Questionnaire.objects.all()
Question.objects.filter(questionnaire__title='beginner').count()
```

### 3. Check Database

```bash
python manage.py dbshell

# SQLite example
SELECT COUNT(*) FROM questionnaire_qtaker;
SELECT skill, COUNT(*) FROM questionnaire_qtaker GROUP BY skill;
```

---

## Common Issues

### "No questionnaire found for skill level"

**Cause:** Test setup didn't create questionnaire properly.

**Fix:** Check `setUp()` method in `BaseTestCase`.

### "Questions not randomizing"

**Cause:** `current_question_set` being reused.

**Fix:** Check that each qtaker gets fresh randomization in `QtakerView`.

### "State pollution between attempts"

**Cause:** Static variables or class-level state.

**Fix:** Ensure all state is instance-level, not class-level.

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python run_tests.py --verbose
```

---

## Performance Benchmarks

Expected test execution times (approximate):

| Test | Time |
|------|------|
| All tests | ~15-30s |
| 20 consecutive attempts | ~5-10s |
| Single quiz workflow | ~1-2s |

If tests take significantly longer, check for:
- N+1 query problems
- Missing database indexes
- Excessive debug logging

---

## Adding New Tests

```python
class MyNewTests(BaseTestCase):
    def test_my_new_feature(self):
        """Test description here."""
        response = self.create_qtaker()
        # ... test code
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

Always inherit from `BaseTestCase` to get the test data setup.

---

## Contact

For issues with tests, check:
1. `questionnaire/tests.py` - Test implementations
2. `run_tests.py` - Test runner script
3. `TESTING.md` - This file
