"""
Sales CSV Repository

CSV-backed CRM repository with asyncio.Lock for write safety
and asyncio.to_thread for non-blocking file I/O.
"""

import asyncio
import csv
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.sales.models import (
    ActivityTypeEnum,
    Client,
    Deal,
    DealStage,
    Quote,
    SalesActivity,
    SalesProduct,
    STAGE_PROBABILITY,
)

logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "sales"


def _read_csv(filepath: Path) -> List[Dict[str, str]]:
    """Read CSV file synchronously (called via to_thread)."""
    if not filepath.exists():
        return []
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_csv(filepath: Path, rows: List[Dict[str, str]], fieldnames: List[str]):
    """Write CSV file synchronously (called via to_thread)."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# CSV field definitions
CLIENT_FIELDS = ["id", "name", "industry", "tier", "created_at"]
DEAL_FIELDS = [
    "id", "client_id", "title", "stage", "amount", "probability",
    "owner", "last_activity_at", "stage_entered_at", "created_at",
    "final_price", "lost_reason", "lost_to_competitor",
]
ACTIVITY_FIELDS = ["id", "deal_id", "type", "summary", "created_at"]
QUOTE_FIELDS = ["id", "deal_id", "version", "total_price", "margin", "evidence_log", "created_at"]
PRODUCT_FIELDS = ["id", "name", "list_price", "cost_base"]


class SalesCsvRepository:
    """
    CSV-backed Sales CRM repository.

    Uses asyncio.Lock per file for write safety,
    asyncio.to_thread for non-blocking I/O.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._dir = data_dir or DATA_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        # Locks created lazily to avoid event loop binding issues
        self._locks: Dict[str, asyncio.Lock] = {}

    def _lock(self, name: str) -> asyncio.Lock:
        """Get or create a lock for the given resource."""
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return self._locks[name]

    def _path(self, name: str) -> Path:
        return self._dir / f"{name}.csv"

    # === Clients ===

    async def list_clients(self) -> List[Client]:
        rows = await asyncio.to_thread(_read_csv, self._path("clients"))
        return [
            Client(
                id=r["id"],
                name=r["name"],
                industry=r.get("industry", ""),
                tier=r.get("tier", "standard"),
                created_at=r.get("created_at", ""),
            )
            for r in rows
        ]

    async def get_client(self, client_id: str) -> Optional[Client]:
        clients = await self.list_clients()
        return next((c for c in clients if c.id == client_id), None)

    async def find_client_by_name(self, name: str) -> Optional[Client]:
        clients = await self.list_clients()
        name_lower = name.strip().lower()
        return next((c for c in clients if c.name.strip().lower() == name_lower), None)

    async def create_client(self, client: Client) -> Client:
        if not client.id:
            client.id = f"CLI-{uuid4().hex[:8].upper()}"
        async with self._lock("clients"):
            rows = await asyncio.to_thread(_read_csv, self._path("clients"))
            rows.append({
                "id": client.id,
                "name": client.name,
                "industry": client.industry,
                "tier": client.tier,
                "created_at": client.created_at,
            })
            await asyncio.to_thread(_write_csv, self._path("clients"), rows, CLIENT_FIELDS)
        return client

    # === Deals ===

    async def list_deals(
        self,
        stage: Optional[DealStage] = None,
        client_id: Optional[str] = None,
    ) -> List[Deal]:
        rows = await asyncio.to_thread(_read_csv, self._path("deals"))
        deals = []
        for r in rows:
            deal = Deal(
                id=r["id"],
                client_id=r["client_id"],
                title=r["title"],
                stage=DealStage(r["stage"]),
                amount=float(r.get("amount", 0)),
                probability=int(r.get("probability", 10)),
                owner=r.get("owner", "SALES"),
                last_activity_at=r.get("last_activity_at", ""),
                stage_entered_at=r.get("stage_entered_at", ""),
                created_at=r.get("created_at", ""),
                final_price=float(r["final_price"]) if r.get("final_price") else None,
                lost_reason=r.get("lost_reason") or None,
                lost_to_competitor=r.get("lost_to_competitor") or None,
            )
            if stage and deal.stage != stage:
                continue
            if client_id and deal.client_id != client_id:
                continue
            deals.append(deal)
        return deals

    async def get_deal(self, deal_id: str) -> Optional[Deal]:
        deals = await self.list_deals()
        return next((d for d in deals if d.id == deal_id), None)

    async def create_deal(self, deal: Deal) -> Deal:
        if not deal.id:
            deal.id = f"DEAL-{uuid4().hex[:8].upper()}"
        async with self._lock("deals"):
            rows = await asyncio.to_thread(_read_csv, self._path("deals"))
            rows.append({
                "id": deal.id,
                "client_id": deal.client_id,
                "title": deal.title,
                "stage": deal.stage.value,
                "amount": str(deal.amount),
                "probability": str(deal.probability),
                "owner": deal.owner,
                "last_activity_at": deal.last_activity_at,
                "stage_entered_at": deal.stage_entered_at,
                "created_at": deal.created_at,
                "final_price": str(deal.final_price) if deal.final_price else "",
                "lost_reason": deal.lost_reason or "",
                "lost_to_competitor": deal.lost_to_competitor or "",
            })
            await asyncio.to_thread(_write_csv, self._path("deals"), rows, DEAL_FIELDS)
        return deal

    async def update_deal(self, deal: Deal) -> Optional[Deal]:
        async with self._lock("deals"):
            rows = await asyncio.to_thread(_read_csv, self._path("deals"))
            found = False
            for i, r in enumerate(rows):
                if r["id"] == deal.id:
                    rows[i] = {
                        "id": deal.id,
                        "client_id": deal.client_id,
                        "title": deal.title,
                        "stage": deal.stage.value,
                        "amount": str(deal.amount),
                        "probability": str(deal.probability),
                        "owner": deal.owner,
                        "last_activity_at": deal.last_activity_at,
                        "stage_entered_at": deal.stage_entered_at,
                        "created_at": deal.created_at,
                        "final_price": str(deal.final_price) if deal.final_price else "",
                        "lost_reason": deal.lost_reason or "",
                        "lost_to_competitor": deal.lost_to_competitor or "",
                    }
                    found = True
                    break
            if not found:
                logger.warning(f"Deal {deal.id} not found in CSV, update skipped")
                return None
            await asyncio.to_thread(_write_csv, self._path("deals"), rows, DEAL_FIELDS)
        return deal

    # === Activities ===

    async def list_activities(self, deal_id: Optional[str] = None) -> List[SalesActivity]:
        rows = await asyncio.to_thread(_read_csv, self._path("activities"))
        activities = []
        for r in rows:
            a = SalesActivity(
                id=r["id"],
                deal_id=r["deal_id"],
                type=ActivityTypeEnum(r.get("type", "note")),
                summary=r.get("summary", ""),
                created_at=r.get("created_at", ""),
            )
            if deal_id and a.deal_id != deal_id:
                continue
            activities.append(a)
        return activities

    async def create_activity(self, activity: SalesActivity) -> SalesActivity:
        if not activity.id:
            activity.id = f"ACT-{uuid4().hex[:8].upper()}"
        async with self._lock("activities"):
            rows = await asyncio.to_thread(_read_csv, self._path("activities"))
            rows.append({
                "id": activity.id,
                "deal_id": activity.deal_id,
                "type": activity.type.value,
                "summary": activity.summary,
                "created_at": activity.created_at,
            })
            await asyncio.to_thread(_write_csv, self._path("activities"), rows, ACTIVITY_FIELDS)
        # Also touch deal's last_activity_at
        deal = await self.get_deal(activity.deal_id)
        if deal:
            deal.last_activity_at = activity.created_at
            await self.update_deal(deal)
        return activity

    # === Quotes ===

    async def list_quotes(self, deal_id: Optional[str] = None) -> List[Quote]:
        rows = await asyncio.to_thread(_read_csv, self._path("quotes"))
        quotes = []
        for r in rows:
            q = Quote(
                id=r["id"],
                deal_id=r["deal_id"],
                version=int(r.get("version", 1)),
                total_price=float(r.get("total_price", 0)),
                margin=float(r.get("margin", 0)),
                evidence_log=r.get("evidence_log", ""),
                created_at=r.get("created_at", ""),
            )
            if deal_id and q.deal_id != deal_id:
                continue
            quotes.append(q)
        return quotes

    async def create_quote(self, quote: Quote) -> Quote:
        if not quote.id:
            quote.id = f"QUO-{uuid4().hex[:8].upper()}"
        async with self._lock("quotes"):
            rows = await asyncio.to_thread(_read_csv, self._path("quotes"))
            rows.append({
                "id": quote.id,
                "deal_id": quote.deal_id,
                "version": str(quote.version),
                "total_price": str(quote.total_price),
                "margin": str(quote.margin),
                "evidence_log": quote.evidence_log,
                "created_at": quote.created_at,
            })
            await asyncio.to_thread(_write_csv, self._path("quotes"), rows, QUOTE_FIELDS)
        return quote

    # === Products ===

    async def list_products(self) -> List[SalesProduct]:
        rows = await asyncio.to_thread(_read_csv, self._path("products"))
        return [
            SalesProduct(
                id=r["id"],
                name=r["name"],
                list_price=float(r.get("list_price", 0)),
                cost_base=float(r.get("cost_base", 0)),
            )
            for r in rows
        ]

    async def get_product(self, product_id: str) -> Optional[SalesProduct]:
        products = await self.list_products()
        return next((p for p in products if p.id == product_id), None)

    # === Dashboard helpers ===

    async def get_pipeline_summary(self) -> Dict[str, Any]:
        """Pipeline dashboard: count + amount per stage."""
        deals = await self.list_deals()
        summary: Dict[str, Dict[str, Any]] = {}
        total_weighted = 0.0

        for stage in DealStage:
            stage_deals = [d for d in deals if d.stage == stage]
            total_amount = sum(d.amount for d in stage_deals)
            weighted = sum(d.amount * d.probability / 100 for d in stage_deals)
            total_weighted += weighted
            summary[stage.value] = {
                "count": len(stage_deals),
                "total_amount": total_amount,
                "weighted_amount": weighted,
            }

        return {
            "stages": summary,
            "total_deals": len(deals),
            "total_weighted_pipeline": total_weighted,
        }


# --- Lazy singleton ---

_sales_repo: Optional[SalesCsvRepository] = None


def get_sales_repo() -> SalesCsvRepository:
    """Get the shared SalesCsvRepository instance."""
    global _sales_repo
    if _sales_repo is None:
        _sales_repo = SalesCsvRepository()
    return _sales_repo
