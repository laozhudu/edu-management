"""
图书管理 API（A2：独立业务域演示，完全复用底座）

底座复用点：RBAC 权限、PageQuery 分页、统一返回、审计（audit_logs）、字典、依赖注入。
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import PageQuery, get_db, paginate_response, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import Book, BorrowRecord

router = APIRouter(tags=["图书管理"])


class BookCreate(BaseModel):
    title: str
    author: str = ""
    isbn: str = ""
    category: str = ""
    publisher: str = ""
    publish_year: int = 0
    total_copies: int = 1


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    category: str | None = None
    publisher: str | None = None
    publish_year: int | None = None
    total_copies: int | None = None
    status: str | None = None


class BorrowBody(BaseModel):
    borrower_name: str
    days: int = 30


def _book_dict(b: Book) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "author": b.author,
        "isbn": b.isbn,
        "category": b.category,
        "publisher": b.publisher,
        "publish_year": b.publish_year,
        "total_copies": b.total_copies,
        "available_copies": b.available_copies,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


@router.get("/books")
def book_list(
    query: PageQuery = Depends(),
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    q = db.query(Book)
    if keyword:
        q = q.filter(Book.title.contains(keyword))
    total = q.count()
    items = q.order_by(Book.id.desc()).offset(query.offset).limit(query.page_size).all()
    return paginate_response([_book_dict(b) for b in items], total, query.page, query.page_size)


@router.post("/books", status_code=201)
def book_create(
    body: BookCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="书名不能为空")
    b = Book(
        title=body.title.strip(),
        author=body.author,
        isbn=body.isbn,
        category=body.category,
        publisher=body.publisher,
        publish_year=body.publish_year,
        total_copies=max(body.total_copies, 1),
        available_copies=max(body.total_copies, 1),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"id": b.id}


@router.put("/books/{book_id}")
def book_update(
    book_id: int,
    body: BookUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    b = db.get(Book, book_id)
    if not b:
        raise HTTPException(status_code=404, detail="图书不存在")
    if body.title is not None:
        b.title = body.title
    if body.author is not None:
        b.author = body.author
    if body.isbn is not None:
        b.isbn = body.isbn
    if body.category is not None:
        b.category = body.category
    if body.total_copies is not None:
        diff = body.total_copies - b.total_copies
        b.total_copies = body.total_copies
        b.available_copies = max(b.available_copies + diff, 0)
    if body.status is not None:
        b.status = body.status
    db.commit()
    return {"ok": True}


@router.delete("/books/{book_id}")
def book_delete(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    b = db.get(Book, book_id)
    if not b:
        raise HTTPException(status_code=404, detail="图书不存在")
    active = db.query(BorrowRecord).filter(BorrowRecord.book_id == book_id, BorrowRecord.status == "0").first()
    if active:
        raise HTTPException(status_code=400, detail="存在未归还借阅，无法删除")
    db.delete(b)
    db.commit()
    return {"ok": True}


@router.post("/books/{book_id}/borrow")
def book_borrow(
    book_id: int,
    body: BorrowBody,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    b = db.get(Book, book_id)
    if not b:
        raise HTTPException(status_code=404, detail="图书不存在")
    if (b.available_copies or 0) <= 0:
        raise HTTPException(status_code=400, detail="无可借册数")
    b.available_copies = (b.available_copies or 0) - 1
    db.add(
        BorrowRecord(
            book_id=book_id,
            borrower_name=body.borrower_name,
            borrow_date=date.today(),
            due_date=date.today() + timedelta(days=max(body.days, 1)),
            status="0",
            operator=_user.username,
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/books/{book_id}/return")
def book_return(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_EDIT)),
):
    rec = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.book_id == book_id, BorrowRecord.status == "0")
        .order_by(BorrowRecord.id.desc())
        .first()
    )
    if not rec:
        raise HTTPException(status_code=400, detail="无借出记录")
    rec.status = "1"
    rec.return_date = date.today()
    b = db.get(Book, book_id)
    if b:
        b.available_copies = (b.available_copies or 0) + 1
    db.commit()
    return {"ok": True}


@router.get("/borrow-records")
def borrow_list(
    query: PageQuery = Depends(),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(Permission.CONFIG_VIEW)),
):
    q = db.query(BorrowRecord)
    total = q.count()
    items = q.order_by(BorrowRecord.id.desc()).offset(query.offset).limit(query.page_size).all()
    records = []
    for r in items:
        book = db.get(Book, r.book_id)
        records.append(
            {
                "id": r.id,
                "book_id": r.book_id,
                "book_title": book.title if book else "",
                "borrower_name": r.borrower_name,
                "borrow_date": r.borrow_date.isoformat() if r.borrow_date else None,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "return_date": r.return_date.isoformat() if r.return_date else None,
                "status": r.status,
            }
        )
    return paginate_response(records, total, query.page, query.page_size)
