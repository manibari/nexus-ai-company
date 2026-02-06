"""
Product Repository

In-memory repository for Product items (Tracer Bullet version)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.product.models import (
    ProductItem,
    ProductStage,
    ProductPriority,
    ProductType,
    QAResult,
    UATFeedback,
    STAGE_ORDER,
)


class ProductRepository:
    """In-memory repository for product items"""

    def __init__(self):
        self._products: Dict[str, ProductItem] = {}

    async def create(self, product: ProductItem) -> ProductItem:
        """Create a new product item"""
        self._products[product.id] = product
        return product

    async def get(self, product_id: str) -> Optional[ProductItem]:
        """Get a product item by ID"""
        return self._products.get(product_id)

    async def update(self, product: ProductItem) -> ProductItem:
        """Update a product item"""
        self._products[product.id] = product
        return product

    async def delete(self, product_id: str) -> bool:
        """Delete a product item"""
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False

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
        results = list(self._products.values())

        if stage:
            results = [p for p in results if p.stage == stage]

        if product_type:
            results = [p for p in results if p.type == product_type]

        if priority:
            results = [p for p in results if p.priority == priority]

        if assignee:
            results = [p for p in results if p.assignee == assignee]

        if version:
            results = [p for p in results if p.target_release == version]

        # Sort by priority (critical first), then by created_at (oldest first)
        priority_order = {
            ProductPriority.CRITICAL: 0,
            ProductPriority.HIGH: 1,
            ProductPriority.MEDIUM: 2,
            ProductPriority.LOW: 3,
        }
        results.sort(key=lambda p: (priority_order.get(p.priority, 4), p.created_at))

        return results[:limit]

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

    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        products = list(self._products.values())

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

    def get_roadmap(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get roadmap grouped by target release version"""
        products = list(self._products.values())

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

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics"""
        products = list(self._products.values())

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
