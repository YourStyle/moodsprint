# MoodSprint API Specification

Base URL: `/api/v1`

## Authentication

All endpoints require Telegram authentication via `Authorization` header:
```
Authorization: tma <initData>
```

### POST /auth/telegram
Authenticate user via Telegram WebApp initData.

**Request Body:**
```json
{
  "init_data": "query_id=...&user=...&auth_date=...&hash=..."
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "telegram_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "xp": 150,
      "level": 2,
      "streak_days": 3,
      "created_at": "2024-01-01T00:00:00Z"
    },
    "token": "jwt_token_here"
  }
}
```

---

## Tasks

### GET /tasks
Get all tasks for current user.

**Query Parameters:**
- `status` (optional): `pending` | `in_progress` | `completed`
- `limit` (optional): number, default 50
- `offset` (optional): number, default 0

**Response 200:**
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": 1,
        "title": "Build MoodSprint app",
        "description": "Create the full application",
        "priority": "high",
        "status": "in_progress",
        "subtasks_count": 5,
        "subtasks_completed": 2,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 10
  }
}
```

### POST /tasks
Create a new task.

**Request Body:**
```json
{
  "title": "Build MoodSprint app",
  "description": "Create the full application with all features",
  "priority": "high"
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "task": {
      "id": 1,
      "title": "Build MoodSprint app",
      "description": "Create the full application with all features",
      "priority": "high",
      "status": "pending",
      "subtasks_count": 0,
      "subtasks_completed": 0,
      "created_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

### GET /tasks/:id
Get single task with subtasks.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "task": {
      "id": 1,
      "title": "Build MoodSprint app",
      "description": "Create the full application",
      "priority": "high",
      "status": "in_progress",
      "created_at": "2024-01-01T00:00:00Z",
      "subtasks": [
        {
          "id": 1,
          "title": "Set up project structure",
          "order": 1,
          "estimated_minutes": 15,
          "status": "completed",
          "created_at": "2024-01-01T00:00:00Z"
        },
        {
          "id": 2,
          "title": "Create database models",
          "order": 2,
          "estimated_minutes": 20,
          "status": "pending",
          "created_at": "2024-01-01T00:00:00Z"
        }
      ]
    }
  }
}
```

### PUT /tasks/:id
Update task.

**Request Body:**
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "priority": "medium",
  "status": "completed"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "task": { ... }
  }
}
```

### DELETE /tasks/:id
Delete task and all subtasks.

**Response 200:**
```json
{
  "success": true,
  "message": "Task deleted"
}
```

### POST /tasks/:id/decompose
AI-powered task decomposition based on current mood.

**Request Body:**
```json
{
  "mood_id": 5
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "subtasks": [
      {
        "id": 1,
        "title": "Open IDE and create new folder",
        "order": 1,
        "estimated_minutes": 5,
        "status": "pending"
      },
      {
        "id": 2,
        "title": "Initialize npm project",
        "order": 2,
        "estimated_minutes": 5,
        "status": "pending"
      }
    ],
    "strategy": "micro",
    "message": "Task broken into small steps for low energy state"
  }
}
```

---

## Subtasks

### PUT /subtasks/:id
Update subtask.

**Request Body:**
```json
{
  "title": "Updated title",
  "status": "completed",
  "estimated_minutes": 10
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "subtask": { ... },
    "xp_earned": 10,
    "achievements_unlocked": []
  }
}
```

### POST /subtasks/reorder
Reorder subtasks within a task.

**Request Body:**
```json
{
  "task_id": 1,
  "subtask_ids": [3, 1, 2, 4]
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Subtasks reordered"
}
```

---

## Mood

### POST /mood
Log mood check.

**Request Body:**
```json
{
  "mood": 3,
  "energy": 4,
  "note": "Feeling okay after lunch"
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "mood_check": {
      "id": 1,
      "mood": 3,
      "energy": 4,
      "note": "Feeling okay after lunch",
      "created_at": "2024-01-01T12:00:00Z"
    },
    "xp_earned": 5
  }
}
```

### GET /mood/latest
Get latest mood check.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "mood_check": {
      "id": 1,
      "mood": 3,
      "energy": 4,
      "note": "Feeling okay after lunch",
      "created_at": "2024-01-01T12:00:00Z"
    }
  }
}
```

### GET /mood/history
Get mood history.

**Query Parameters:**
- `days` (optional): number, default 7

**Response 200:**
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "date": "2024-01-01",
        "checks": [
          {
            "id": 1,
            "mood": 3,
            "energy": 4,
            "created_at": "2024-01-01T12:00:00Z"
          }
        ],
        "average_mood": 3.5,
        "average_energy": 4.0
      }
    ]
  }
}
```

