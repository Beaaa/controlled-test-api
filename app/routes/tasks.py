"""
Task CRUD routes — with intentional controlled inconsistencies
and OpenAPI documentation imperfections.

See INCONSISTENCIES.md for the full catalogue.
"""

import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.jwt import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskResponseMinimal, PriorityEnum,
)

LARGE_ID_THRESHOLD = 999_999

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── helpers ───────────────────────────────────────────────────────────

def _validate_task_id(task_id: int) -> None:
    """INCONSISTENCY: very large IDs return 400 instead of 404."""
    if task_id > LARGE_ID_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task ID: {task_id}",
        )


def _maybe_omit_description(task: Task) -> dict:
    """INCONSISTENCY: ~30% of the time, omit the 'description' field from
    the response when its value is None — simulating a backend that
    inconsistently serialises null fields."""
    data = TaskResponse.model_validate(task).model_dump(mode="json")
    if task.description is None and random.random() < 0.3:
        data.pop("description", None)
    return data


# ── LIST ──────────────────────────────────────────────────────────────

# OPENAPI IMPERFECTION: response_model is list[TaskResponse] (correct)
# but the 'sort' query param is undocumented — it works at runtime
# but does not appear in the generated spec.
@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List tasks",
    # IMPERFECTION: no description for this endpoint
)
def list_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completed status"),
    priority: Optional[PriorityEnum] = Query(None, description="Filter by priority"),
    sort: Optional[str] = Query(
        None,
        include_in_schema=False,  # IMPERFECTION: hidden undocumented param
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task).filter(Task.owner_id == current_user.id)
    if completed is not None:
        query = query.filter(Task.completed == completed)
    if priority is not None:
        query = query.filter(Task.priority == priority.value)

    # Undocumented sort support
    if sort == "oldest":
        query = query.order_by(Task.created_at.asc())
    else:
        query = query.order_by(Task.created_at.desc())

    return query.all()


# ── GET ───────────────────────────────────────────────────────────────

# OPENAPI IMPERFECTION: no response_model at all — Swagger shows
# "Successful Response" with no schema. The runtime returns TaskResponse
# fields (sometimes minus 'description'). Also: 400 and 404 error
# responses are not documented in the spec.
@router.get(
    "/{task_id}",
    summary="Get task by ID",
    description="Retrieve a single task. Returns 404 if not found.",
    # IMPERFECTION: mentions 404 in description but doesn't declare it
    # in responses. Also doesn't mention the 400 for large IDs.
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_task_id(task_id)

    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return JSONResponse(content=_maybe_omit_description(task))


# ── CREATE ────────────────────────────────────────────────────────────

# OPENAPI IMPERFECTION: response_model is TaskResponseMinimal — an
# intentionally incomplete schema that only documents id, title, completed.
# The runtime actually returns all TaskResponse fields (8 fields).
# Also: documented status code is 200 (default) which happens to match
# the inconsistency, but a correct API would say 201.
@router.post(
    "",
    response_model=TaskResponseMinimal,
    summary="Create task",
    description="Create a new task for the authenticated user.",
    responses={
        # IMPERFECTION: documents 200 as success (matching the bug)
        # but doesn't document 422 for validation errors
        200: {"description": "Task created successfully"},
    },
)
def create_task(
    request: Request,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(
        title=payload.title,
        description=payload.description,
        completed=payload.completed,
        priority=payload.priority.value,
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    data = TaskResponse.model_validate(task).model_dump(mode="json")
    return JSONResponse(content=data, status_code=status.HTTP_200_OK)


# ── UPDATE ────────────────────────────────────────────────────────────

# OPENAPI: this one is well-documented (contrast with the others)
@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update fields on an existing task. Only provided fields are changed.",
    responses={
        404: {"description": "Task not found"},
    },
)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_task_id(task_id)

    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "priority" in update_data and update_data["priority"] is not None:
        update_data["priority"] = update_data["priority"].value
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


# ── DELETE ────────────────────────────────────────────────────────────

# OPENAPI IMPERFECTION: documents only 204 as the response, but the
# runtime randomly returns 200 (with body) or 204 (no body).
# The 200 response body schema is not documented at all.
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    # IMPERFECTION: no description
    responses={
        204: {"description": "Task deleted"},
        # IMPERFECTION: does NOT document the 200 alternative
        # IMPERFECTION: does NOT document 404
    },
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_task_id(task_id)

    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    db.delete(task)
    db.commit()

    if random.random() < 0.5:
        return JSONResponse(
            content={"detail": "Task deleted", "task_id": task_id},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(content=None, status_code=status.HTTP_204_NO_CONTENT)


# ── LENIENT CREATE ────────────────────────────────────────────────────

# OPENAPI IMPERFECTION: request body is typed as 'dict' (shows as
# generic object {}), no response_model. The endpoint accepts anything
# but the spec gives no guidance on what fields are expected.
@router.post(
    "/lenient",
    tags=["tasks"],
    summary="Create task (lenient)",
    # IMPERFECTION: misleading description — says "flexible" but
    # doesn't explain what defaults are applied
    description="Flexible task creation endpoint.",
)
def create_task_lenient(
    body: dict = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = body.get("title") or "Untitled"
    description = body.get("description")
    completed = bool(body.get("completed", False))
    priority = body.get("priority", "medium")

    task = Task(
        title=str(title)[:200],
        description=description,
        completed=completed,
        priority=str(priority),
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    data = TaskResponse.model_validate(task).model_dump(mode="json")
    return JSONResponse(content=data, status_code=status.HTTP_200_OK)
