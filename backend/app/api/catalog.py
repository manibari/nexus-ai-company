"""
Product Catalog API Router

產品目錄 API - 從 products/ 目錄讀取產品資訊
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Products directory path
PRODUCTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "products"


def parse_product_md(product_dir: Path) -> Optional[Dict[str, Any]]:
    """解析 PRODUCT.md 檔案"""
    product_file = product_dir / "PRODUCT.md"
    if not product_file.exists():
        return None

    content = product_file.read_text(encoding="utf-8")

    # Extract basic info from table
    product = {
        "id": product_dir.name,
        "name": product_dir.name,
        "description": "",
        "status": "development",
        "version": "0.0.0",
        "release_date": None,
        "links": {},
        "features": [],
        "tech_stack": {},
        "full_content": content,
    }

    # Parse title (first H1)
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    if title_match:
        product["name"] = title_match.group(1).strip()

    # Parse basic info table
    # Look for | 產品代號 | ... | pattern
    code_match = re.search(r"\|\s*產品代號\s*\|\s*([^|]+)\s*\|", content)
    if code_match:
        product["id"] = code_match.group(1).strip()

    version_match = re.search(r"\|\s*版本\s*\|\s*([^|]+)\s*\|", content)
    if version_match:
        product["version"] = version_match.group(1).strip()

    status_match = re.search(r"\|\s*狀態\s*\|\s*([^|]+)\s*\|", content)
    if status_match:
        status_text = status_match.group(1).strip()
        if "Production" in status_text or "🟢" in status_text:
            product["status"] = "production"
        elif "Beta" in status_text or "🟡" in status_text:
            product["status"] = "beta"
        elif "MVP" in status_text or "🔵" in status_text:
            product["status"] = "mvp"
        elif "Development" in status_text or "🔧" in status_text:
            product["status"] = "development"
        elif "Deprecated" in status_text or "⚪" in status_text:
            product["status"] = "deprecated"

    date_match = re.search(r"\|\s*上線日期\s*\|\s*([^|]+)\s*\|", content)
    if date_match:
        product["release_date"] = date_match.group(1).strip()

    # Parse description (## 簡介 section)
    desc_match = re.search(r"## 簡介\s*\n+(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
    if desc_match:
        product["description"] = desc_match.group(1).strip()[:200]

    # Parse features (from ## 功能清單)
    features_match = re.search(r"## 功能清單\s*\n(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
    if features_match:
        features_text = features_match.group(1)
        # Extract items with ✅
        features = re.findall(r"[✅✓]\s*(.+?)(?:\n|$)", features_text)
        product["features"] = [f.strip() for f in features[:6]]  # Limit to 6

    # Parse tech stack (## 技術架構)
    tech_match = re.search(r"## 技術架構\s*\n(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
    if tech_match:
        tech_text = tech_match.group(1)
        frontend_match = re.search(r"\|\s*Frontend\s*\|\s*([^|]+)\s*\|", tech_text)
        backend_match = re.search(r"\|\s*Backend\s*\|\s*([^|]+)\s*\|", tech_text)
        database_match = re.search(r"\|\s*Database\s*\|\s*([^|]+)\s*\|", tech_text)

        if frontend_match:
            product["tech_stack"]["frontend"] = frontend_match.group(1).strip()
        if backend_match:
            product["tech_stack"]["backend"] = backend_match.group(1).strip()
        if database_match:
            product["tech_stack"]["database"] = database_match.group(1).strip()

    # Parse links (## 相關連結 or ## 部署資訊)
    links_match = re.search(r"## (?:相關連結|部署資訊)\s*\n(.+?)(?=\n##|\n---|\Z)", content, re.DOTALL)
    if links_match:
        links_text = links_match.group(1)

        # Demo/Frontend URL
        demo_match = re.search(r"(?:Demo|Frontend|前端)[^|]*\|\s*(https?://[^\s|]+|http://localhost:\d+)", links_text, re.IGNORECASE)
        if demo_match:
            product["links"]["demo"] = demo_match.group(1).strip()

        # API URL
        api_match = re.search(r"(?:API|Backend|後端)[^|]*\|\s*(https?://[^\s|]+|http://localhost:\d+)", links_text, re.IGNORECASE)
        if api_match:
            product["links"]["api"] = api_match.group(1).strip()

        # Source URL
        source_match = re.search(r"(?:源碼|Source|GitHub)[^|]*\|\s*(https?://[^\s|]+)", links_text, re.IGNORECASE)
        if source_match:
            product["links"]["source"] = source_match.group(1).strip()

        # Docs URL
        docs_match = re.search(r"(?:文件|Docs)[^|]*\|\s*([^\s|]+)", links_text, re.IGNORECASE)
        if docs_match:
            product["links"]["docs"] = docs_match.group(1).strip()

    return product


def get_all_products() -> List[Dict[str, Any]]:
    """取得所有產品"""
    products = []

    if not PRODUCTS_DIR.exists():
        return products

    for item in PRODUCTS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            product = parse_product_md(item)
            if product:
                products.append(product)

    # Sort by status (production first, then mvp, then development)
    status_order = {"production": 0, "beta": 1, "mvp": 2, "development": 3, "deprecated": 4}
    products.sort(key=lambda p: status_order.get(p["status"], 5))

    return products


@router.get("", response_model=List[Dict[str, Any]])
async def list_catalog():
    """取得產品目錄清單"""
    products = get_all_products()
    # Return without full_content for list view
    return [
        {k: v for k, v in p.items() if k != "full_content"}
        for p in products
    ]


@router.get("/{product_id}", response_model=Dict[str, Any])
async def get_product(product_id: str):
    """取得產品詳情"""
    product_dir = PRODUCTS_DIR / product_id
    if not product_dir.exists():
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    product = parse_product_md(product_dir)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} has no PRODUCT.md")

    return product


@router.get("/{product_id}/changelog", response_model=Dict[str, Any])
async def get_changelog(product_id: str):
    """取得產品版本歷史"""
    changelog_file = PRODUCTS_DIR / product_id / "CHANGELOG.md"
    if not changelog_file.exists():
        raise HTTPException(status_code=404, detail=f"Changelog not found for {product_id}")

    content = changelog_file.read_text(encoding="utf-8")
    return {
        "product_id": product_id,
        "content": content,
    }
