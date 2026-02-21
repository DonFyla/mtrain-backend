# Chess Academy - Developer Guide

A comprehensive guide for developers working on the Chess Academy Questionnaire backend.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Data Models Deep Dive](#data-models-deep-dive)
5. [API Flow & Logic](#api-flow--logic)
6. [Key Implementation Details](#key-implementation-details)
7. [Development Workflow](#development-workflow)
8. [Testing & Debugging](#testing--debugging)
9. [Deployment Notes](#deployment-notes)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

The Chess Academy Questionnaire is a skill-assessment platform that delivers adaptive chess quizzes. Users progress through three levels (Beginner → Intermediate → Expert) by answering questions and scoring above 60%.

### Core Features
- **Multi-level progression**: 3 skill levels with automatic promotion
- **Question types**: Multiple choice (radio) and text-based answers
- **Session management**: 5 randomized questions per quiz session
- **Rich content**: CKEditor for HTML-formatted questions
- **REST API**: Stateless, JSON-based API for frontend integration

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Django REST   │────▶│   Database      │
│   (React/etc)   │◄────│   API           │◄────│   (SQLite/PG)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Admin Panel   │
                        │   (CKEditor)    │
                        └─────────────────┘
```

### Tech Stack
| Layer | Technology |
|-------|------------|
| Framework | Django 5.2 + Django REST Framework |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Rich Text | CKEditor + CKEditor Uploader |
| Static Files | WhiteNoise |
| CORS | django-cors-headers |
| Deployment | Railway |

---

## Project Structure

```
backend/
├── backend/                 # Project configuration
│   ├── __init__.py
│   ├── asgi.py             # ASGI config
│   ├── settings.py         # All settings
│   ├── urls.py             # Root URL routes
│   └── wsgi.py             # WSGI config
├── questionnaire/           # Main application
│   ├── admin.py            # Admin panel config
│   ├── apps.py             # App config
│   ├── forms.py            # Django forms
│   ├── models.py           # Data models
│   ├── serializers.py      # DRF serializers
│   ├── urls.py             # App URL routes
│   ├── utils.py            # Utility functions
│   ├── views.py            # API views
│   └── migrations/         # Database migrations
├── media/                  # User-uploaded files
│   └── uploads/            # CKEditor uploads
├── staticfiles/            # Collected static files
├── API_DOCUMENTATION.md    # API reference
├── DEVELOPER_GUIDE.md      # This file
├── manage.py               # Django management
├── requirements.txt        # Dependencies
└── runtime.txt             # Python version
```

---

## Data Models Deep Dive

### Questionnaire
The container for a skill level's questions.

```python
title = models.CharField(max_length=255, unique=True)
# Values: "beginner", "intermediate", "expert"
```

**Important**: The `title` field must exactly match the skill level choices in `Qtaker.chess_level`. This coupling is used in views to fetch the correct questionnaire.

### Qtaker (Quiz Taker)
Core user model for quiz sessions.

| Field | Purpose |
|-------|---------|
| `name`, `age`, `email` | User info |
| `skill` | Current level (beginner/intermediate/expert) |
| `current_score` | Running score in current session |
| `test_result` | Final percentage (set on completion) |
| `current_question_set` | JSON array of question IDs for current quiz |
| `next_question_set` | JSON array for next level (when promoted) |
| `last_question_id` | Tracks last answered question |
| `last_text_answer` | Stores text answer for validation |

**Progression Logic**:
```python
# In Qtaker model
@classmethod
def get_next_skill(cls, current_skill):
    skills = ["beginner", "intermediate", "expert"]
    # Returns next skill or None if at expert level
```

### Question
Individual quiz questions.

| Field | Details |
|-------|---------|
| `questionnaire` | FK to parent questionnaire |
| `question_type` | "radio" or "text" |
| `question` | Rich text (HTML via CKEditor) |
| `placement` | Order within questionnaire |

### Options
Answer choices for questions.

```python
question = models.ForeignKey(Question, on_delete=models.CASCADE)
text = models.TextField()      # WYSIWYG content
correct = models.BooleanField()  # Only one should be True
```

**Note**: For text-type questions, create one Option with the correct answer text.

---

## API Flow & Logic

### 1. Starting a Quiz (`POST /api/qtaker/`)

```
User submits info → Create Qtaker → Randomize 5 questions 
→ Store in current_question_set → Return first question ID
```

**Key Code** (`views.py:27-36`):
```python
# Randomize questions
randomized_questions = all_questions.order_by('?')[:questions_to_take]
randomized_question_ids = list(randomized_questions.values_list('id', flat=True))

# Store in session
qtaker.current_question_set = randomized_question_ids
qtaker.save()
```

### 2. Fetching Questions (`GET /api/quiz/<qtaker_id>/<question_id>/`)

```
Get Qtaker → Check skill → Load current_question_set 
→ Find question by ID → Return with options
```

**State Handling**:
- Uses `current_question_set` JSONField to track session
- Falls back to creating new set if none exists

### 3. Submitting Answers (`POST /api/quiz/<qtaker_id>/<question_id>/`)

**Radio Questions**:
```python
chosen_opt = Options.objects.get(pk=answer_str, question=question)
is_correct = chosen_opt.correct
```

**Text Questions**:
```python
correct_opt = Options.objects.get(question=question, correct=True)
is_correct = answer_str.strip().lower() == correct_opt.text.strip().lower()
```

**Important**: Text comparison is case-insensitive.

### 4. Viewing Results (`GET /api/answer/<qtaker_id>/<answer_id>/`)

Handles scoring increment here:
```python
if is_correct:
    qtaker.current_score += 1
    qtaker.save()
```

### 5. Final Results (`GET /api/result/<qtaker_id>/`)

**Pass Condition**: `score > 60%`

**On Pass**:
1. Calculate next skill level
2. Create randomized question set for next level
3. Store in `next_question_set`
4. Update `qtaker.skill` to next level

**On Fail**:
- Returns current level info
- No promotion

---

## Key Implementation Details

### Randomization Strategy

Questions are randomized at session start, not per-request:

```python
# Happens once when qtaker is created
randomized_questions = all_questions.order_by('?')[:5]
question_ids = list(randomized_questions.values_list('id', flat=True))
qtaker.current_question_set = question_ids
```

This ensures consistent question order during a session.

### Question Set State Machine

```
[current_question_set] ──▶ On Pass ──▶ [next_question_set]
                                     │
                                     ▼
                    Becomes new [current_question_set]
```

### CKEditor Integration

Configured in `settings.py`:
```python
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'filebrowserUploadUrl': '/ckeditor/upload/',
    },
}
```

**Note**: Uploads go to `/media/uploads/` directory.

### Database Configuration

Auto-switches based on `DATABASE_URL`:

```python
if DATABASE_URL:
    # Production: PostgreSQL (Railway)
    DATABASES = {'default': dj_database_url.config(...)}
else:
    # Development: SQLite
    DATABASES = {...sqlite3...}
```

---

## Development Workflow

### Local Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Start server
python manage.py runserver
```

### Creating Questionnaires (Admin)

1. Go to `/admin/`
2. Create Questionnaire with title exactly matching skill level
3. Add Questions with placements (1, 2, 3...)
4. For radio: add multiple Options, mark one correct
5. For text: add one Option with the exact correct answer text

### Adding New Question Types

To add a new question type (e.g., "checkbox" for multiple answers):

1. **Model** (`models.py`):
   ```python
   QUESTION_TYPES = [
       ("text", "Text Answer"),
       ("radio", "Single Choice"),
       ("checkbox", "Multiple Choice"),  # Add this
   ]
   ```

2. **View** (`views.py`):
   - Update answer validation in `quiz()` view
   - Handle list of answers instead of single value

3. **Serializer** (`serializers.py`):
   - May need to adjust `AnswerFormSerializer`

---

## Testing & Debugging

### Running Tests

The project includes comprehensive tests to ensure code quality and prevent bugs.

#### Quick Test Commands

```bash
# Run critical tests (fast)
python manage.py test_critical

# Run all tests
python run_tests.py

# Run the 20-attempts stress test
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts

# Run with verbose output
python run_tests.py --verbose

# Stop on first failure (debugging)
python run_tests.py --failfast
```

#### Test Categories

| Test Class | Coverage |
|------------|----------|
| `QtakerCreationTests` | Quiz taker creation, validation |
| `QuizFlowTests` | Question retrieval, answer submission |
| `ScoringAndResultsTests` | Score calculation, pass/fail logic |
| `SkillProgressionTests` | Level progression (beginner → expert) |
| `MultipleAttemptsTests` | **Same user 20 times (critical)** |
| `EdgeCaseTests` | Error handling, edge cases |
| `PerformanceTests` | Query optimization |
| `IntegrationTests` | End-to-end workflows |

#### Critical Test: 20 Consecutive Attempts

This test ensures the same user can take the quiz 20 times without:
- State pollution between sessions
- Database corruption
- Score calculation errors
- Question randomization issues

```bash
python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts
```

**Expected output:**
```
✓ Successfully completed 20 consecutive attempts
  - Passed: 10
  - Failed: 10
```

### Useful Django Commands

```bash
# Shell with project context
python manage.py shell

# Check database
python manage.py dbshell

# Show SQL for migration
python manage.py sqlmigrate questionnaire 0001

# Check for issues
python manage.py check
```

### Common Debug Queries (Shell)

```python
from questionnaire.models import *

# Check qtaker state
qtaker = Qtaker.objects.get(id=1)
print(qtaker.current_question_set)
print(qtaker.current_score)

# List questions for a skill
q = Questionnaire.objects.get(title="beginner")
questions = Question.objects.filter(questionnaire=q)

# Check answer options
opts = Options.objects.filter(question_id=15)
for o in opts:
    print(o.id, o.correct, o.text[:50])
```

### Logging

Add to `settings.py` for debugging:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
```

### Test Files

- `questionnaire/tests.py` - 40+ comprehensive test cases
- `run_tests.py` - Custom test runner with helpful output
- `TESTING.md` - Complete testing documentation
- `pytest.ini` - pytest configuration (optional)

---

## Deployment Notes

### Railway Deployment

1. **Connect GitHub repo** to Railway
2. **Environment Variables**:
   - `DATABASE_URL`: Auto-provisioned PostgreSQL
   - `SECRET_KEY`: Generate strong key
   - `DEBUG`: Set to `False`
3. **Build Command**: (none - Python)
4. **Start Command**: `gunicorn backend.wsgi`

### Production Checklist

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` is strong and secret
- [ ] Database using PostgreSQL
- [ ] Allowed hosts configured
- [ ] CORS origins restricted
- [ ] Static files collected
- [ ] Media uploads persisted (volume mounted)

### Static Files

```bash
# Collect before deployment
python manage.py collectstatic
```

WhiteNoise serves static files in production.

### Media Files on Railway

```python
# settings.py handles this automatically
if os.path.exists('/app/media'):
    MEDIA_ROOT = '/app/media'  # Use volume
```

---

## Troubleshooting

### "No questionnaire found for skill level"

**Cause**: Questionnaire title doesn't match skill level exactly.

**Fix**: Check `Questionnaire.title` values match "beginner", "intermediate", or "expert".

### Questions not randomizing

**Cause**: `current_question_set` already exists.

**Fix**: Clear the field to force new randomization:
```python
qtaker.current_question_set = []
qtaker.save()
```

### CKEditor uploads failing

**Check**:
1. `MEDIA_URL` and `MEDIA_ROOT` configured
2. Volume mounted at `/app/media` (Railway)
3. Directory permissions correct

### Text answers marked wrong

**Cause**: Case sensitivity or whitespace mismatch.

**Fix**: Check stored correct answer in admin:
```python
# In shell
q = Question.objects.get(id=X)
opt = Options.objects.get(question=q, correct=True)
print(repr(opt.text))  # Check exact text
```

### Database connection errors on Railway

**Check**:
1. `DATABASE_URL` environment variable set
2. SSL required for PostgreSQL (handled by `dj_database_url`)
3. Database service is running

---

## Contributing Guidelines

### Code Style
- Follow PEP 8
- Use type hints where helpful
- Comment complex quiz logic

### Migrations
- Always include migrations with model changes
- Test migrations on fresh database

### API Changes
- Update `API_DOCUMENTATION.md`
- Maintain backward compatibility when possible
- Version endpoints if breaking changes needed

---

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [CKEditor Django](https://django-ckeditor.readthedocs.io/)
- [Railway Docs](https://docs.railway.app/)

---

## Contact

For questions about this codebase, refer to the existing `API_DOCUMENTATION.md` for endpoint details or this guide for implementation context.
