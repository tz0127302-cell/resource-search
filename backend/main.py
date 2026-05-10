import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from backend.database import init_db, get_db, SessionLocal
from backend.models import Resource
from backend.schemas import ResourceResponse, SearchResult
from backend.crawler import Crawler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="白榆科技", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====== API 路由（必须先定义） ======

@app.get("/api/search", response_model=SearchResult)
def search(
    q: str = Query("", description="搜索关键词"),
    resource_type: Optional[str] = Query(None, description="筛选类型: netdisk / website"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Resource)

    if q:
        keyword = f"%{q}%"
        query = query.filter(
            or_(
                Resource.title.ilike(keyword),
                Resource.tags.ilike(keyword),
                Resource.description.ilike(keyword),
            )
        )

    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)

    total = query.count()
    resources = (
        query.order_by(Resource.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SearchResult(
        total=total,
        page=page,
        page_size=page_size,
        results=[ResourceResponse.model_validate(r) for r in resources],
    )


@app.get("/api/resources/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    r = db.query(Resource).filter(Resource.id == resource_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="资源不存在")
    return ResourceResponse.model_validate(r)


@app.post("/api/crawl")
def crawl(
    urls: list[str],
    extract_method: str = "auto",
    db: Session = Depends(get_db),
):
    crawler = Crawler()
    added = 0
    for url in urls:
        items = crawler.crawl_page(url, extract_method)
        for item in items:
            existing = db.query(Resource).filter(Resource.url == item["url"]).first()
            if existing:
                continue
            res = Resource(
                title=item["title"],
                url=item["url"],
                resource_type=item["resource_type"],
                source=url,
            )
            db.add(res)
            added += 1
    db.commit()
    return {"message": f"成功添加 {added} 个资源"}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Resource.id)).scalar()
    by_type = (
        db.query(Resource.resource_type, func.count(Resource.id))
        .group_by(Resource.resource_type)
        .all()
    )
    return {
        "total": total,
        "by_type": {rtype: count for rtype, count in by_type},
    }


# ====== 前端静态文件（放在最后，不干扰 API） ======
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
