"""
Seed script — populates the database with realistic, edge-case, and
intentionally malformed data for the AI Test Engine to probe.

Usage:
    python seed.py          # wipes + seeds
    python seed.py --append # keeps existing data, adds more
"""

import sys
import random
from datetime import datetime, timezone, timedelta

from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.task import Task
from app.models.comment import Comment
from app.auth.passwords import hash_password


# ── Configuration ─────────────────────────────────────────────────────

SEED_USERS = [
    # Normal users
    {"username": "alice",    "email": "alice@example.com",    "password": "password123"},
    {"username": "bob",      "email": "bob@company.org",      "password": "bobsecure!"},
    {"username": "charlie",  "email": "charlie@test.io",      "password": "charlie99"},
    {"username": "diana",    "email": "diana@enterprise.com", "password": "d1@naPass"},
    {"username": "eve",      "email": "eve@security.net",     "password": "ev3Sec!"},
    # Edge-case usernames
    {"username": "a",        "email": "a@edge.com",           "password": "shortname"},
    {"username": "x" * 50,   "email": "max_length@edge.com",  "password": "maxuser!"},
    {"username": "user-with-dashes", "email": "dashes@edge.com", "password": "dashes123"},
    {"username": "user.dots", "email": "dots@edge.com",       "password": "dots1234"},
    {"username": "UPPERCASE", "email": "upper@edge.com",      "password": "upper123"},
]

VALID_PRIORITIES = ["low", "medium", "high", "critical"]

NORMAL_TASKS = [
    {"title": "Set up CI/CD pipeline",               "description": "Configure GitHub Actions for automated testing and deployment.", "priority": "high"},
    {"title": "Write unit tests for auth module",     "description": "Cover registration, login, and token refresh flows.",           "priority": "critical"},
    {"title": "Design database schema v2",            "description": "Add support for tags and attachments.",                         "priority": "medium"},
    {"title": "Fix pagination bug",                   "description": "Offset-based pagination returns duplicates on concurrent inserts.", "priority": "high"},
    {"title": "Update README",                        "description": "Document new API endpoints and authentication flow.",           "priority": "low"},
    {"title": "Refactor error handling",              "description": None,                                                           "priority": "medium"},
    {"title": "Add rate-limit headers to responses",  "description": "Include X-RateLimit-Remaining and X-RateLimit-Reset.",          "priority": "medium"},
    {"title": "Investigate memory leak in worker",    "description": "OOM kills observed after 48h uptime.",                          "priority": "critical"},
    {"title": "Implement soft-delete for tasks",      "description": "Tasks should be marked deleted, not removed.",                  "priority": "medium"},
    {"title": "Add search endpoint",                  "description": "Full-text search across task titles and descriptions.",         "priority": "low"},
    {"title": "Create onboarding guide",              "description": None,                                                           "priority": "low"},
    {"title": "Migrate to async SQLAlchemy",          "description": "Benchmark sync vs async for typical query patterns.",           "priority": "medium"},
    {"title": "Review third-party dependencies",      "description": "Audit for known CVEs.",                                        "priority": "high"},
    {"title": "Optimize N+1 queries on comments",     "description": "Use joinedload for the task->comments relationship.",           "priority": "high"},
    {"title": "Add Prometheus metrics exporter",      "description": "Expose /metrics in OpenMetrics format.",                        "priority": "medium"},
]

EDGE_CASE_TASKS = [
    # Empty / whitespace-heavy
    {"title": "   ",                                   "description": "",                "priority": "low"},
    {"title": "T",                                     "description": None,              "priority": "medium"},
    {"title": "A" * 200,                               "description": "Max-length title test.", "priority": "high"},
    # Unicode
    {"title": "Tarefa com acentos: cafe, naif",        "description": "Descricao em portugues.", "priority": "medium"},
    {"title": "Task with emoji in body",               "description": "Details: check logs for output.",  "priority": "low"},
    {"title": "Japanese: API test",                    "description": "Internationalization edge case.",   "priority": "high"},
    # Malformed / intentionally bad priority (simulates lenient endpoint writes)
    {"title": "Task with invalid priority",            "description": "Stored via lenient endpoint.",      "priority": "super_urgent"},
    {"title": "Task with numeric priority",            "description": "Priority should be a string enum.", "priority": "999"},
    {"title": "Task with empty priority",              "description": "Missing priority value.",            "priority": ""},
    # Special characters
    {"title": "Task with 'quotes' and \"doubles\"",    "description": "O'Reilly style.",                   "priority": "medium"},
    {"title": "Path traversal: ../../etc/passwd",      "description": "Should be treated as plain text.",  "priority": "low"},
    {"title": "<script>alert('xss')</script>",         "description": "<b>bold</b> injection attempt.",    "priority": "medium"},
    # Very long description
    {"title": "Task with huge description",            "description": "x" * 5000,                          "priority": "low"},
    # Null-heavy
    {"title": "Minimal task",                          "description": None,                                 "priority": "medium"},
    {"title": "Another minimal task",                  "description": None,                                 "priority": "medium"},
]

