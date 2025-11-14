"""Agent orchestrator service."""

import json
import logging
from typing import Any, Dict, List

from beanie import PydanticObjectId
from openai import AsyncOpenAI

from app.agent.tools import AgentTools
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


class AgentService:
    """AI Agent orchestrator using LLM with function calling."""

    SYSTEM_PROMPT = """You are a personal AI life assistant. Your role is to help users manage their digital life by:
- Understanding their emails, calendar, and tasks
- Extracting important information and creating actionable items
- Maintaining long-term memory of preferences and context
- Being proactive with suggestions and reminders
- Executing tasks autonomously when appropriate

You have access to tools to search emails, manage tasks, and retrieve memories. Use these tools to provide helpful, contextual responses.

Be conversational, helpful, and proactive. When you identify actionable items from the conversation, create tasks automatically."""

    @staticmethod
    async def chat(
        user_id: PydanticObjectId, message: str, use_memory: bool = True
    ) -> Dict[str, Any]:
        """Process user message with agent orchestrator."""
        try:
            # Build messages
            messages = [
                {"role": "system", "content": AgentService.SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ]

            # Optionally retrieve relevant memories for context
            context_memories = []
            if use_memory:
                context_memories = await AgentTools.search_memory(user_id, message, limit=3)
                if context_memories:
                    context_text = "\n".join(
                        [f"- {m['content']}" for m in context_memories]
                    )
                    messages.insert(
                        1,
                        {
                            "role": "system",
                            "content": f"Relevant context from memory:\n{context_text}",
                        },
                    )

            # Get tool definitions
            tools = AgentTools.get_tool_definitions()

            # Call OpenAI with function calling
            response = await openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=settings.openai_temperature,
            )

            # Process response
            assistant_message = response.choices[0].message
            tools_used = []
            actions_taken = []

            # Handle tool calls
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Agent calling tool: {tool_name} with args: {tool_args}")

                    # Execute tool
                    tool_result = await AgentService._execute_tool(
                        user_id, tool_name, tool_args
                    )

                    tools_used.append(tool_name)
                    actions_taken.append(
                        {"tool": tool_name, "args": tool_args, "result": tool_result}
                    )

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call.model_dump()],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result),
                        }
                    )

                # Get final response after tool execution
                final_response = await openai_client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    temperature=settings.openai_temperature,
                )

                final_message = final_response.choices[0].message.content
            else:
                final_message = assistant_message.content

            return {
                "message": final_message,
                "tools_used": tools_used,
                "context_retrieved": len(context_memories),
                "actions_taken": actions_taken,
            }

        except Exception as e:
            logger.error(f"Error in agent chat: {e}", exc_info=True)
            return {
                "message": f"I apologize, but I encountered an error: {str(e)}",
                "tools_used": [],
                "context_retrieved": 0,
                "actions_taken": [],
            }

    @staticmethod
    async def _execute_tool(
        user_id: PydanticObjectId, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        """Execute a tool function."""
        try:
            if tool_name == "search_emails":
                return await AgentTools.search_emails(user_id, **tool_args)
            elif tool_name == "create_task":
                return await AgentTools.create_task(user_id, **tool_args)
            elif tool_name == "get_tasks":
                return await AgentTools.get_tasks(user_id, **tool_args)
            elif tool_name == "search_memory":
                return await AgentTools.search_memory(user_id, **tool_args)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
