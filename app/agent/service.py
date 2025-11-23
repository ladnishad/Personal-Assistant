"""Agent orchestrator service using OpenAI Agents SDK."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Agent, ModelSettings, Runner
from beanie import PydanticObjectId
from openai.types.responses import ResponseTextDeltaEvent

from app.agent.calendar_agent import create_calendar_management_agent
from app.agent.citations import extract_citations, process_content_with_citations
from app.agent.computer_agent import create_computer_control_agent
from app.agent.computer_tools import (
    enable_screenshot_streaming,
    disable_screenshot_streaming,
    get_screenshot_captures,
    clear_screenshot_captures,
    set_user_context,
)
from app.agent.guardrails import OUTPUT_GUARDRAILS
from app.agent.package_agent import create_package_tracking_agent
from app.agent.package_tools import set_package_user_id
from app.agent.session import MongoDBConversationSession
from app.agent.tools import (
    AGENT_TOOLS,
    _save_memory_internal,
    _search_memory_internal,
    clean_message,
    extract_remember_commands,
    set_current_citations,
    set_current_user_id,
)
from app.auth.models import User
from app.config import settings
from app.conversations.models import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class AgentService:
    """AI Agent orchestrator using OpenAI Agents SDK."""

    SYSTEM_PROMPT = """You are a personal AI life assistant with LONG-TERM MEMORY. Your role is to:
- Help users manage their digital life (emails, calendar, tasks, packages)
- **LEARN about the user and REMEMBER important information**
- Extract meaningful information and create actionable items
- Be proactive with suggestions based on what you know about them
- Execute tasks autonomously when appropriate
- **Help users work on specific tasks by researching and documenting information**
- **Track and monitor package deliveries automatically**

**CRITICAL - TASK CREATION:**
You MUST use the `create_task` tool when users ask you to:
- Create, add, make, or set up a task/todo/reminder
- Remember to do something later
- Track an action item
- Plan something (trips, events, projects)

**IMPORTANT**: You must ACTUALLY CALL the `create_task` function. NEVER just SAY you created a task without calling the tool!

Examples of when to use `create_task`:
- User: "Create a task to review the report" → CALL create_task(title="Review the report")
- User: "Remind me to call Sarah tomorrow" → CALL create_task(title="Call Sarah", due_date="tomorrow")
- User: "Add a todo to buy groceries" → CALL create_task(title="Buy groceries")
- User: "I need to finish the presentation by Friday" → CALL create_task(title="Finish presentation", due_date="Friday")
- User: "Plan our trip to Austin" → CALL create_task(title="Plan Austin trip")

**CRITICAL - PLANNING WORKFLOW:**
When users ask you to plan, research, or work on something complex (trips, events, projects), you MUST follow this workflow:

1. **Check for Existing Task**: FIRST call `get_tasks` to see if there's already a related task
   - If user is continuing a conversation about a task they just created, UPDATE that task
   - If user mentions "this task", "the task", "it", they're referring to an existing task
   - Only create a NEW task if there's no related task found
2. **Create or Identify Task**:
   - If NEW: Call `create_task` with a descriptive title and detailed description
   - If EXISTING: Use the task_id from `get_tasks` results
3. **Research**: Use web search extensively to gather comprehensive information (accommodations, activities, prices, reviews, links)
4. **Document in Task**: Call `update_task_content` to save ALL detailed research as beautifully formatted markdown to the task
5. **Brief Chat Response**: Keep your chat message SHORT - just acknowledge completion

