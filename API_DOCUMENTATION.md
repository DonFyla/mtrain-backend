# Chess Academy Questionnaire API

A Django REST API for a chess learning platform that delivers skill-based quizzes with multiple question types and automatic level progression.

## Features

- Multi-level assessment system (Beginner → Intermediate → Expert)
- Two question types: Multiple choice (radio) and text-based answers
- 5 randomized questions per quiz session
- Automatic skill progression when scoring > 60%
- Rich text questions using CKEditor
- RESTful API with JSON responses
- SQLite (development) / PostgreSQL (production) support

## Tech Stack

- **Framework:** Django 5.2
- **API:** Django REST Framework
- **Database:** SQLite (dev), PostgreSQL (prod via DATABASE_URL)
- **Rich Text:** CKEditor + CKEditor Uploader
- **CORS:** django-cors-headers
- **Static Files:** WhiteNoise

## Installation

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser for admin panel
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string ( Railway) | No (falls back to SQLite) |
| `SECRET_KEY` | Django secret key | No (dev key used) |
| `DEBUG` | Debug mode | No |

## API Endpoints

### 1. Create Quiz Taker / Start Quiz

**Endpoint:** `POST /api/qtaker/`

Creates a new quiz taker and returns the first question.

**Request Body:**
```json
{
    "name": "John Doe",
    "age": 25,
    "email": "john@example.com",
    "skill": "beginner"
}
```

**Response (201 Created):**
```json
{
    "qtaker_id": 1,
    "message": "User created successfully",
    "skill": "beginner",
    "total_questions_in_session": 5,
    "question_id": 15
}
```

**Error Response (404):**
```json
{
    "error": "No questionnaire found for skill level: beginner"
}
```

---

### 2. Get Quiz Question

**Endpoint:** `GET /api/quiz/<qtaker_id>/<question_id>/`

Retrieves a question with its options (for radio questions).

**Response (200 OK):**
```json
{
    "qtaker": {
        "id": 1,
        "name": "John Doe",
        "skill": "beginner",
        "age": 25,
        "current_score": 2,
        "last_answer_id": 45
    },
    "question": {
        "id": 15,
        "text": "<p>What is the value of a knight?</p>",
        "placement": 1,
        "question_type": "radio",
        "options": [
            {"id": 44, "text": "1 point", "correct": false},
            {"id": 45, "text": "3 points", "correct": true},
            {"id": 46, "text": "5 points", "correct": false}
        ]
    },
    "questionnaire": {
        "id": 1,
        "title": "beginner"
    },
    "next_question": {"id": 22}
}
```

---

### 3. Submit Answer

**Endpoint:** `POST /api/quiz/<qtaker_id>/<question_id>/`

Submits an answer and gets immediate feedback.

**Request Body (Radio):**
```json
{
    "answer": "45"
}
```

**Request Body (Text):**
```json
{
    "answer": "The knight moves in an L-shape"
}
```

**Response (200 OK):**
```json
{
    "is_correct": true,
    "message": "Answer recorded",
    "next_question_id": 22,
    "current_score": 3,
    "last_answer_id": 45,
    "chosen_answer": {
        "id": 45,
        "text": "3 points",
        "correct": true
    },
    "correct_answer": {
        "id": 45,
        "text": "3 points",
        "correct": true
    }
}
```

---

### 4. View Answer Details

**Endpoint:** `GET /api/answer/<qtaker_id>/<answer_id>/`

Retrieves detailed answer information including correct answer.

**Response (200 OK):**
```json
{
    "qtaker": {
        "id": 1,
        "name": "John Doe",
        "skill": "beginner"
    },
    "answer": {
        "id": 45,
        "text": "3 points",
        "correct": true
    },
    "correct_answer": {
        "id": 45,
        "text": "3 points"
    },
    "question": {
        "id": 15,
        "text": "<p>What is the value of a knight?</p>"
    },
    "next_question": {
        "id": 22,
        "text": "<p>How does a bishop move?</p>"
    },
    "score": 3,
    "is_correct": true
}
```

---

### 5. Get Final Result

**Endpoint:** `GET /api/result/<qtaker_id>/`

Returns final score, pass/fail status, and next level information.

**Response - Passed (200 OK):**
```json
{
    "current_skill": "beginner",
    "current_questionnaire": {
        "id": 1,
        "title": "beginner"
    },
    "qtaker": {
        "id": 1,
        "name": "John Doe",
        "age": 25,
        "email": "john@example.com",
        "skill": "intermediate",
        "current_score": 0,
        "test_result": 80.0
    },
    "score": 4,
    "total_questions": 5,
    "percentage": 80.0,
    "passed": true,
    "next_skill": "intermediate",
    "next_questionnaire": {
        "id": 2,
        "title": "intermediate",
        "first_question_id": 30
    }
}
```

**Response - Failed (200 OK):**
```json
{
    "current_skill": "beginner",
    "current_questionnaire": {
        "id": 1,
        "title": "beginner"
    },
    "qtaker": { ... },
    "score": 2,
    "total_questions": 5,
    "percentage": 40.0,
    "passed": false,
    "next_skill": null,
    "next_questionnaire": null
}
```

---

## Data Models

### Questionnaire
| Field | Type | Description |
|-------|------|-------------|
| title | CharField | Unique title (matches skill names: beginner, intermediate, expert) |
| description | TextField | Questionnaire description |
| created_at | DateTimeField | Auto-added creation timestamp |
| created_by | ForeignKey | Admin user who created it |

### Question
| Field | Type | Description |
|-------|------|-------------|
| questionnaire | ForeignKey | Parent questionnaire |
| question_type | CharField | "radio" or "text" |
| question | RichTextUploadingField | Question content (HTML via CKEditor) |
| placement | PositiveIntegerField | Order of question |
| created_by | ForeignKey | Admin user who created it |

### Options
| Field | Type | Description |
|-------|------|-------------|
| question | ForeignKey | Parent question |
| text | TextField | Option text (supports WYSIWYG) |
| correct | BooleanField | Whether this is the correct answer |

### Qtaker
| Field | Type | Description |
|-------|------|-------------|
| name | CharField | Taker's name |
| age | IntegerField | Taker's age |
| email | EmailField | Optional email |
| skill | CharField | Current skill level (beginner/intermediate/expert) |
| current_score | IntegerField | Score in current session |
| test_result | FloatField | Final percentage score |
| current_question_set | JSONField | List of question IDs for current session |
| next_question_set | JSONField | Question IDs for next level (when promoted) |

## Admin Panel

Access at `/admin/` after creating a superuser.

### Setup Questionnaires

1. Create a Questionnaire with title: `beginner`
2. Add Questions with placement order (1, 2, 3...)
3. For radio questions, add Options with one marked as correct
4. Repeat for `intermediate` and `expert` questionnaires

## Deployment (Railway)

1. Connect GitHub repository to Railway
2. Set environment variables:
   - `DATABASE_URL` (auto-provisioned PostgreSQL)
   - `SECRET_KEY` (generate a strong key)
3. Deploy command: `python manage.py migrate`
4. Build command: Not needed (Python)
5. Start command: `gunicorn backend.wsgi`

### Railway Configuration

```toml
# Procfile (create in root)
web: gunicorn backend.wsgi --bind 0.0.0.0:$PORT
```

```python
# settings.py handles DATABASE_URL automatically
# See settings.py lines 320-338
```

## CORS Configuration

Allowed origins:
- `http://localhost:3000` (development frontend)
- `https://themovingtrain.org` (production frontend)

## License

MIT License
