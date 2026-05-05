from __future__ import annotations

from sqlalchemy.orm import Session
from models.todo import Todo, TodoStatus, RecurrenceType
from services.audit_mixin import AuditMixin
from typing import List, Optional
from datetime import datetime, timedelta
from core.logger import get_logger
from core.utils import get_local_now, escape_like_wildcards

logger = get_logger(__name__)


class TodoService(AuditMixin):
    def __init__(self, db: Session):
        self.db = db

    def create_todo(self, title: str, description: str = None, priority: int = 5,
                    assigned_to: int = None, due_date: datetime = None,
                    created_by: int = None, status: str = None,
                    recurrence_type: str = None, recurrence_interval: int = 1) -> Todo:
        todo = Todo(
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            due_date=due_date,
            status=status if status else TodoStatus.PENDING,
            recurrence_type=recurrence_type if recurrence_type else RecurrenceType.NONE,
            recurrence_interval=recurrence_interval,
            created_at=get_local_now()
        )
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        logger.info(f"创建待办事项: {title}")

        self.log_create(
            user_id=created_by,
            resource_type="todo",
            resource_id=todo.id,
            resource_name=title,
            details=f"创建待办: {title}"
        )

        return todo

    def get_todos(self, status: str = None, skip: int = 0, limit: int = 100) -> List[Todo]:
        query = self.db.query(Todo)
        if status:
            query = query.filter(Todo.status == status)
        return query.order_by(Todo.created_at.desc()).offset(skip).limit(limit).all()

    def get_todo(self, todo_id: int) -> Optional[Todo]:
        return self.db.query(Todo).filter(Todo.id == todo_id).first()

    def get_todos_by_user(self, user_id: int, status: str = None) -> List[Todo]:
        query = self.db.query(Todo).filter(Todo.assigned_to == user_id)
        if status:
            query = query.filter(Todo.status == status)
        return query.order_by(Todo.created_at.desc()).all()

    def update_todo(self, todo_id: int, user_id: Optional[int] = None, **kwargs) -> Optional[Todo]:
        todo = self.get_todo(todo_id)
        if not todo:
            return None

        if 'status' in kwargs and kwargs['status'] == TodoStatus.COMPLETED:
            if todo.status != TodoStatus.COMPLETED:
                kwargs['completed_at'] = get_local_now()

        for key, value in kwargs.items():
            if value is not None and hasattr(todo, key):
                setattr(todo, key, value)

        self.db.commit()
        self.db.refresh(todo)
        logger.info(f"更新待办事项: {todo.title}")

        self.log_update(
            user_id=user_id,
            resource_type="todo",
            resource_id=todo_id,
            resource_name=todo.title,
            details=f"更新待办: {todo.title}"
        )

        return todo

    def delete_todo(self, todo_id: int, user_id: Optional[int] = None) -> bool:
        todo = self.get_todo(todo_id)
        if todo:
            self.log_delete(
                user_id=user_id,
                resource_type="todo",
                resource_id=todo_id,
                resource_name=todo.title,
                details=f"删除待办: {todo.title}"
            )
            self.db.delete(todo)
            self.db.commit()
            logger.info(f"删除待办事项: {todo.title}")
            return True
        return False

    def complete_todo(self, todo_id: int, user_id: Optional[int] = None) -> Optional[Todo]:
        todo = self.get_todo(todo_id)
        if not todo:
            return None
        
        todo.status = TodoStatus.COMPLETED
        todo.completed_at = get_local_now()
        self.db.commit()
        self.db.refresh(todo)
        logger.info(f"完成待办事项: {todo.title}")

        self.log_audit(
            user_id=user_id,
            action_type="update",
            resource_type="todo",
            resource_id=todo_id,
            details=f"完成待办: {todo.title}"
        )
        
        if todo.recurrence_type and todo.recurrence_type != RecurrenceType.NONE:
            self._create_next_recurrence(todo)
        
        return todo

    def _create_next_recurrence(self, todo: Todo) -> Optional[Todo]:
        next_due_date = self._calculate_next_due_date(
            todo.due_date, 
            todo.recurrence_type, 
            todo.recurrence_interval
        )
        
        new_todo = Todo(
            title=todo.title,
            description=todo.description,
            priority=todo.priority,
            assigned_to=todo.assigned_to,
            due_date=next_due_date,
            status=TodoStatus.PENDING,
            recurrence_type=todo.recurrence_type,
            recurrence_interval=todo.recurrence_interval,
            created_at=get_local_now()
        )
        self.db.add(new_todo)
        self.db.commit()
        self.db.refresh(new_todo)
        logger.info(f"创建循环待办事项: {new_todo.title}, 下次截止日期: {next_due_date}")
        return new_todo

    def _calculate_next_due_date(self, current_due_date: datetime, 
                                  recurrence_type: str, interval: int) -> datetime:
        if not current_due_date:
            current_due_date = get_local_now()
        
        if recurrence_type == RecurrenceType.DAILY:
            return current_due_date + timedelta(days=interval)
        elif recurrence_type == RecurrenceType.WEEKLY:
            return current_due_date + timedelta(weeks=interval)
        elif recurrence_type == RecurrenceType.MONTHLY:
            next_date = current_due_date
            for _ in range(interval):
                if next_date.month == 12:
                    next_date = next_date.replace(year=next_date.year + 1, month=1)
                else:
                    next_date = next_date.replace(month=next_date.month + 1)
            return next_date
        return current_due_date

    def search_todos(self, keyword: str) -> List[Todo]:
        escaped = escape_like_wildcards(keyword)
        return self.db.query(Todo).filter(
            Todo.title.like(f"%{escaped}%", escape='\\') |
            Todo.description.like(f"%{escaped}%", escape='\\')
        ).all()
