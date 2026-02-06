"""
CEO Intake Module

處理 CEO 的非結構化輸入，轉化為可執行的任務和商機。

流程：
1. 接收 CEO 輸入（文字、Email、URL 等）
2. 意圖識別（商機、專案、問題、任務）
3. 實體解析（公司、人名、金額等）
4. 資訊補全（爬蟲、搜尋）
5. 結構化
6. CEO 確認
7. 路由到對應 Agent
"""

from app.intake.models import CEOInput, InputIntent, InputStatus, InputType
from app.intake.processor import IntakeProcessor
from app.intake.enricher import DataEnricher

__all__ = [
    "CEOInput",
    "InputIntent",
    "InputStatus",
    "InputType",
    "IntakeProcessor",
    "DataEnricher",
]