---

## Focus Sessions

### POST /focus/start
Start a focus session.

**Request Body:**
```json
{
  "subtask_id": 1,
  "planned_duration_minutes": 25
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "session": {
      "id": 1,
      "subtask_id": 1,
      "subtask_title": "Set up project structure",
      "planned_duration_minutes": 25,
      "started_at": "2024-01-01T12:00:00Z",
      "status": "active"
    }
  }
}
```

### GET /focus/active
Get active focus session.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "session": {
      "id": 1,
      "subtask_id": 1,
      "subtask_title": "Set up project structure",
      "planned_duration_minutes": 25,
      "started_at": "2024-01-01T12:00:00Z",
      "elapsed_minutes": 12,
      "status": "active"
    }
  }
}
```

**Response 200 (no active session):**
```json
{
  "success": true,
  "data": {
    "session": null
  }
}
```

### POST /focus/complete
Complete focus session.

**Request Body:**
```json
{
  "session_id": 1,
  "complete_subtask": true
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "session": {
      "id": 1,
      "subtask_id": 1,
      "planned_duration_minutes": 25,
      "actual_duration_minutes": 23,
      "started_at": "2024-01-01T12:00:00Z",
      "ended_at": "2024-01-01T12:23:00Z",
      "status": "completed"
    },
    "xp_earned": 35,
    "achievements_unlocked": [
      {
        "code": "first_focus",
        "title": "First Focus",
        "description": "Complete your first focus session"
      }
    ]
  }
}
```

### POST /focus/cancel
Cancel focus session.

**Request Body:**
```json
{
  "session_id": 1,
  "reason": "interrupted"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "session": {
      "id": 1,
      "status": "cancelled"
    }
  }
}
```

### GET /focus/history
Get focus session history.

**Query Parameters:**
- `limit` (optional): number, default 20
- `offset` (optional): number, default 0

**Response 200:**
```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": 1,
        "subtask_title": "Set up project structure",
        "task_title": "Build MoodSprint app",
        "actual_duration_minutes": 23,
        "status": "completed",
        "started_at": "2024-01-01T12:00:00Z"
      }
    ],
    "total": 15,
    "total_minutes": 345
  }
}
```

---

## Gamification

### GET /user/stats
Get user stats and progress.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "xp": 1250,
    "level": 4,
    "xp_for_next_level": 1600,
    "xp_progress_percent": 78,
    "streak_days": 5,
    "longest_streak": 12,
    "total_tasks_completed": 23,
    "total_focus_minutes": 845,
    "total_subtasks_completed": 156,
    "today": {
      "tasks_completed": 2,
      "subtasks_completed": 8,
      "focus_minutes": 120,
      "mood_checks": 2
    }
  }
}
```

### GET /achievements
Get all available achievements.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "achievements": [
      {
        "id": 1,
        "code": "first_task",
        "title": "First Step",
        "description": "Complete your first task",
        "xp_reward": 50,
        "icon": "trophy",
        "category": "tasks"
      },
      {
        "id": 2,
        "code": "focus_master",
        "title": "Focus Master",
        "description": "Complete 10 focus sessions",
        "xp_reward": 100,
        "icon": "target",
        "category": "focus",
        "progress_max": 10
      }
    ]
  }
}
```

### GET /user/achievements
Get user's unlocked achievements.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "unlocked": [
      {
        "id": 1,
        "code": "first_task",
        "title": "First Step",
        "description": "Complete your first task",
        "xp_reward": 50,
        "icon": "trophy",
        "unlocked_at": "2024-01-01T12:00:00Z"
      }
    ],
    "in_progress": [
      {
        "id": 2,
        "code": "focus_master",
        "title": "Focus Master",
        "description": "Complete 10 focus sessions",
        "xp_reward": 100,
        "icon": "target",
        "progress": 3,
        "progress_max": 10
      }
    ]
  }
}
```

### GET /user/daily-goals
Get daily goals progress.

**Response 200:**
```json
{
  "success": true,
  "data": {
    "goals": [
      {
        "type": "focus_minutes",
        "title": "Focus Time",
        "target": 60,
        "current": 45,
        "completed": false
      },
      {
        "type": "subtasks",
        "title": "Complete Subtasks",
        "target": 5,
        "current": 5,
        "completed": true
      },
      {
        "type": "mood_check",
        "title": "Log Mood",
        "target": 1,
        "current": 1,
        "completed": true
      }
    ],
    "all_completed": false,
    "bonus_xp_available": 30
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "title": "Title is required"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing auth |
| `FORBIDDEN` | 403 | Access denied |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid input |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal error |
