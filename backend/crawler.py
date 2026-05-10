import re
import logging
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 常见的网盘域名关键词
NETDISK_DOMAINS = [
    "pan.baidu.com", "yun.baidu.com",
    "pan.xunlei.com", "115.com", "pan.quark.cn",
    "aliyundrive.com", "alipan.com",
    "123pan.com", "123684.com", "123865.com",
    "lanzouv.com", "lanzouo.com", "lanzoui.com",
    "nextcloud", "owncloud",
]

DOMAIN_ALIAS = {
    "pan.baidu.com": "百度网盘",
    "yun.baidu.com": "百度网盘",
    "pan.xunlei.com": "迅雷网盘",
    "115.com": "115网盘",
    "pan.quark.cn": "夸克网盘",
    "aliyundrive.com": "阿里云盘",
    "alipan.com": "阿里云盘",
    "123pan.com": "123云盘",
    "lanzouv.com": "蓝奏云",
    "lanzouo.com": "蓝奏云",
    "lanzoui.com": "蓝奏云",
}


def guess_resource_type(url: str) -> str:
    parsed = urlparse(url)
    for domain in NETDISK_DOMAINS:
        if domain in parsed.netloc:
            return "netdisk"
    return "website"


def get_netdisk_label(url: str) -> str:
    parsed = urlparse(url)
    for domain, alias in DOMAIN_ALIAS.items():
        if domain in parsed.netloc:
            return alias
    return "网盘"


class Crawler:
    def __init__(self, timeout: int = 15, delay: float = 1.0):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        })

    def fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

    def extract_links(self, html: str, base_url: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        resources = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            full_url = urljoin(base_url, href)
            text = a_tag.get_text(strip=True)

            if not text or not full_url.startswith("http"):
                continue

            rtype = guess_resource_type(full_url)
            resources.append({
                "title": text,
                "url": full_url,
                "resource_type": rtype,
            })

        return resources

    def extract_text_based(self, html: str, base_url: str) -> list[dict]:
        """从页面文本中提取网盘链接"""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text()
        resources = []

        # 匹配常见网盘链接模式
        netdisk_patterns = [
            r"https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+",
            r"https?://pan\.quark\.cn/s/[a-zA-Z0-9_-]+",
            r"https?://(?:www\.)?123pan\.com/s/[a-zA-Z0-9_-]+",
            r"https?://(?:www\.)?alipan\.com/s/[a-zA-Z0-9_-]+",
            r"https?://(?:www\.)?aliyundrive\.com/s/[a-zA-Z0-9_-]+",
            r"https?://115\.com/s/[a-zA-Z0-9_-]+",
        ]

        for pattern in netdisk_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group()
                resources.append({
                    "title": get_netdisk_label(url),
                    "url": url,
                    "resource_type": "netdisk",
                })

        return resources

    def crawl_page(self, url: str, extract_method: str = "auto") -> list[dict]:
        html = self.fetch(url)
        if not html:
            return []

        if extract_method == "links":
            return self.extract_links(html, url)
        elif extract_method == "text":
            return self.extract_text_based(html, url)
        else:
            links = self.extract_links(html, url)
            text_links = self.extract_text_based(html, url)
            seen = set()
            combined = []
            for r in links + text_links:
                if r["url"] not in seen:
                    seen.add(r["url"])
                    combined.append(r)
            return combined
