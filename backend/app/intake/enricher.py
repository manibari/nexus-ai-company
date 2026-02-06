"""
Data Enricher

資訊補全模組：從外部來源補全公司、聯絡人資訊
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    """公司資訊"""
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    size: Optional[str] = None  # startup, small, medium, large, enterprise
    employee_count: Optional[int] = None
    founded_year: Optional[int] = None
    location: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    technologies: List[str] = None
    funding: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "industry": self.industry,
            "description": self.description,
            "size": self.size,
            "employee_count": self.employee_count,
            "location": self.location,
            "website": self.website,
        }


@dataclass
class ContactInfo:
    """聯絡人資訊"""
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    company: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "email": self.email,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "company": self.company,
        }


class DataEnricher:
    """
    資訊補全器

    從外部來源補全：
    - 公司資訊（官網、LinkedIn、Crunchbase）
    - 聯絡人資訊（LinkedIn）
    - 產業資訊
    - 新聞動態
    """

    def __init__(self, http_client=None):
        self.http = http_client
        self._cache: Dict[str, Any] = {}

    async def fetch_url_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        從 URL 抓取資訊

        支援：
        - 公司官網
        - LinkedIn 公司頁面
        - Crunchbase
        - 新聞文章
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # 快取檢查
        cache_key = f"url:{url}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = None

        try:
            # LinkedIn 公司頁面
            if "linkedin.com/company" in url:
                result = await self._fetch_linkedin_company(url)

            # Crunchbase
            elif "crunchbase.com" in url:
                result = await self._fetch_crunchbase(url)

            # 一般網站
            else:
                result = await self._fetch_website(url)

            if result:
                self._cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Failed to fetch URL info: {url}, error: {e}")
            return None

    async def search_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        搜尋公司資訊

        依序嘗試：
        1. Google 搜尋官網
        2. LinkedIn 搜尋
        3. Crunchbase 搜尋
        """
        cache_key = f"company:{company_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # TODO: 實際實作搜尋邏輯
        # 目前返回模擬資料

        result = {
            "name": company_name,
            "source": "search",
            "confidence": 0.6,
        }

        self._cache[cache_key] = result
        return result

    async def find_contacts(
        self,
        company_name: str,
        titles: List[str] = None,
    ) -> List[ContactInfo]:
        """
        尋找公司聯絡人

        Args:
            company_name: 公司名稱
            titles: 目標職稱（如 CEO, CTO, VP Sales）
        """
        titles = titles or ["CEO", "CTO", "VP", "Director"]

        # TODO: 實際實作搜尋邏輯
        # 可以使用：
        # - LinkedIn Sales Navigator API
        # - Apollo.io API
        # - Hunter.io API

        return []

    async def get_company_news(
        self,
        company_name: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """取得公司相關新聞"""
        # TODO: 實作新聞搜尋
        # 可以使用：
        # - Google News API
        # - NewsAPI
        # - 自建爬蟲

        return []

    async def enrich_lead(
        self,
        company_name: str,
        contact_email: Optional[str] = None,
        website_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        完整補全 Lead 資訊

        整合多個來源的資訊
        """
        result = {
            "company": None,
            "contacts": [],
            "news": [],
            "technologies": [],
        }

        # 1. 從 URL 取得公司資訊
        if website_url:
            url_info = await self.fetch_url_info(website_url)
            if url_info:
                result["company"] = url_info

        # 2. 搜尋公司資訊
        if not result["company"]:
            search_result = await self.search_company(company_name)
            if search_result:
                result["company"] = search_result

        # 3. 尋找聯絡人
        contacts = await self.find_contacts(company_name)
        result["contacts"] = [c.to_dict() for c in contacts]

        # 4. 取得新聞
        news = await self.get_company_news(company_name)
        result["news"] = news

        return result

    # === 內部方法 ===

    async def _fetch_linkedin_company(self, url: str) -> Optional[Dict[str, Any]]:
        """從 LinkedIn 公司頁面抓取資訊"""
        # LinkedIn 需要登入才能抓取完整資訊
        # 實際實作可能需要：
        # 1. LinkedIn API（需要申請）
        # 2. Proxycurl 等第三方服務
        # 3. Selenium 模擬登入

        logger.info(f"Fetching LinkedIn company: {url}")

        # 模擬返回
        return {
            "source": "linkedin",
            "url": url,
        }

    async def _fetch_crunchbase(self, url: str) -> Optional[Dict[str, Any]]:
        """從 Crunchbase 抓取資訊"""
        logger.info(f"Fetching Crunchbase: {url}")

        # TODO: 實作 Crunchbase API 呼叫

        return {
            "source": "crunchbase",
            "url": url,
        }

    async def _fetch_website(self, url: str) -> Optional[Dict[str, Any]]:
        """從一般網站抓取資訊"""
        logger.info(f"Fetching website: {url}")

        parsed = urlparse(url)
        domain = parsed.netloc

        # 移除 www 前綴
        if domain.startswith("www."):
            domain = domain[4:]

        result = {
            "source": "website",
            "url": url,
            "domain": domain,
        }

        # TODO: 實作網站爬取
        # 可以抓取：
        # - <title> 標籤
        # - meta description
        # - Open Graph 標籤
        # - 結構化資料 (JSON-LD)

        return result

    def _extract_company_name_from_domain(self, domain: str) -> str:
        """從域名提取公司名稱"""
        # 移除常見後綴
        name = domain.split(".")[0]

        # 轉換為標題格式
        name = name.replace("-", " ").replace("_", " ").title()

        return name
