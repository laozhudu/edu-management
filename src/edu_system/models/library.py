# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
library 域模型 — 图书管理（A2：验证底座不局限教务的演示业务域）

完全复用现有底座（User 权限/审计/字典/分页），无任何教务耦合。
"""
from __future__ import annotations

from edu_system.models.base import *  # noqa: F401,F403,F405


class Book(Base):
    """图书"""

    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False, comment="书名")
    author = Column(String(60), default="", comment="作者")
    isbn = Column(String(20), default="", index=True, comment="ISBN")
    category = Column(String(40), default="", comment="分类")
    publisher = Column(String(60), default="", comment="出版社")
    publish_year = Column(Integer, default=0, comment="出版年份")
    total_copies = Column(Integer, default=1, comment="馆藏册数")
    available_copies = Column(Integer, default=1, comment="可借册数")
    status = Column(String(4), default="0", comment="状态: 0在架/1下架")
    created_at = Column(DateTime, server_default=func.now())


class BorrowRecord(Base):
    """借阅记录"""

    __tablename__ = "borrow_records"
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    borrower_name = Column(String(40), default="", comment="借阅人")
    borrow_date = Column(Date, nullable=True, comment="借出日期")
    due_date = Column(Date, nullable=True, comment="应还日期")
    return_date = Column(Date, nullable=True, comment="实际归还日期")
    status = Column(String(4), default="0", comment="0借出/1已还/2逾期")
    operator = Column(String(32), default="", comment="经办人")
    created_at = Column(DateTime, server_default=func.now())
