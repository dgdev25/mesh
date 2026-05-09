"""Communication Simulator Tests Package.

End-to-end simulator scenarios for the Mesh MCP Server. Each test module is
exposed below and registered in ``TEST_REGISTRY`` for dynamic dispatch from
``python -m simulator_tests``.
"""

from .base_test import BaseSimulatorTest
from .test_analyze_validation import AnalyzeValidationTest
from .test_basic_conversation import BasicConversationTest
from .test_chat_simple_validation import ChatSimpleValidationTest
from .test_codereview_validation import CodeReviewValidationTest
from .test_consensus_conversation import TestConsensusConversation
from .test_consensus_three_models import TestConsensusThreeModels
from .test_consensus_workflow_accurate import TestConsensusWorkflowAccurate
from .test_content_validation import ContentValidationTest
from .test_conversation_chain_validation import ConversationChainValidationTest
from .test_cross_tool_comprehensive import CrossToolComprehensiveTest
from .test_cross_tool_continuation import CrossToolContinuationTest
from .test_debug_certain_confidence import DebugCertainConfidenceTest
from .test_debug_validation import DebugValidationTest
from .test_line_number_validation import LineNumberValidationTest
from .test_logs_validation import LogsValidationTest
from .test_model_thinking_config import TestModelThinkingConfig
from .test_openrouter_fallback import OpenRouterFallbackTest
from .test_openrouter_models import OpenRouterModelsTest
from .test_per_tool_deduplication import PerToolDeduplicationTest
from .test_planner_continuation_history import PlannerContinuationHistoryTest
from .test_planner_validation import PlannerValidationTest
from .test_precommitworkflow_validation import PrecommitWorkflowValidationTest
from .test_prompt_size_limit_bug import PromptSizeLimitBugTest
from .test_refactor_validation import RefactorValidationTest
from .test_secaudit_validation import SecauditValidationTest
from .test_testgen_validation import TestGenValidationTest
from .test_thinkdeep_validation import ThinkDeepWorkflowValidationTest
from .test_token_allocation_validation import TokenAllocationValidationTest
from .test_vision_capability import VisionCapabilityTest

TEST_REGISTRY = {
    "basic_conversation": BasicConversationTest,
    "chat_validation": ChatSimpleValidationTest,
    "codereview_validation": CodeReviewValidationTest,
    "content_validation": ContentValidationTest,
    "per_tool_deduplication": PerToolDeduplicationTest,
    "cross_tool_continuation": CrossToolContinuationTest,
    "cross_tool_comprehensive": CrossToolComprehensiveTest,
    "line_number_validation": LineNumberValidationTest,
    "logs_validation": LogsValidationTest,
    "model_thinking_config": TestModelThinkingConfig,
    "openrouter_fallback": OpenRouterFallbackTest,
    "openrouter_models": OpenRouterModelsTest,
    "planner_validation": PlannerValidationTest,
    "planner_continuation_history": PlannerContinuationHistoryTest,
    "precommit_validation": PrecommitWorkflowValidationTest,
    "token_allocation_validation": TokenAllocationValidationTest,
    "testgen_validation": TestGenValidationTest,
    "thinkdeep_validation": ThinkDeepWorkflowValidationTest,
    "refactor_validation": RefactorValidationTest,
    "secaudit_validation": SecauditValidationTest,
    "debug_validation": DebugValidationTest,
    "debug_certain_confidence": DebugCertainConfidenceTest,
    "conversation_chain_validation": ConversationChainValidationTest,
    "vision_capability": VisionCapabilityTest,
    "consensus_conversation": TestConsensusConversation,
    "consensus_workflow_accurate": TestConsensusWorkflowAccurate,
    "consensus_three_models": TestConsensusThreeModels,
    "analyze_validation": AnalyzeValidationTest,
    "prompt_size_limit_bug": PromptSizeLimitBugTest,
}

__all__ = [
    "BaseSimulatorTest",
    "TEST_REGISTRY",
    *(cls.__name__ for cls in TEST_REGISTRY.values()),
]
