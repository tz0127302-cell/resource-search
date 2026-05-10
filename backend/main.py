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


SEED_DATA = [
    ("Adobe Photoshop 2025", "https://pan.baidu.com/s/1ps1234", "netdisk", "设计,图像处理", "专业图像编辑软件，设计必备"),
    ("JetBrains IntelliJ IDEA", "https://pan.quark.cn/s/1iq5678", "netdisk", "开发,Java,IDE", "最强Java开发IDE，智能代码提示"),
    ("7-Zip 24.0", "https://www.7-zip.org/", "website", "系统工具,压缩", "免费开源压缩工具，轻量高效"),
    ("Snipaste 截图工具", "https://pan.baidu.com/s/1sn9012", "netdisk", "办公,截图", "好用的截图贴图工具，效率提升神器"),
    ("OBS Studio 录屏", "https://pan.quark.cn/s/1obs3456", "netdisk", "媒体,录屏,直播", "免费开源录屏直播软件"),
    ("Visual Studio Code", "https://code.visualstudio.com/", "website", "开发,编辑器", "微软出品的轻量代码编辑器"),
    ("Everything 搜索", "https://pan.baidu.com/s/1ev7890", "netdisk", "系统工具,搜索", "Windows 文件瞬间搜索工具"),
    ("Notion 笔记", "https://www.notion.so/", "website", "办公,笔记,协作", "全能笔记与知识管理工具"),
    ("DaVinci Resolve 调色", "https://pan.baidu.com/s/1dv1234", "netdisk", "媒体,视频编辑,调色", "专业视频调色和剪辑软件"),
    ("Wireshark 抓包", "https://www.wireshark.org/", "website", "网络,抓包,分析", "网络协议分析工具，开发者必备"),
    ("PotPlayer 播放器", "https://pan.baidu.com/s/1pp5678", "netdisk", "媒体,播放器", "最强本地视频播放器，解码能力一流"),
    ("Figma 设计", "https://www.figma.com/", "website", "设计,UI,协作", "在线UI设计工具，团队协作首选"),
    ("Typora Markdown", "https://pan.baidu.com/s/1tp9012", "netdisk", "办公,Markdown,写作", "优雅的 Markdown 编辑器，所见即所得"),
    ("Docker Desktop", "https://www.docker.com/", "website", "开发,容器,部署", "容器化开发环境，开发部署神器"),
    ("迅雷极速版", "https://pan.baidu.com/s/1xl3456", "netdisk", "系统工具,下载", "轻量下载工具，告别限速"),
    ("Postman API", "https://www.postman.com/", "website", "开发,API,测试", "API调试与测试工具"),
    ("向日葵远程控制", "https://pan.baidu.com/s/1xrk7890", "netdisk", "办公,远程控制", "远程桌面控制，办公必备"),
    ("HandBrake 视频压缩", "https://handbrake.fr/", "website", "媒体,视频,压缩", "免费视频格式转换压缩工具"),
    ("AutoCAD 2025", "https://pan.quark.cn/s/1ac1234", "netdisk", "设计,CAD,制图", "工程制图与设计软件"),
    ("Clash Verge 代理", "https://github.com/clash-verge-rev/clash-verge-rev", "website", "网络,代理,工具", "网络代理管理工具"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # 数据库为空时填充示例数据
    db = SessionLocal()
    try:
        if db.query(func.count(Resource.id)).scalar() == 0:
            for title, url, rtype, tags, desc in SEED_DATA:
                db.add(Resource(title=title, url=url, resource_type=rtype, tags=tags, description=desc))
            db.commit()
            logger.info("已添加 %d 条示例数据", len(SEED_DATA))
    finally:
        db.close()
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


# ====== 后台管理 API ======

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "baiyu2026")


def verify_admin(token: str):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员密码错误")
    return True


def ensure_url_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


@app.post("/api/resources", response_model=ResourceResponse)
def create_resource(
    body: dict,
    admin_token: str = Query(...),
    db: Session = Depends(get_db),
):
    verify_admin(admin_token)
    res = Resource(
        title=body.get("title", ""),
        url=ensure_url_scheme(body.get("url", "")),
        resource_type=body.get("resource_type", "netdisk"),
        tags=body.get("tags", ""),
        description=body.get("description", ""),
    )
    db.add(res)
    db.commit()
    db.refresh(res)
    return ResourceResponse.model_validate(res)


@app.put("/api/resources/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: int,
    body: dict,
    admin_token: str = Query(...),
    db: Session = Depends(get_db),
):
    verify_admin(admin_token)
    r = db.query(Resource).filter(Resource.id == resource_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="资源不存在")
    if "title" in body:
        r.title = body["title"]
    if "url" in body:
        r.url = ensure_url_scheme(body["url"])
    if "resource_type" in body:
        r.resource_type = body["resource_type"]
    if "tags" in body:
        r.tags = body["tags"]
    if "description" in body:
        r.description = body["description"]
    db.commit()
    db.refresh(r)
    return ResourceResponse.model_validate(r)


@app.delete("/api/resources/{resource_id}")
def delete_resource(
    resource_id: int,
    admin_token: str = Query(...),
    db: Session = Depends(get_db),
):
    verify_admin(admin_token)
    r = db.query(Resource).filter(Resource.id == resource_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="资源不存在")
    db.delete(r)
    db.commit()
    return {"message": "已删除"}


@app.get("/api/admin/all")
def list_all(
    admin_token: str = Query(...),
    db: Session = Depends(get_db),
):
    verify_admin(admin_token)
    resources = db.query(Resource).order_by(Resource.created_at.desc()).all()
    return {
        "total": len(resources),
        "results": [ResourceResponse.model_validate(r) for r in resources],
    }


# ====== 前端静态文件（放在最后，不干扰 API） ======
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
