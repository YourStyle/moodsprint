"""Tasks API endpoints."""
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.api import api_bp
from app.models import Task, Subtask, MoodCheck, User
from app.models.task import TaskStatus, TaskPriority
from app.models.subtask import SubtaskStatus
from app.services import AIDecomposer, XPCalculator, AchievementChecker
from app.utils import success_response, validation_error, not_found


@api_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """
    Get all tasks for current user.

    Query params:
    - status: filter by status (pending, in_progress, completed)
    - limit: max results (default 50)
    - offset: pagination offset (default 0)
    """
    user_id = get_jwt_identity()

    # Build query
    query = Task.query.filter_by(user_id=user_id)

    # Filter by status
    status = request.args.get('status')
    if status and status in [s.value for s in TaskStatus]:
        query = query.filter_by(status=status)

    # Order by created_at desc
    query = query.order_by(Task.created_at.desc())

    # Get total count before pagination
    total = query.count()

    # Pagination
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    tasks = query.offset(offset).limit(limit).all()

    return success_response({
        'tasks': [t.to_dict() for t in tasks],
        'total': total
    })


@api_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    """
    Create a new task.

    Request body:
    {
        "title": "Task title",
        "description": "Optional description",
        "priority": "low|medium|high"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return validation_error({'body': 'Request body is required'})

    title = data.get('title', '').strip()
    if not title:
        return validation_error({'title': 'Title is required'})

    if len(title) > 500:
        return validation_error({'title': 'Title must be less than 500 characters'})

    priority = data.get('priority', TaskPriority.MEDIUM.value)
    if priority not in [p.value for p in TaskPriority]:
        priority = TaskPriority.MEDIUM.value

    task = Task(
        user_id=user_id,
        title=title,
        description=data.get('description'),
        priority=priority
    )

    db.session.add(task)
    db.session.commit()

    return success_response({'task': task.to_dict()}, status_code=201)


@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id: int):
    """Get a single task with subtasks."""
    user_id = get_jwt_identity()

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found('Task not found')

    return success_response({'task': task.to_dict(include_subtasks=True)})


@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id: int):
    """
    Update a task.

    Request body (all optional):
    {
        "title": "New title",
        "description": "New description",
        "priority": "low|medium|high",
        "status": "pending|in_progress|completed"
    }
    """
    user_id = get_jwt_identity()

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found('Task not found')

    data = request.get_json() or {}

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            return validation_error({'title': 'Title cannot be empty'})
        if len(title) > 500:
            return validation_error({'title': 'Title must be less than 500 characters'})
        task.title = title

    if 'description' in data:
        task.description = data['description']

    if 'priority' in data:
        if data['priority'] in [p.value for p in TaskPriority]:
            task.priority = data['priority']

    if 'status' in data:
        if data['status'] in [s.value for s in TaskStatus]:
            task.status = data['status']

    db.session.commit()

    # Check achievements if task completed
    xp_info = None
    achievements_unlocked = []
    if task.status == TaskStatus.COMPLETED.value:
        user = User.query.get(user_id)
        xp_info = user.add_xp(XPCalculator.task_completed())
        user.update_streak()

        checker = AchievementChecker(user)
        achievements_unlocked = checker.check_all()

        db.session.commit()

    response_data = {'task': task.to_dict()}
    if xp_info:
        response_data['xp_earned'] = xp_info['xp_earned']
        response_data['achievements_unlocked'] = [a.to_dict() for a in achievements_unlocked]

    return success_response(response_data)


@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id: int):
    """Delete a task and all its subtasks."""
    user_id = get_jwt_identity()

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found('Task not found')

    db.session.delete(task)
    db.session.commit()

    return success_response(message='Task deleted')


@api_bp.route('/tasks/<int:task_id>/decompose', methods=['POST'])
@jwt_required()
def decompose_task(task_id: int):
    """
    AI-decompose a task into subtasks based on mood.

    Request body:
    {
        "mood_id": 5  // optional, uses latest mood if not provided
    }
    """
    user_id = get_jwt_identity()

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found('Task not found')

    data = request.get_json() or {}

    # Get mood check
    mood_id = data.get('mood_id')
    if mood_id:
        mood_check = MoodCheck.query.filter_by(id=mood_id, user_id=user_id).first()
    else:
        mood_check = MoodCheck.query.filter_by(user_id=user_id)\
            .order_by(MoodCheck.created_at.desc()).first()

    if not mood_check:
        # Use default strategy if no mood
        strategy = 'standard'
    else:
        strategy = mood_check.decomposition_strategy

    # Clear existing subtasks
    Subtask.query.filter_by(task_id=task.id).delete()

    # Decompose task
    decomposer = AIDecomposer()
    subtask_data = decomposer.decompose_task(
        task.title,
        task.description,
        strategy
    )

    # Create subtasks
    subtasks = []
    for data in subtask_data:
        subtask = Subtask(
            task_id=task.id,
            title=data['title'],
            estimated_minutes=data['estimated_minutes'],
            order=data['order']
        )
        db.session.add(subtask)
        subtasks.append(subtask)

    db.session.commit()

    return success_response({
        'subtasks': [s.to_dict() for s in subtasks],
        'strategy': strategy,
        'message': decomposer.get_strategy_message(strategy)
    })


# Subtask endpoints

@api_bp.route('/subtasks/<int:subtask_id>', methods=['PUT'])
@jwt_required()
def update_subtask(subtask_id: int):
    """
    Update a subtask.

    Request body (all optional):
    {
        "title": "New title",
        "status": "pending|in_progress|completed|skipped",
        "estimated_minutes": 15
    }
    """
    user_id = get_jwt_identity()

    subtask = Subtask.query.join(Task).filter(
        Subtask.id == subtask_id,
        Task.user_id == user_id
    ).first()

    if not subtask:
        return not_found('Subtask not found')

    data = request.get_json() or {}
    old_status = subtask.status

    if 'title' in data:
        title = data['title'].strip()
        if title:
            subtask.title = title[:500]

    if 'estimated_minutes' in data:
        try:
            minutes = int(data['estimated_minutes'])
            subtask.estimated_minutes = max(1, min(120, minutes))
        except (ValueError, TypeError):
            pass

    if 'status' in data:
        if data['status'] in [s.value for s in SubtaskStatus]:
            subtask.status = data['status']
            if data['status'] == SubtaskStatus.COMPLETED.value:
                subtask.complete()

    # Update parent task status
    subtask.task.update_status_from_subtasks()

    db.session.commit()

    # Calculate XP if completed
    xp_info = None
    achievements_unlocked = []

    was_completed = (
        old_status != SubtaskStatus.COMPLETED.value
        and subtask.status == SubtaskStatus.COMPLETED.value
    )

    if was_completed:
        user = User.query.get(user_id)
        xp_earned = XPCalculator.subtask_completed()

        # Bonus XP if all subtasks completed (task completed)
        if subtask.task.status == TaskStatus.COMPLETED.value:
            xp_earned += XPCalculator.task_completed()

        xp_info = user.add_xp(xp_earned)
        user.update_streak()

        checker = AchievementChecker(user)
        achievements_unlocked = checker.check_all()

        db.session.commit()

    response_data = {'subtask': subtask.to_dict()}
    if xp_info:
        response_data['xp_earned'] = xp_info['xp_earned']
        response_data['achievements_unlocked'] = [a.to_dict() for a in achievements_unlocked]

    return success_response(response_data)


@api_bp.route('/subtasks/reorder', methods=['POST'])
@jwt_required()
def reorder_subtasks():
    """
    Reorder subtasks within a task.

    Request body:
    {
        "task_id": 1,
        "subtask_ids": [3, 1, 2, 4]
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'task_id' not in data or 'subtask_ids' not in data:
        return validation_error({'body': 'task_id and subtask_ids are required'})

    task = Task.query.filter_by(id=data['task_id'], user_id=user_id).first()
    if not task:
        return not_found('Task not found')

    subtask_ids = data['subtask_ids']

    # Update order for each subtask
    for order, subtask_id in enumerate(subtask_ids, 1):
        subtask = Subtask.query.filter_by(id=subtask_id, task_id=task.id).first()
        if subtask:
            subtask.order = order

    db.session.commit()

    return success_response(message='Subtasks reordered')
