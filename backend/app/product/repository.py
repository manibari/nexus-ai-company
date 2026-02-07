"""
Product Repository

SQLAlchemy-backed repository for Product items.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.product.models import (
    ProductItem,
    ProductStage,
    ProductPriority,
    ProductType,
    QAResult,
    UATFeedback,
    STAGE_ORDER,
)

logger = logging.getLogger(__name__)


# === Global accessor ===
_product_repo: Optional["ProductRepository"] = None


def get_product_repo() -> "ProductRepository":
    """取得共享的 ProductRepository 實例"""
    global _product_repo
    if _product_repo is None:
        from app.db.database import AsyncSessionLocal
        _product_repo = ProductRepository(session_factory=AsyncSessionLocal)
    return _product_repo


def set_product_repo(repo: "ProductRepository") -> None:
    """設定共享的 ProductRepository 實例（用於測試注入）"""
    global _product_repo
    _product_repo = repo


# === Domain ↔ DB Converters ===

def _domain_to_db(product: ProductItem) -> "ProductItemDB":
    """ProductItem dataclass → ProductItemDB ORM"""
    from app.db.models import ProductItemDB
    return ProductItemDB(
        id=product.id,
        title=product.title,
        description=product.description,
        type=product.type.value,
        priority=product.priority.value,
        stage=product.stage.value,
        stage_entered_at=product.stage_entered_at,
        version=product.version,
        target_release=product.target_release,
        spec_doc=product.spec_doc,
        acceptance_criteria=product.acceptance_criteria,
        assignee=product.assignee,
        owner=product.owner,
        qa_results=[r.to_dict() for r in product.qa_results] if product.qa_results else [],
        uat_feedback=[f.to_dict() for f in product.uat_feedback] if product.uat_feedback else [],
        created_at=product.created_at,
        started_at=product.started_at,
        completed_at=product.completed_at,
        estimated_hours=product.estimated_hours,
        actual_hours=product.actual_hours,
        blocked_reason=product.blocked_reason,
        blocked_by=product.blocked_by,
        source_input_id=product.source_input_id,
        related_opportunity_id=product.related_opportunity_id,
        notes=product.notes,
        tags=product.tags,
    )


def _db_to_domain(row) -> ProductItem:
    """ProductItemDB ORM → ProductItem dataclass"""
    # Deserialize QA results
    qa_results = []
    for r in (row.qa_results or []):
        qa_results.append(QAResult(
            test_name=r.get("test_name", ""),
            passed=r.get("passed", False),
            details=r.get("details"),
            timestamp=datetime.fromisoformat(r["timestamp"]) if r.get("timestamp") else datetime.utcnow(),
        ))

    # Deserialize UAT feedback
    uat_feedback = []
    for f in (row.uat_feedback or []):
        uat_feedback.append(UATFeedback(
            feedback=f.get("feedback", ""),
            from_ceo=f.get("from_ceo", True),
            approved=f.get("approved"),
            timestamp=datetime.fromisoformat(f["timestamp"]) if f.get("timestamp") else datetime.utcnow(),
        ))

    return ProductItem(
        id=row.id,
        title=row.title,
        description=row.description or "",
        type=ProductType(row.type) if row.type else ProductType.FEATURE,
        priority=ProductPriority(row.priority) if row.priority else ProductPriority.MEDIUM,
        stage=ProductStage(row.stage) if row.stage else ProductStage.P1_BACKLOG,
        stage_entered_at=row.stage_entered_at or datetime.utcnow(),
        version=row.version,
        target_release=row.target_release,
        spec_doc=row.spec_doc,
        acceptance_criteria=row.acceptance_criteria or [],
        assignee=row.assignee,
        owner=row.owner or "ORCHESTRATOR",
        qa_results=qa_results,
        uat_feedback=uat_feedback,
        created_at=row.created_at or datetime.utcnow(),
        started_at=row.started_at,
        completed_at=row.completed_at,
        estimated_hours=row.estimated_hours,
        actual_hours=row.actual_hours,
        blocked_reason=row.blocked_reason,
        blocked_by=row.blocked_by,
        source_input_id=row.source_input_id,
        related_opportunity_id=row.related_opportunity_id,
        notes=row.notes,
        tags=row.tags or [],
    )


class ProductRepository:
    """SQLAlchemy-backed repository for product items"""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def _session(self):
        return self._session_factory()

    async def create(self, product: ProductItem) -> ProductItem:
        """Create a new product item"""
        from app.db.models import ProductItemDB
        async with self._session() as session:
            db_item = _domain_to_db(product)
            session.add(db_item)
            await session.commit()
        logger.info(f"Created product item: {product.id}")
        return product

    async def get(self, product_id: str) -> Optional[ProductItem]:
        """Get a product item by ID"""
        from app.db.models import ProductItemDB
        async with self._session() as session:
            row = await session.get(ProductItemDB, product_id)
            return _db_to_domain(row) if row else None

    async def update(self, product: ProductItem) -> ProductItem:
        """Update a product item"""
        from app.db.models import ProductItemDB
        async with self._session() as session:
            row = await session.get(ProductItemDB, product.id)
            if not row:
                raise ValueError(f"ProductItem {product.id} not found")
            row.title = product.title
            row.description = product.description
            row.type = product.type.value
            row.priority = product.priority.value
            row.stage = product.stage.value
            row.stage_entered_at = product.stage_entered_at
            row.version = product.version
            row.target_release = product.target_release
            row.spec_doc = product.spec_doc
            row.acceptance_criteria = product.acceptance_criteria
            row.assignee = product.assignee
            row.owner = product.owner
            row.qa_results = [r.to_dict() for r in product.qa_results]
            row.uat_feedback = [f.to_dict() for f in product.uat_feedback]
            row.started_at = product.started_at
            row.completed_at = product.completed_at
            row.estimated_hours = product.estimated_hours
            row.actual_hours = product.actual_hours
            row.blocked_reason = product.blocked_reason
            row.blocked_by = product.blocked_by
            row.source_input_id = product.source_input_id
            row.related_opportunity_id = product.related_opportunity_id
            row.notes = product.notes
            row.tags = product.tags
            await session.commit()
        return product

    async def delete(self, product_id: str) -> bool:
        """Delete a product item"""
        from app.db.models import ProductItemDB
        async with self._session() as session:
            row = await session.get(ProductItemDB, product_id)
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def list(
        self,
        stage: Optional[ProductStage] = None,
        product_type: Optional[ProductType] = None,
        priority: Optional[ProductPriority] = None,
        assignee: Optional[str] = None,
        version: Optional[str] = None,
        limit: int = 100,
    ) -> List[ProductItem]:
        """List product items with optional filters"""
        from app.db.models import ProductItemDB
        async with self._session() as session:
            stmt = select(ProductItemDB)

            if stage:
                stmt = stmt.where(ProductItemDB.stage == stage.value)
            if product_type:
                stmt = stmt.where(ProductItemDB.type == product_type.value)
            if priority:
                stmt = stmt.where(ProductItemDB.priority == priority.value)
            if assignee:
                stmt = stmt.where(ProductItemDB.assignee == assignee)
            if version:
                stmt = stmt.where(ProductItemDB.target_release == version)

            stmt = stmt.order_by(ProductItemDB.created_at).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        # Convert to domain and sort by priority
        products = [_db_to_domain(r) for r in rows]
        priority_order = {
            ProductPriority.CRITICAL: 0,
            ProductPriority.HIGH: 1,
            ProductPriority.MEDIUM: 2,
            ProductPriority.LOW: 3,
        }
        products.sort(key=lambda p: (priority_order.get(p.priority, 4), p.created_at))
        return products

    async def advance_stage(self, product_id: str) -> Optional[ProductItem]:
        """Advance product to next stage"""
        product = await self.get(product_id)
        if not product:
            return None

        new_stage = product.advance_stage()
        if new_stage:
            await self.update(product)
            return product
        return None

    async def set_stage(
        self, product_id: str, stage: ProductStage
    ) -> Optional[ProductItem]:
        """Set product to specific stage"""
        product = await self.get(product_id)
        if not product:
            return None

        can_advance, blockers = product.can_advance_to(stage)
        if not can_advance:
            return None

        product.stage = stage
        product.stage_entered_at = datetime.utcnow()

        if stage == ProductStage.P3_IN_PROGRESS and not product.started_at:
            product.started_at = datetime.utcnow()
        elif stage == ProductStage.P6_DONE:
            product.completed_at = datetime.utcnow()

        await self.update(product)
        return product

    async def block(
        self, product_id: str, reason: str, blocked_by: Optional[str] = None
    ) -> Optional[ProductItem]:
        """Mark product as blocked"""
        product = await self.get(product_id)
        if not product:
            return None

        product.stage = ProductStage.BLOCKED
        product.blocked_reason = reason
        product.blocked_by = blocked_by
        product.stage_entered_at = datetime.utcnow()

        await self.update(product)
        return product

    async def unblock(self, product_id: str, return_to_stage: ProductStage) -> Optional[ProductItem]:
        """Unblock product and return to specified stage"""
        product = await self.get(product_id)
        if not product or product.stage != ProductStage.BLOCKED:
            return None

        product.stage = return_to_stage
        product.blocked_reason = None
        product.blocked_by = None
        product.stage_entered_at = datetime.utcnow()

        await self.update(product)
        return product

    async def assign(
        self, product_id: str, assignee: str
    ) -> Optional[ProductItem]:
        """Assign product to an agent"""
        product = await self.get(product_id)
        if not product:
            return None

        product.assignee = assignee
        await self.update(product)
        return product

    async def add_qa_result(
        self, product_id: str, test_name: str, passed: bool, details: Optional[str] = None
    ) -> Optional[ProductItem]:
        """Add QA test result"""
        product = await self.get(product_id)
        if not product:
            return None

        result = QAResult(
            test_name=test_name,
            passed=passed,
            details=details,
        )
        product.qa_results.append(result)

        await self.update(product)
        return product

    async def add_uat_feedback(
        self, product_id: str, feedback: str, approved: Optional[bool] = None
    ) -> Optional[ProductItem]:
        """Add UAT feedback"""
        product = await self.get(product_id)
        if not product:
            return None

        uat = UATFeedback(
            feedback=feedback,
            approved=approved,
        )
        product.uat_feedback.append(uat)

        await self.update(product)
        return product

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        products = await self.list(limit=10000)

        # Count by stage
        stage_counts = {stage.value: 0 for stage in ProductStage}
        for p in products:
            stage_counts[p.stage.value] += 1

        # Count by type
        type_counts = {t.value: 0 for t in ProductType}
        for p in products:
            type_counts[p.type.value] += 1

        # Count by priority
        priority_counts = {pr.value: 0 for pr in ProductPriority}
        for p in products:
            priority_counts[p.priority.value] += 1

        # Blocked items
        blocked = [p for p in products if p.stage == ProductStage.BLOCKED]

        # In progress
        in_progress = [p for p in products if p.stage == ProductStage.P3_IN_PROGRESS]

        # Stale items (>7 days in stage)
        stale = [p for p in products if p.days_in_stage > 7 and p.stage not in [ProductStage.P6_DONE, ProductStage.P1_BACKLOG]]

        return {
            "total": len(products),
            "by_stage": stage_counts,
            "by_type": type_counts,
            "by_priority": priority_counts,
            "blocked_count": len(blocked),
            "in_progress_count": len(in_progress),
            "stale_count": len(stale),
            "blocked_items": [p.to_summary() for p in blocked],
            "stale_items": [p.to_summary() for p in stale],
        }

    async def get_roadmap(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get roadmap grouped by target release version"""
        products = await self.list(limit=10000)

        roadmap: Dict[str, List[Dict[str, Any]]] = {}

        for p in products:
            version = p.target_release or "Unscheduled"
            if version not in roadmap:
                roadmap[version] = []
            roadmap[version].append(p.to_summary())

        # Sort versions (semver-like sorting)
        sorted_roadmap = {}
        for version in sorted(roadmap.keys(), key=lambda v: (v == "Unscheduled", v)):
            sorted_roadmap[version] = roadmap[version]

        return sorted_roadmap

    async def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics"""
        products = await self.list(limit=10000)

        completed = [p for p in products if p.stage == ProductStage.P6_DONE]

        # Average time to complete (for completed items)
        avg_completion_days = 0
        if completed:
            total_days = sum(
                (p.completed_at - p.created_at).days
                for p in completed
                if p.completed_at
            )
            avg_completion_days = total_days / len(completed) if completed else 0

        # QA pass rate
        all_qa_results = []
        for p in products:
            all_qa_results.extend(p.qa_results)

        qa_pass_rate = 0
        if all_qa_results:
            passed = sum(1 for r in all_qa_results if r.passed)
            qa_pass_rate = (passed / len(all_qa_results)) * 100

        return {
            "total_products": len(products),
            "completed_products": len(completed),
            "avg_completion_days": round(avg_completion_days, 1),
            "qa_pass_rate": round(qa_pass_rate, 1),
            "total_qa_tests": len(all_qa_results),
        }
