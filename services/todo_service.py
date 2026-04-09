from sqlalchemy.orm import Session
from models.todo import Todo, TodoStatus
from typing import List, Optional
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)


class TodoService:
    def __init__(self, db: Session):
        self.db = db

    def create_todo(self, title: str, description: str = None, priority: int = 5,
                    assigned_to: int = None, due_date: datetime = None,
                    created_by: int = None) -> Todo:
        todo = Todo(
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            due_date=due_date
        )
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        logger.info(f"创建待办事项: {title}")
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

    def update_todo(self, todo_id: int, **kwargs) -> Optional[Todo]:
        todo = self.get_todo(todo_id)
        if not todo:
            return None

        if 'status' in kwargs and kwargs['status'] == TodoStatus.COMPLETED:
            if todo.status != TodoStatus.COMPLETED:
                kwargs['completed_at'] = datetime.now()

        for key, value in kwargs.items():
            if value is not None and hasattr(todo, key):
                setattr(todo, key, value)

        self.db.commit()
        self.db.refresh(todo)
        logger.info(f"更新待办事项: {todo.title}")
        return todo

    def delete_todo(self, todo_id: int) -> bool:
        todo = self.get_todo(todo_id)
        if todo:
            self.db.delete(todo)
            self.db.commit()
            logger.info(f"删除待办事项: {todo.title}")
            return True
        return False

    def complete_todo(self, todo_id: int) -> Optional[Todo]:
        return self.update_todo(todo_id, status=TodoStatus.COMPLETED)

    def search_todos(self, keyword: str) -> List[Todo]:
        return self.db.query(Todo).filter(
            Todo.title.like(f"%{keyword}%") |
            Todo.description.like(f"%{keyword}%")
        ).all()
