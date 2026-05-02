from sqlalchemy.orm import Session
from models.document import Document
from services.audit_mixin import AuditMixin
from typing import List, Optional
from core.logger import get_logger
from core.utils import get_local_now

logger = get_logger(__name__)


class DocumentService(AuditMixin):
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, title: str, content: str = None, category: str = None,
                        tags: str = None, created_by: int = None) -> Document:
        document = Document(
            title=title,
            content=content,
            category=category,
            tags=tags,
            created_by=created_by,
            created_at=get_local_now()
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        logger.info(f"创建文档: {title}")

        self.log_create(
            user_id=created_by,
            resource_type="document",
            resource_id=document.id,
            resource_name=title
        )

        return document

    def get_documents(self, category: str = None, skip: int = 0, limit: int = 100) -> List[Document]:
        query = self.db.query(Document)
        if category:
            query = query.filter(Document.category == category)
        return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    def get_document(self, document_id: int) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_documents_by_user(self, user_id: int, category: str = None) -> List[Document]:
        query = self.db.query(Document).filter(Document.created_by == user_id)
        if category:
            query = query.filter(Document.category == category)
        return query.order_by(Document.created_at.desc()).all()

    def update_document(self, document_id: int, user_id: int = None, **kwargs) -> Optional[Document]:
        document = self.get_document(document_id)
        if not document:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(document, key):
                setattr(document, key, value)

        document.updated_at = get_local_now()
        self.db.commit()
        self.db.refresh(document)
        logger.info(f"更新文档: {document.title}")

        self.log_update(
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            resource_name=document.title
        )

        return document

    def delete_document(self, document_id: int, user_id: int = None) -> bool:
        document = self.get_document(document_id)
        if document:
            self.log_delete(
                user_id=user_id,
                resource_type="document",
                resource_id=document_id,
                resource_name=document.title
            )
            self.db.delete(document)
            self.db.commit()
            logger.info(f"删除文档: {document.title}")
            return True
        return False

    def search_documents(self, keyword: str) -> List[Document]:
        return self.db.query(Document).filter(
            Document.title.like(f"%{keyword}%") |
            Document.content.like(f"%{keyword}%")
        ).all()

    def get_categories(self) -> List[str]:
        result = self.db.query(Document.category).distinct().all()
        return [r[0] for r in result if r[0]]