COMMENT_TEMPLATES = [
    "Looking into this now.",
    "Blocked by upstream dependency.",
    "Fixed in commit abc123.",
    "Needs code review before merge.",
    "Can we prioritize this for next sprint?",
    "Duplicate of task #{n}.",
    "Closing — no longer relevant.",
    "Reopening: regression found in v2.1.",
    "",                          # intentionally empty (malformed)
    "   ",                       # whitespace-only (malformed)
    "Comment with 'single' and \"double\" quotes.",
    "<script>alert('xss')</script>",
    "x" * 3000,                  # very long comment
    "Short.",
    None,                        # will be stored as empty string (malformed)
]


# ── Helpers ───────────────────────────────────────────────────────────

def _random_past_datetime(days_back: int = 90) -> datetime:
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return datetime.now(timezone.utc) - delta


def _seed_users(db) -> list[User]:
    users = []
    created = 0
    skipped = 0
    for u in SEED_USERS:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if existing:
            users.append(existing)
            skipped += 1
            continue
        user = User(
            username=u["username"],
            email=u["email"],
            password_hash=hash_password(u["password"]),
            created_at=_random_past_datetime(180),
            updated_at=_random_past_datetime(30),
        )
        db.add(user)
        users.append(user)
        created += 1
    db.flush()
    print(f"  [+] {created} users created, {skipped} skipped (already exist)")
    return users


def _seed_tasks(db, users: list[User]) -> list[Task]:
    tasks = []

    # Normal tasks — distributed among first 5 users
    for t in NORMAL_TASKS:
        owner = random.choice(users[:5])
        task = Task(
            title=t["title"],
            description=t["description"],
            completed=random.choice([True, False]),
            priority=t["priority"],
            owner_id=owner.id,
            created_at=_random_past_datetime(60),
            updated_at=_random_past_datetime(14),
        )
        db.add(task)
        tasks.append(task)

    # Edge-case tasks — assigned to edge-case users or random
    for t in EDGE_CASE_TASKS:
        owner = random.choice(users)
        task = Task(
            title=t["title"],
            description=t["description"],
            completed=random.choice([True, False, False]),
            priority=t["priority"],
            owner_id=owner.id,
            created_at=_random_past_datetime(90),
            updated_at=_random_past_datetime(7),
        )
        db.add(task)
        tasks.append(task)

    db.flush()
    print(f"  [+] {len(tasks)} tasks created ({len(NORMAL_TASKS)} normal, {len(EDGE_CASE_TASKS)} edge-case)")
    return tasks


def _seed_comments(db, users: list[User], tasks: list[Task]) -> int:
    count = 0
    # Add 1–4 comments to ~60 % of tasks
    for task in tasks:
        if random.random() > 0.6:
            continue
        n_comments = random.randint(1, 4)
        for _ in range(n_comments):
            template = random.choice(COMMENT_TEMPLATES)
            content = (template or "").replace("{n}", str(random.randint(1, len(tasks))))
            comment = Comment(
                content=content,
                task_id=task.id,
                author_id=random.choice(users).id,
                created_at=_random_past_datetime(30),
                updated_at=_random_past_datetime(7),
            )
            db.add(comment)
            count += 1
    db.flush()
    print(f"  [+] {count} comments created")
    return count


# ── Main ──────────────────────────────────────────────────────────────

def seed(append: bool = False):
    if not append:
        print("[*] Dropping all tables …")
        Base.metadata.drop_all(bind=engine)
        print("[*] Recreating tables …")
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[*] Seeding data …")
        users = _seed_users(db)
        tasks = _seed_tasks(db, users)
        _seed_comments(db, users, tasks)
        db.commit()
        print("[*] Seed complete.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    append = "--append" in sys.argv
    seed(append=append)
