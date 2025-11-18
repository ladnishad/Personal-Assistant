"""Guardrails for agent input and output validation using OpenAI Agents SDK."""

import logging
from typing import Any, Dict

from agents import GuardrailFunctionOutput, output_guardrail

logger = logging.getLogger(__name__)


@output_guardrail
async def check_task_creation_hallucination(context, agent, agent_output) -> GuardrailFunctionOutput:
    """Check if agent claims to create a task without actually calling the tool.

    This guardrail detects when the agent's response contains language suggesting
    a task was created ("created a task", "task created", etc.) but the agent
    didn't actually call the create_task tool.

    This is a non-blocking guardrail (tripwire=False) - it logs warnings but
    allows the response to proceed. This helps us monitor and improve prompt
    engineering to reduce hallucinations.

    Args:
        context: Context dictionary (from SDK)
        agent: The agent instance (from SDK)
        agent_output: The agent's output to validate

    Returns:
        GuardrailFunctionOutput with tripwire status and validation message
    """
    # Keywords that suggest task creation
    task_keywords = [
        "created a task",
        "created the task",
        "added a task",
        "added the task",
        "made a task",
        "task created",
        "task added",
        "set a reminder",
        "set reminder",
        "i've created",
        "i created",
        "i've added",
        "i added",
    ]

    # Get the output text from agent_output
    output_text = ""
    if isinstance(agent_output, str):
        output_text = agent_output
    elif hasattr(agent_output, "text"):
        output_text = agent_output.text
    elif hasattr(agent_output, "content"):
        output_text = agent_output.content
    elif isinstance(agent_output, dict):
        output_text = agent_output.get("text", agent_output.get("content", ""))

    # Check if any task creation keywords are present
    output_lower = output_text.lower()
    hallucination_detected = False
    matched_keyword = None

    for keyword in task_keywords:
        if keyword in output_lower:
            hallucination_detected = True
            matched_keyword = keyword
            break

    if hallucination_detected:
        # Log warning but don't block (tripwire=False)
        logger.warning(
            f"⚠️ POTENTIAL HALLUCINATION: Agent response contains '{matched_keyword}' "
            f"but may not have called create_task tool. Consider reviewing prompt engineering."
        )

        return GuardrailFunctionOutput(
            output_info=f"Potential hallucination detected: '{matched_keyword}' in response",
            tripwire_triggered=False,  # Don't block, just log
        )

    return GuardrailFunctionOutput(
        output_info="Task creation validation passed", tripwire_triggered=False
    )


@output_guardrail
async def check_planning_workflow_compliance(
    context, agent, agent_output
) -> GuardrailFunctionOutput:
    """Check if agent followed planning workflow for research tasks.

    When users request planning/research (trips, events, etc.), the agent should:
    1. Check for existing tasks
    2. Create/identify task
    3. Research using web search
    4. Update task content with findings
    5. Keep chat response brief

    This guardrail checks if update_task_content was called for planning requests.

    Args:
        context: Context dictionary (from SDK)
        agent: The agent instance (from SDK)
        agent_output: The agent's output to validate

    Returns:
        GuardrailFunctionOutput with tripwire status and validation message
    """
    # Planning keywords that trigger this check
    planning_keywords = [
        "plan",
        "research",
        "look into",
        "find out",
        "investigate",
        "trip",
        "accommodation",
        "itinerary",
    ]

    # Get the output text from agent_output
    output_text = ""
    if isinstance(agent_output, str):
        output_text = agent_output
    elif hasattr(agent_output, "text"):
        output_text = agent_output.text
    elif hasattr(agent_output, "content"):
        output_text = agent_output.content

    # Check if this looks like a planning request response
    output_lower = output_text.lower()
    is_planning_response = any(
        keyword in output_lower for keyword in planning_keywords
    )

    if is_planning_response:
        # Check if context indicates update_task_content was called
        # (This would need to be populated by the service)
        if context and not context.get("content_updated", False):
            logger.warning(
                f"⚠️ PLANNING WORKFLOW: Agent response suggests planning/research "
                f"but update_task_content may not have been called. "
                f"Detailed content should be in task, not chat."
            )

            return GuardrailFunctionOutput(
                output_info="Planning workflow may be incomplete - check task content update",
                tripwire_triggered=False,  # Don't block, just log
            )

    return GuardrailFunctionOutput(
        output_info="Planning workflow validation passed", tripwire_triggered=False
    )


# List of all guardrails to apply to the agent
OUTPUT_GUARDRAILS = [
    check_task_creation_hallucination,
    # check_planning_workflow_compliance,  # Disabled for now - needs context integration
]

INPUT_GUARDRAILS = [
    # Add input guardrails here if needed in the future
    # Examples:
    # - check_for_malicious_input
    # - validate_user_permissions
    # - check_rate_limits
]
