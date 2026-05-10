from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ResourceBase(BaseModel):
    title: str
    url: str
    resource_type: str = "other"
    tags: str = ""
    description: Optional[str] = ""
    source: Optional[str] = ""


class ResourceCreate(ResourceBase):
    pass


class ResourceResponse(ResourceBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SearchResult(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[ResourceResponse]


class CrawlRequest(BaseModel):
    urls: list[str]
    resource_type: str = "other"
