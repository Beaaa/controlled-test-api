from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.jwt import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


# OPENAPI IMPERFECTION: well-documented response_model, but the
# task_id path parameter has no description. Also: 404 error
# response is not declared in the spec.
@router.get(
    "",
    response_model=list[CommentResponse],
    summary="List comments for a task",
    # IMPERFECTION: no endpoint description
)
def list_comments(
    task_id: int,  # IMPERFECTION: no Path(..., description=...)
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_task_or_404(task_id, db)
    return (
        db.query(Comment)
        .filter(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
        .all()
    )


# OPENAPI: this one is well-documented (contrast with list_comments)
@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to task",
    description="Create a new comment on the specified task. "
                "The authenticated user becomes the author.",
    responses={
        201: {"description": "Comment created"},
        404: {"description": "Task not found"},
    },
)
def create_comment(
    task_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_task_or_404(task_id, db)
    comment = Comment(
        content=payload.content,
        task_id=task_id,
        author_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
