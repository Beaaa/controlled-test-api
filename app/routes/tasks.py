"""
Task CRUD routes — with intentional controlled inconsistencies.

See INCONSISTENCIES.md for the full catalogue of deliberate behaviors.
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
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, PriorityEnum

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

@router.get("", response_model=list[TaskResponse])
def list_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completed status"),
    priority: Optional[PriorityEnum] = Query(None, description="Filter by priority"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task).filter(Task.owner_id == current_user.id)
    if completed is not None:
        query = query.filter(Task.completed == completed)
    if priority is not None:
        query = query.filter(Task.priority == priority.value)
    return query.order_by(Task.created_at.desc()).all()


# ── GET ───────────────────────────────────────────────────────────────

@router.get("/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # INCONSISTENCY: large IDs → 400 instead of 404
    _validate_task_id(task_id)

    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # INCONSISTENCY: sometimes omits description when null
    return JSONResponse(content=_maybe_omit_description(task))


# ── CREATE ────────────────────────────────────────────────────────────

@router.post("")
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

    # INCONSISTENCY: returns 200 instead of the expected 201
    return JSONResponse(content=data, status_code=status.HTTP_200_OK)


# ── UPDATE ────────────────────────────────────────────────────────────

@router.put("/{task_id}", response_model=TaskResponse)
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

@router.delete("/{task_id}")
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

    # INCONSISTENCY: randomly returns 200 or 204
    if random.random() < 0.5:
        return JSONResponse(
            content={"detail": "Task deleted", "task_id": task_id},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(content=None, status_code=status.HTTP_204_NO_CONTENT)


# ── LENIENT CREATE (undocumented) ─────────────────────────────────────

@router.post("/lenient", tags=["tasks"])
def create_task_lenient(
    body: dict = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """INCONSISTENCY: accepts malformed payloads — skips Pydantic validation.
    Missing 'title' defaults to 'Untitled'. Unknown priority values are
    silently stored as-is. Extra fields are ignored without error."""
    title = body.get("title") or "Untitled"
    description = body.get("description")
    completed = bool(body.get("completed", False))
    priority = body.get("priority", "medium")  # accepts ANY string

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
