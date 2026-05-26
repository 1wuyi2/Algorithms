"""AI-assisted scheduling advisor exports."""

from .ai_assistant import (
    AIScheduleAssistant,
    AdvisorRiskLevel,
    QAAnswer,
    ScheduleInsight,
    ScheduleSuggestion,
    SuggestionPriority,
    analyze_schedule,
)
from .edu_system_sync import (
    EduSystemClient,
    EduSystemConfig,
    EduSystemType,
    SyncResult,
    generate_sync_report,
)
from .llm_client import (
    LLMClient,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    create_default_client,
)

__all__ = [
    # AI助手
    "AIScheduleAssistant",
    "AdvisorRiskLevel",
    "QAAnswer",
    "ScheduleInsight",
    "ScheduleSuggestion",
    "SuggestionPriority",
    "analyze_schedule",
    
    # LLM客户端
    "LLMClient",
    "LLMConfig",
    "LLMProvider",
    "LLMResponse",
    "create_default_client",
    
    # 教务系统同步
    "EduSystemClient",
    "EduSystemConfig",
    "EduSystemType",
    "SyncResult",
    "generate_sync_report",
]