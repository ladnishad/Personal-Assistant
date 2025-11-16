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

    SYSTEM_PROMPT = """You are a personal AI life assistant with LONG-TERM MEMORY. Your role is to:
- Help users manage their digital life (emails, calendar, tasks)
- **LEARN about the user and REMEMBER important information**
- Extract meaningful information and create actionable items
- Be proactive with suggestions based on what you know about them
- Execute tasks autonomously when appropriate

**CRITICAL - MEMORY FUNCTIONALITY:**
You MUST actively use the `save_memory` tool to remember:
1. **Relationships**: Family members, friends, colleagues (names, relationships)
   - Example: User mentions "my mom Neeta is calling" → save "User's mother is named Neeta Lad"

2. **Preferences**: Likes, dislikes, habits
   - Example: "I don't drink" → save "User doesn't consume alcohol"

3. **Routines**: Regular patterns, schedules
   - Example: "I work out every morning at 6" → save "User exercises daily at 6 AM"

4. **Facts**: Important information about the user
   - Example: "I'm allergic to peanuts" → save "User has peanut allergy"

5. **Context**: Any situational or background information worth remembering

**WHEN TO SAVE:**
- Whenever the user mentions a family member, friend, or colleague name
- When you learn about likes/dislikes
- When you discover preferences, routines, or habits
- When you learn facts about their life, work, health
- IMMEDIATELY when you encounter new information

**HOW TO RESPOND:**
- After saving important info, acknowledge naturally (e.g., "Got it, I'll remember that your mother is Neeta!")
- Use saved memories to personalize future responses
- Search memory when relevant to provide context-aware help

You have access to tools for emails, tasks, and MEMORY. Use them proactively to provide personalized, contextual assistance."""

    @staticmethod
    async def chat(
        user_id: PydanticObjectId, message: str, use_memory: bool = True
    ) -> Dict[str, Any]:
        """Process user message with agent orchestrator."""
        try:
            # Extract any @remember commands from message
            remember_commands = AgentTools.extract_remember_commands(message)
            clean_msg = AgentTools.clean_message(message)

            # Process @remember commands first
            remember_responses = []
            if remember_commands:
                for mem_content in remember_commands:
                    result = await AgentTools.save_memory(
                        user_id=user_id,
                        content=mem_content,
                        memory_type="note",  # @remember is explicitly user-requested
                        importance=0.9,  # High importance for explicit requests
                    )
                    if result.get("saved"):
                        remember_responses.append(f"✓ Remembered: {mem_content}")

                logger.info(f"Saved {len(remember_commands)} @remember commands for user {user_id}")

            # Build messages
            messages = [
                {"role": "system", "content": AgentService.SYSTEM_PROMPT},
                {"role": "user", "content": clean_msg or message},
            ]

            # Optionally retrieve relevant memories for context
            context_memories = []
            if use_memory:
                context_memories = await AgentTools.search_memory(user_id, clean_msg or message, limit=5)
                if context_memories:
                    context_text = "\n".join(
                        [f"- {m['content']} (type: {m['type']}, importance: {m['importance']:.1f})"
                         for m in context_memories]
                    )
                    messages.insert(
                        1,
                        {
                            "role": "system",
                            "content": f"Relevant memories about this user:\n{context_text}\n\nUse this context to personalize your response.",
                        },
                    )
                    logger.info(f"Retrieved {len(context_memories)} memories for context")

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

            # Prepend @remember confirmations to response if any
            if remember_responses:
                final_message = "\n".join(remember_responses) + "\n\n" + final_message

            return {
                "message": final_message,
                "tools_used": tools_used,
                "context_retrieved": len(context_memories),
                "actions_taken": actions_taken,
                "memories_saved": len(remember_commands) + sum(1 for a in actions_taken if a["tool"] == "save_memory"),
            }

        except Exception as e:
            logger.error(f"Error in agent chat: {e}", exc_info=True)
            return {
                "message": f"I apologize, but I encountered an error: {str(e)}",
                "tools_used": [],
                "context_retrieved": 0,
                "actions_taken": [],
                "memories_saved": 0,
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
            elif tool_name == "save_memory":
                return await AgentTools.save_memory(user_id, **tool_args)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