**MANDATORY RULES:**
- ✅ ALWAYS call `get_tasks` first to check for existing related tasks
- ✅ UPDATE existing tasks rather than creating duplicates
- ✅ ALL research details go in the task content (via `update_task_content`)
- ✅ Chat message must be brief (1-2 sentences max)
- ✅ Use web search for current prices, availability, reviews
- ✅ Format task content with headers (##, ###), lists, links, prices
- ❌ NEVER create duplicate tasks when a related one exists
- ❌ NEVER put detailed research in the chat message
- ❌ NEVER skip calling `update_task_content` after research

**Example 1 - Updating Existing Task:**
Conversation context:
- User: "Add a task to plan our anniversary"
- You: Created task "Plan 1st anniversary celebration"
- User: "We'd like to go to Fredericksburg, TX from Dec 20-23 with a $3000 budget. Can you look into accommodations and plan it all?"

Your actions:
1. `get_tasks(status="todo", limit=10)` → Find "Plan 1st anniversary celebration" task
2. Web search: "Fredericksburg TX hotels December prices", "things to do Fredericksburg TX", "romantic restaurants Fredericksburg TX"
3. `update_task_content(task_id="691a939f...", content="## Fredericksburg Anniversary Trip\n\n### Accommodations\n- **Inn on Barons Creek** - $250/night, downtown [link]\n...")`
4. Chat message: "I've added accommodation options, activities, and a budget breakdown to your anniversary trip task!"

**Example 2 - Creating New Task:**
User: "Plan a business trip to Austin next month"

Your actions:
1. `get_tasks(status="todo")` → No related tasks found
2. `create_task(title="Plan business trip to Austin")`
3. Web search and research...
4. `update_task_content(...)`
5. Chat message: "I've created a task with hotel options and meeting venue recommendations!"

**IMPORTANT**: When you create or update a task, keep your response message concise and friendly. The system will automatically show a beautiful clickable card linking to the task, so you don't need to tell users "click here" or explain how to view it.

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

**EMAIL MANAGEMENT:**
You have comprehensive email management capabilities. Use them to help users with their inbox:

**Core Email Tools:**
- `get_recent_emails` - Get recent emails with filters (category, read status, date)
- `search_emails` - Search emails by query (sender, subject, content)
- `get_email_details` - Read full email with classification and extracted entities
- `get_emails_by_category` - Filter by type (promotional, package_shipping, financial, travel, etc.)
- `find_emails_from_sender` - Find all emails from specific person/company
- `get_unread_emails` - Get unread emails prioritized by importance
- `get_email_thread` - Get entire conversation thread
- `get_related_emails` - Find related emails (same order/tracking/merchant)
- `mark_emails_read` - Mark emails as read/unread
- `star_email` - Star important emails
- `sync_emails` - Trigger email sync from Gmail
- `scan_emails_for_packages` - Automatically detect packages from emails

**When Presenting Emails to Users:**
- **Summarize intelligently** based on what user asked - never dump raw email content
- **Use emojis** for visual clarity (📧 general, 📦 packages, 💰 financial, ✈️ travel, 🎉 promotional, etc.)
- **Extract key information**: tracking numbers, amounts, dates, action items, deadlines
- **Focus on actionable content**: what needs attention, what requires response
- **Provide context**: use extracted entities and classification to understand email purpose
- **Be concise**: 1-3 sentences per email unless user asks for details

**Examples of Email Interactions:**

User: "What emails did I get today?"
→ Call `get_recent_emails(from_date="today", limit=20)`
→ Summarize: "📧 You got 12 emails today: 📦 Amazon order shipped, 💰 Bank statement available, 🎉 3 promotional emails, and 8 others. Anything specific you'd like to see?"

User: "Show me financial emails"
→ Call `get_emails_by_category(category="financial", limit=10)`
→ Summarize each with amounts, banks, due dates extracted from entities

User: "Read that Amazon email"
→ Call `search_emails(query="Amazon", limit=5)` or `get_email_details(email_id="...")`
→ Provide detailed summary with key points, tracking numbers, order details

User: "Any unread emails?"
→ Call `get_unread_emails(limit=20)`
→ Prioritize by category importance, highlight packages/financial/personal first

User: "Check my emails for packages"
→ Call `scan_emails_for_packages(days_back=7)` to auto-detect and create package records
→ Report: "📦 Found 2 packages! Amazon order arriving tomorrow, Best Buy shipped today"

User: "Find all emails from my boss"
→ Call `find_emails_from_sender(sender_email="boss@company.com")`
→ Summarize recent emails with key topics

**Email Intelligence:**
- All emails are automatically classified into categories (promotional, package_shipping, financial, personal, etc.)
- Entities are extracted (tracking numbers, amounts, dates, merchants, order numbers)
- Use this intelligence to provide smart summaries and context

**PACKAGE TRACKING:**
When users ask about packages, deliveries, or tracking:
- You can use `scan_emails_for_packages` to automatically detect packages from emails
- For detailed package tracking, transfer to the Package Tracking Specialist agent
- The specialist can track shipments, provide delivery updates, and analyze email context

**CALENDAR MANAGEMENT:**
Transfer to Calendar Management Specialist when users ask about:
- Their schedule or calendar ("What's on my calendar?", "What do I have today/tomorrow?")
- Availability ("Am I free at 2pm?", "Do I have anything on Monday?")
- Finding events ("When is my dentist appointment?", "Find my meeting with John")
- Creating events ("Schedule a meeting...", "Add to my calendar...", "Block time for...")
- Upcoming commitments ("What's my week looking like?", "What's coming up?")

The Calendar Management Specialist can:
- Sync calendars from Google Calendar
- View events (today, tomorrow, this week, upcoming)
- Search for specific events by keyword
- Check availability and detect scheduling conflicts
- Create new calendar events
- Provide intelligent scheduling suggestions

Examples when to transfer to Calendar Management:
→ "What's on my calendar today?"
→ "Am I free tomorrow at 2pm?"
→ "Find my dentist appointment"
→ "Schedule a team meeting next Monday at 10am"
→ "What does my week look like?"
→ "Do I have any conflicts on Friday?"

**COMPUTER CONTROL & AUTOMATION:**
⚠️ CRITICAL: If the user mentions ANY of these, you MUST transfer to Computer Control Specialist:
- "go to" any website (e.g., "go to google.com", "go to amazon")
- "navigate to" any URL or site
- "open" any website or browser
- "search google" or "search on [website]"
- ANY request about current prices, deals, or product availability
- ANY request to compare products or check reviews on actual sites

DO NOT use your web search tool for these - transfer to Computer Control Specialist immediately.

Transfer to Computer Control Specialist when users:
- Ask about product prices, deals, or costs ("how much", "price", "cost", "deals")
- Check product availability or stock ("available", "in stock", "can I get")
- Want to compare products or services ("compare", "vs", "better", "which one")
- Need current/real-time information from websites
- Book reservations (restaurants, hotels, events)
- Order items online (e-commerce)
- Fill out web forms
- Search websites and gather information
- Perform any task requiring visual interface interaction

The Computer Control Specialist can:
- Browse e-commerce sites to check current prices and availability
- Compare products side-by-side across multiple websites
- Navigate websites and web applications
- Click buttons, fill forms, type text
- Take screenshots to understand visual state
- Execute multi-step workflows autonomously
- Handle complex web-based tasks

Examples when to transfer to Computer Control:
→ "What are the best headphones under $100" (needs real browsing for current prices)
→ "Is the Sony WH-CH720N available at Best Buy"
→ "Compare prices for wireless headphones"
→ "Book a table at Resy for tomorrow at 7pm"
→ "Search Amazon for wireless headphones under $100"
→ "Fill out this form on the website"
→ "Order pizza from Domino's"
→ "Find available hotel rooms in Austin for next week"

You have access to tools for emails, tasks, web search, MEMORY, package tracking, calendar management, and computer control. Use them proactively to provide personalized, contextual assistance."""

    @staticmethod
    async def _ensure_user_profile_memory(user: User) -> None:
        """Ensure basic user profile is saved in long-term memory."""
        from app.memory.models import Memory, MemoryType

        # Check if we have a profile memory for this user
        existing_profile = await Memory.find_one(
            Memory.user_id == user.id,
            Memory.memory_type == MemoryType.FACT,
            Memory.category == "profile",
        )

        if not existing_profile and user.full_name:
            # Set user context and save initial profile memory
            set_current_user_id(user.id)
            # Create initial profile memory using the internal function
            await _save_memory_internal(
                content=f"User's name is {user.full_name}",
                memory_type="fact",
                category="profile",
                importance=0.9,
            )
            logger.info(f"Created initial profile memory for user {user.id}")

    @staticmethod
    def _get_system_instructions(user: User, context_memories: List[Dict]) -> str:
        """Build system instructions with user profile and relevant memories.

        Args:
            user: The User object
            context_memories: List of relevant memories for this conversation

        Returns:
            Complete system instructions string
        """
        system_context = f"""{AgentService.SYSTEM_PROMPT}

**USER PROFILE:**
- Name: {user.full_name or 'Not provided'}
- Email: {user.email}
- Timezone: {user.timezone}
- Account created: {user.created_at.strftime('%Y-%m-%d')}

You already know this basic information about the user, so don't ask for it."""

        # Add relevant memories if available
        if context_memories:
            context_text = "\n".join(
                [
                    f"- {m['content']} (type: {m['type']}, importance: {m['importance']:.1f})"
                    for m in context_memories
                ]
            )
            system_context += (
                f"\n\n**RELEVANT MEMORIES:**\n{context_text}\n\nUse this context to personalize your response."
            )

        return system_context

    @staticmethod
    async def chat(
        user: User,
        message: str,
        use_memory: bool = True,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        stream_screenshots: bool = False,
    ) -> Dict[str, Any]:
        """Process user message with agent orchestrator using Agents SDK.

        Args:
            user: The user making the request
            message: User's message
            use_memory: Whether to use long-term memory
            conversation_id: Existing conversation ID or None for new
            task_id: Task ID to link this conversation to
            conversation_history: Optional conversation history (for compatibility)
            stream_screenshots: Whether to stream screenshots from computer control agent

        Returns:
            Dictionary with response message, conversation_id, and metadata
        """
        try:
            user_id = user.id

            # Ensure user profile is in long-term memory
            await AgentService._ensure_user_profile_memory(user)

            # Set user context for tools
            set_current_user_id(user_id)

            # Enable screenshot streaming if requested
            if stream_screenshots:
                enable_screenshot_streaming()
                logger.info("Screenshot streaming enabled for this request")
            else:
                disable_screenshot_streaming()

            # Set user context for computer tools (for confirmations)
            set_user_context(str(user_id), conversation_id)

            # Extract any @remember commands from message
            remember_commands = extract_remember_commands(message)
            clean_msg = clean_message(message)

            # Process @remember commands first
            remember_responses = []
            if remember_commands:
                for mem_content in remember_commands:
                    result = await _save_memory_internal(
                        content=mem_content,
                        memory_type="note",  # @remember is explicitly user-requested
                        importance=0.9,  # High importance for explicit requests
                    )
                    if result.get("saved"):
                        remember_responses.append(f"✓ Remembered: {mem_content}")

                logger.info(
                    f"Saved {len(remember_commands)} @remember commands for user {user_id}"
                )

            # Retrieve relevant memories for context
            context_memories = []
            if use_memory:
                context_memories = await _search_memory_internal(
                    clean_msg or message, limit=5
                )
                if context_memories:
                    logger.info(f"Retrieved {len(context_memories)} memories for context")

            # Build system instructions
            instructions = AgentService._get_system_instructions(user, context_memories)

            # Set user context for package tools (using contextvars for async-safe context)
            # This must be set before creating agents so tools can access user_id
            set_package_user_id(user_id)

            # Create specialized agents (will use contextvar user_id in tools)
            package_agent = create_package_tracking_agent()
            computer_agent = create_computer_control_agent()
            calendar_agent = create_calendar_management_agent()

            # Optimize model settings for faster responses
            # For GPT-5 models, use low reasoning effort for speed
            model_settings = None
            if settings.openai_model.startswith("gpt-5"):
                model_settings = ModelSettings(
                    reasoning_effort="low",  # Faster responses
                    verbosity="low",  # Less verbose reasoning
                )

            # Create agent with guardrails and handoffs
            agent = Agent(
                name="LifeOS Assistant",
                instructions=instructions,
                tools=AGENT_TOOLS,
                model=settings.openai_model,
                model_settings=model_settings,
                output_guardrails=OUTPUT_GUARDRAILS,
                handoffs=[package_agent, computer_agent, calendar_agent],  # Add all specialized agents
            )

            # Create session for conversation history
            session = MongoDBConversationSession(
                user_id=user_id,
                conversation_id=conversation_id,
                max_history_messages=20,
            )

            # Run agent with Agents SDK
            logger.info(f"Running agent with model: {settings.openai_model}")
            result = await Runner.run(
                agent,
                clean_msg or message,
                session=session,
            )

            # Get final message
            final_message = result.final_output

            # Collect screenshots if streaming was enabled
            screenshots = []
            if stream_screenshots:
                screenshots = get_screenshot_captures()
                logger.info(f"Collected {len(screenshots)} screenshots from execution")
                # Clear captures for next request
                clear_screenshot_captures()

            # Extract citations from web search results
            citations = extract_citations(result)
            if citations:
                logger.info(f"Extracted {len(citations)} citations from web search")
                # Set citations in context for tools to access
                set_current_citations(citations)
                # Process final message to replace citation placeholders
                final_message = process_content_with_citations(final_message, citations)

            # Prepend @remember confirmations to response if any
            if remember_responses:
                final_message = "\n".join(remember_responses) + "\n\n" + final_message

            # Extract tools used and actions taken from result
            tools_used = []
            actions_taken = []

            # Parse new_items to extract tool calls
            for item in result.new_items:
                # Check for function calls
                if hasattr(item, "type") and item.type == "function_call":
                    tool_name = getattr(item, "name", None)
                    if tool_name:
                        tools_used.append(tool_name)

                # Check for function call outputs
                if hasattr(item, "type") and item.type == "function_call_output":
                    call_id = getattr(item, "call_id", None)
                    output = getattr(item, "output", None)

                    # Try to find matching function call
                    for other_item in result.new_items:
                        if (
                            hasattr(other_item, "type")
                            and other_item.type == "function_call"
                            and getattr(other_item, "call_id", None) == call_id
                        ):
                            tool_name = getattr(other_item, "name", None)
                            tool_args = getattr(other_item, "arguments", {})

                            if tool_name:
                                actions_taken.append(
                                    {
                                        "tool": tool_name,
                                        "args": tool_args,
                                        "result": output,
                                    }
                                )
                            break

            # Detect task references from actions taken
            task_reference = None
            task_created = None
            content_updated = False

            for action in actions_taken:
                if action["tool"] == "create_task" and isinstance(
                    action.get("result"), dict
                ):
                    if action["result"].get("created"):
                        task_created = {
                            "task_id": action["result"]["id"],
                            "task_title": action["result"]["title"],
                            "action": "created",
                        }
                elif action["tool"] == "update_task_content" and isinstance(
                    action.get("result"), dict
                ):
                    if action["result"].get("content_updated"):
                        content_updated = True
                        task_reference = {
                            "task_id": action["result"]["id"],
                            "task_title": action["result"]["title"],
                            "action": "updated",
                        }

            # Post-process task content with citations if needed
            if citations and (task_reference or task_created):
                try:
                    from app.tasks.service import TaskService
                    from app.tasks.schemas import TaskUpdate

                    # Get task ID from either task_reference or task_created
                    task_id = None
                    if task_reference and task_reference.get("task_id"):
                        task_id = task_reference["task_id"]
                    elif task_created and task_created.get("task_id"):
                        task_id = task_created["task_id"]

                    if task_id:
                        task = await TaskService.get_task(task_id, user_id)

                        if task and task.content:
                            # Check if content has citation placeholders (more robust check)
                            import re
                            citation_pattern = r'\bcite[a-z]*\d+[a-z]*\d*\b'
                            if re.search(citation_pattern, task.content, re.IGNORECASE):
                                logger.info(f"Post-processing task {task_id} with {len(citations)} citations")
                                processed_content = process_content_with_citations(
                                    task.content, citations
                                )

                                # Only update if content actually changed
                                if processed_content != task.content:
                                    await TaskService.update_task(
                                        task_id, user_id, TaskUpdate(content=processed_content)
                                    )
                                    logger.info(
                                        f"Successfully replaced citations in task {task_id} with dual format"
                                    )
                                else:
                                    logger.info(f"No citation changes needed for task {task_id}")
                except Exception as e:
                    logger.error(f"Error post-processing task citations: {e}", exc_info=True)

            # If task was created but content wasn't updated, still reference the created task
            if not task_reference and task_created:
                task_reference = task_created

                # Log warning if this looks like a planning request without content update
                planning_keywords = [
                    "plan",
                    "research",
                    "look into",
                    "find out",
                    "investigate",
                    "trip",
                    "accommodation",
                ]
                if any(keyword in message.lower() for keyword in planning_keywords):
                    logger.warning(
                        f"⚠️ Planning request detected but update_task_content was not called. "
                        f"Task '{task_created['task_title']}' may be missing detailed content."
                    )

            # Get conversation ID from session
            conversation_id_result = session.get_conversation_id()

            # Link conversation to task if task_id was provided (for task-specific chats)
            if task_id and conversation_id_result:
                try:
                    from beanie import PydanticObjectId
                    from app.conversations.models import Conversation

                    conv = await Conversation.get(conversation_id_result)
                    if conv and not conv.task_id:  # Only set if not already set
                        conv.task_id = PydanticObjectId(task_id)
                        await conv.save()
                        logger.info(
                            f"Linked conversation {conversation_id_result} to task {task_id}"
                        )
                except Exception as e:
                    logger.error(f"Error linking conversation to task from task_id: {e}", exc_info=True)

            # Also link conversation to task if a task was created or updated
            if task_reference and task_reference.get("task_id"):
                try:
                    from beanie import PydanticObjectId
                    from app.conversations.models import Conversation

                    conv = await Conversation.get(conversation_id_result)
                    if conv and not conv.task_id:  # Only set if not already set
                        conv.task_id = PydanticObjectId(task_reference["task_id"])
                        await conv.save()
                        logger.info(
                            f"Linked conversation {conversation_id_result} to task {task_reference['task_id']}"
                        )
                except Exception as e:
                    logger.error(f"Error linking conversation to task from task_reference: {e}", exc_info=True)

            return {
                "message": final_message,
                "conversation_id": conversation_id_result,
                "tools_used": tools_used,
                "context_retrieved": len(context_memories),
                "actions_taken": actions_taken,
                "memories_saved": len(remember_commands)
                + sum(1 for a in actions_taken if a["tool"] == "save_memory"),
                "task_reference": task_reference,
                "screenshots": screenshots,
            }

        except Exception as e:
            logger.error(f"Error in agent chat: {e}", exc_info=True)
            return {
                "message": f"I apologize, but I encountered an error: {str(e)}",
                "conversation_id": conversation_id
                if "conversation_id" in locals()
                else None,
                "tools_used": [],
                "context_retrieved": 0,
                "actions_taken": [],
                "memories_saved": 0,
                "task_reference": None,
                "screenshots": [],
            }
        finally:
            # Clear citations context to avoid leaking between requests
            set_current_citations([])

    @staticmethod
    async def chat_streamed(
        user: User,
        message: str,
        use_memory: bool = True,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        stream_screenshots: bool = False,
    ):
        """Process user message with streaming using Agents SDK.

        Yields Server-Sent Events (SSE) formatted strings for real-time updates.

        Args:
            user: The user making the request
            message: User's message
            use_memory: Whether to use long-term memory
            conversation_id: Existing conversation ID or None for new
            task_id: Task ID to link this conversation to
            stream_screenshots: Whether to stream screenshots from computer control

        Yields:
            SSE-formatted event strings (event: <type>\ndata: <json>\n\n)
        """
        import json
        import time

        try:
            start_time = time.time()
            user_id = user.id

            # Ensure user profile is in long-term memory
            await AgentService._ensure_user_profile_memory(user)
            logger.info(f"⏱️  Profile check: {time.time() - start_time:.2f}s")

            # Set user context for tools
            set_current_user_id(user_id)

            # Set user context for computer tools (for confirmations and screenshots)
            set_user_context(str(user_id), conversation_id)

            # Enable screenshot streaming if requested
            if stream_screenshots:
                enable_screenshot_streaming()
                logger.info("Screenshot streaming enabled for this conversation")

            # Extract any @remember commands from message
            remember_commands = extract_remember_commands(message)
            clean_msg = clean_message(message)

            # Process @remember commands first
            remember_responses = []
            if remember_commands:
                for mem_content in remember_commands:
                    result = await _save_memory_internal(
                        content=mem_content,
                        memory_type="note",
                        importance=0.9,
                    )
                    if result.get("saved"):
                        remember_responses.append(f"✓ Remembered: {mem_content}")

                logger.info(f"Saved {len(remember_commands)} @remember commands for user {user_id}")

            # Retrieve relevant memories for context
            context_memories = []
            if use_memory:
                mem_start = time.time()
                context_memories = await _search_memory_internal(clean_msg or message, limit=5)
                logger.info(f"⏱️  Memory search: {time.time() - mem_start:.2f}s")
                if context_memories:
                    logger.info(f"Retrieved {len(context_memories)} memories for context")

            # Build system instructions
            instructions = AgentService._get_system_instructions(user, context_memories)

            # Force Computer Control transfer for obvious browser requests
            message_lower = message.lower()
            browser_triggers = [
                "go to", "navigate to", "open google", "open amazon", "open browser",
                "search google", "check price", "check availability", "current price",
                "browse to", "visit website", "go on", "pull up", "show me on"
            ]

            if any(trigger in message_lower for trigger in browser_triggers):
                instructions += "\n\n⚠️ MANDATORY: The user is explicitly asking for browser interaction. You MUST immediately transfer to Computer Control Specialist. Do NOT use web search."

            # Set user context for package tools
            set_package_user_id(user_id)

            # Create specialized agents
            package_agent = create_package_tracking_agent()
            computer_agent = create_computer_control_agent()
            calendar_agent = create_calendar_management_agent()

            # Optimize model settings for faster responses
            # For GPT-5 models, use low reasoning effort for speed
            model_settings = None
            if settings.openai_model.startswith("gpt-5"):
                model_settings = ModelSettings(
                    reasoning_effort="low",  # Faster responses
                    verbosity="low",  # Less verbose reasoning
                )

            # Create agent with guardrails and handoffs
            agent = Agent(
                name="LifeOS Assistant",
                instructions=instructions,
                tools=AGENT_TOOLS,
                model=settings.openai_model,
                model_settings=model_settings,
                output_guardrails=OUTPUT_GUARDRAILS,
                handoffs=[package_agent, computer_agent, calendar_agent],  # Include all specialized agents
            )

            # Create session for conversation history
            session = MongoDBConversationSession(
                user_id=user_id,
                conversation_id=conversation_id,
                max_history_messages=20,
            )

            # Emit initial status and flush to establish connection
            initial_event = f"event: agent_status\ndata: {json.dumps({'status': 'thinking', 'message': 'Processing your request...'})}\n\n"
            logger.info(f"🚀 Emitting initial status event")
            yield initial_event

            # Run agent with streaming
            agent_start = time.time()
            logger.info(f"Running streamed agent with model: {settings.openai_model}")
            result = Runner.run_streamed(
                agent,
                clean_msg or message,
                session=session,
            )
            logger.info(f"⏱️  Agent stream initialized: {time.time() - agent_start:.2f}s")
            logger.info(f"🔄 Starting to consume stream events...")

            # Track state for processing
            tools_used = []
            actions_taken = []
            message_parts = []
            current_tool_calls = {}  # Map call_id to tool info

            # Process streaming events
            async for event in result.stream_events():
                logger.info(f"🔥 Stream event type: {event.type}")

                # Handle raw response events (token-by-token LLM output)
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    delta_text = event.data.delta
                    message_parts.append(delta_text)
                    logger.info(f"📨 Emitting delta: {delta_text[:50]}")

                    # Emit message delta
                    yield f"event: message_delta\ndata: {json.dumps({'delta': delta_text})}\n\n"

                # Handle run item events (completed items like tool calls, messages)
                elif event.type == "run_item_stream_event":
                    item = event.item
                    item_type = item.type
                    logger.info(f"🔧 Run item event - item type: {item_type}")

                    # Tool call item
                    if item_type == "tool_call_item":
                        tool_name = getattr(item, "name", None)
                        tool_args = getattr(item, "arguments", {})
                        call_id = getattr(item, "id", None)

                        if tool_name:
                            tools_used.append(tool_name)
                            if call_id:
                                current_tool_calls[call_id] = {
                                    "name": tool_name,
                                    "args": tool_args,
                                }

                            # Emit tool call event
                            tool_event = {
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "call_id": call_id or tool_name,
                            }
                            yield f"event: tool_call\ndata: {json.dumps(tool_event)}\n\n"

                            # Emit status update
                            friendly_name = tool_name.replace("_", " ").title()
                            yield f"event: agent_status\ndata: {json.dumps({'status': 'calling_tool', 'message': f'Using {friendly_name}...'})}\n\n"

                    # Tool call output item
                    elif item_type == "tool_call_output_item":
                        call_id = getattr(item, "call_id", None)
                        output = getattr(item, "output", None)

                        # Try to find matching tool call
                        tool_name = None
                        tool_args = {}
                        if call_id and call_id in current_tool_calls:
                            tool_info = current_tool_calls[call_id]
                            tool_name = tool_info["name"]
                            tool_args = tool_info["args"]

                        if tool_name:
                            actions_taken.append(
                                {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": output,
                                }
                            )

                            # Emit tool result event
                            result_event = {
                                "tool_name": tool_name,
                                "call_id": call_id,
                                "result": str(output)[:200] if output else None,
                            }
                            yield f"event: tool_result\ndata: {json.dumps(result_event)}\n\n"

                            # Check for screenshots if streaming is enabled
                            if stream_screenshots:
                                screenshots = get_screenshot_captures()
                                for screenshot in screenshots:
                                    screenshot_event = {
                                        "screenshot": screenshot["screenshot"],
                                        "width": screenshot["width"],
                                        "height": screenshot["height"],
                                        "timestamp": screenshot["timestamp"],
                                        "action_context": screenshot.get("action_context"),
                                    }
                                    yield f"event: screenshot_capture\ndata: {json.dumps(screenshot_event)}\n\n"
                                    logger.info(f"📸 Emitted screenshot: {screenshot.get('action_context', 'unknown')}")
                                # Clear screenshots after emitting to avoid duplicates
                                clear_screenshot_captures()

                            # Emit status update
                            yield f"event: agent_status\ndata: {json.dumps({'status': 'processing', 'message': 'Processing results...'})}\n\n"

                    # Message output item (final message)
                    elif item_type == "message_output_item":
                        # Message is complete, handled at the end
                        pass

                # Handle agent update events (handoffs)
                elif event.type == "agent_updated_stream_event":
                    # Use new_agent as per documentation
                    agent_name = event.new_agent.name
                    yield f"event: agent_status\ndata: {json.dumps({'status': 'handoff', 'message': f'Transferred to {agent_name}'})}\n\n"

            # Stream complete
            logger.info(f"✅ Stream events loop complete")
            logger.info(f"⏱️  Total streaming time: {time.time() - agent_start:.2f}s")

            # Get final message from result
            final_message = result.final_output
            logger.info(f"📝 Final message length: {len(final_message)} chars")

            # Extract citations from web search results
            citations = extract_citations(result)
            if citations:
                logger.info(f"Extracted {len(citations)} citations from web search")
                set_current_citations(citations)
                final_message = process_content_with_citations(final_message, citations)

            # Prepend @remember confirmations to response if any
            if remember_responses:
                final_message = "\n".join(remember_responses) + "\n\n" + final_message

            # Emit complete message
            yield f"event: message_complete\ndata: {json.dumps({'message': final_message})}\n\n"

            # Detect task references from actions taken
            task_reference = None
            task_created = None

            for action in actions_taken:
                if action["tool"] == "create_task" and isinstance(action.get("result"), dict):
                    if action["result"].get("created"):
                        task_created = {
                            "task_id": action["result"]["id"],
                            "task_title": action["result"]["title"],
                            "action": "created",
                        }
                elif action["tool"] == "update_task_content" and isinstance(
                    action.get("result"), dict
                ):
                    if action["result"].get("content_updated"):
                        task_reference = {
                            "task_id": action["result"]["id"],
                            "task_title": action["result"]["title"],
                            "action": "updated",
                        }

            # Post-process task content with citations if needed
            if citations and (task_reference or task_created):
                try:
                    from app.tasks.service import TaskService
                    from app.tasks.schemas import TaskUpdate

                    # Get task ID from either task_reference or task_created
                    task_id = None
                    if task_reference and task_reference.get("task_id"):
                        task_id = task_reference["task_id"]
                    elif task_created and task_created.get("task_id"):
                        task_id = task_created["task_id"]

                    if task_id:
                        task = await TaskService.get_task(task_id, user_id)

                        if task and task.content:
                            # Check if content has citation placeholders (more robust check)
                            import re
                            citation_pattern = r'\bcite[a-z]*\d+[a-z]*\d*\b'
                            if re.search(citation_pattern, task.content, re.IGNORECASE):
                                logger.info(f"Post-processing task {task_id} with {len(citations)} citations")
                                processed_content = process_content_with_citations(
                                    task.content, citations
                                )

                                # Only update if content actually changed
                                if processed_content != task.content:
                                    await TaskService.update_task(
                                        task_id, user_id, TaskUpdate(content=processed_content)
                                    )
                                    logger.info(
                                        f"Successfully replaced citations in task {task_id} with dual format"
                                    )
                                else:
                                    logger.info(f"No citation changes needed for task {task_id}")
                except Exception as e:
                    logger.error(f"Error post-processing task citations: {e}", exc_info=True)

            # If task was created but content wasn't updated, still reference the created task
            if not task_reference and task_created:
                task_reference = task_created

            # Get conversation ID from session
            conversation_id_result = session.get_conversation_id()

            # Link conversation to task if task_id was provided (for task-specific chats)
            if task_id and conversation_id_result:
                try:
                    from beanie import PydanticObjectId
                    from app.conversations.models import Conversation

                    conv = await Conversation.get(conversation_id_result)
                    if conv and not conv.task_id:  # Only set if not already set
                        conv.task_id = PydanticObjectId(task_id)
                        await conv.save()
                        logger.info(
                            f"Linked conversation {conversation_id_result} to task {task_id}"
                        )
                except Exception as e:
                    logger.error(f"Error linking conversation to task from task_id: {e}", exc_info=True)

            # Also link conversation to task if a task was created or updated
            if task_reference and task_reference.get("task_id"):
                try:
                    from beanie import PydanticObjectId
                    from app.conversations.models import Conversation

                    conv = await Conversation.get(conversation_id_result)
                    if conv and not conv.task_id:  # Only set if not already set
                        conv.task_id = PydanticObjectId(task_reference["task_id"])
                        await conv.save()
                        logger.info(
                            f"Linked conversation {conversation_id_result} to task {task_reference['task_id']}"
                        )
                except Exception as e:
                    logger.error(f"Error linking conversation to task from task_reference: {e}", exc_info=True)

            # Emit final done event with metadata
            done_data = {
                "conversation_id": conversation_id_result,
                "tools_used": tools_used,
                "context_retrieved": len(context_memories),
                "actions_taken": actions_taken,
                "memories_saved": len(remember_commands)
                + sum(1 for a in actions_taken if a["tool"] == "save_memory"),
                "task_reference": task_reference,
            }
            logger.info(f"🏁 Emitting done event")
            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

            logger.info(f"⏱️  Total request time: {time.time() - start_time:.2f}s")
            logger.info(f"✅ Streaming complete!")

        except Exception as e:
            logger.error(f"Error in streamed agent chat: {e}", exc_info=True)
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

        finally:
            # Clear citations context to avoid leaking between requests
            set_current_citations([])
