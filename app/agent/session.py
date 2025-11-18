"""Custom session implementation for MongoDB conversations using OpenAI Agents SDK."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import SessionABC
from beanie import PydanticObjectId

from app.conversations.models import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class MongoDBConversationSession(SessionABC):
    """Custom session adapter for MongoDB Conversation storage.

    Implements the SessionABC protocol from openai-agents to integrate with
    our existing MongoDB conversation storage.
    """

    def __init__(
        self,
        user_id: PydanticObjectId,
        conversation_id: Optional[str] = None,
        max_history_messages: int = 20,
    ):
        """Initialize the MongoDB conversation session.

        Args:
            user_id: The ID of the user owning this conversation
            conversation_id: Existing conversation ID or None to create new one
            max_history_messages: Maximum number of messages to retrieve from history
        """
        self.user_id = user_id
        self.conversation_id_str = conversation_id
        self.conversation: Optional[Conversation] = None
        self.max_history_messages = max_history_messages

    async def _ensure_conversation(self) -> Conversation:
        """Ensure conversation exists, creating if needed."""
        if self.conversation:
            return self.conversation

        if self.conversation_id_str:
            # Load existing conversation
            self.conversation = await Conversation.get(self.conversation_id_str)
            if self.conversation and self.conversation.user_id == self.user_id:
                return self.conversation
            logger.warning(
                f"Conversation {self.conversation_id_str} not found or access denied"
            )

        # Create new conversation
        self.conversation = Conversation(
            user_id=self.user_id, title="New Conversation"
        )
        await self.conversation.insert()
        self.conversation_id_str = str(self.conversation.id)
        logger.info(f"Created new conversation {self.conversation_id_str}")

        return self.conversation

    def get_conversation_id(self) -> str:
        """Get the conversation ID (useful for returning to client)."""
        return self.conversation_id_str if self.conversation_id_str else ""

    async def get_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve conversation history in Agents SDK format.

        Args:
            limit: Maximum number of items to retrieve. If None, uses max_history_messages.
                   When specified, returns the latest N items in chronological order.

        Returns:
            List of message dicts compatible with Agents SDK input format
        """
        try:
            # Ensure conversation exists
            conversation = await self._ensure_conversation()

            # Use provided limit or fall back to max_history_messages
            item_limit = limit if limit is not None else self.max_history_messages

            # Fetch messages from MongoDB
            messages = (
                await ConversationMessage.find(
                    ConversationMessage.conversation_id == conversation.id
                )
                .sort(+ConversationMessage.timestamp)  # Chronological order
                .limit(item_limit)
                .to_list()
            )

            # Convert to Agents SDK format
            # Note: We only return role and content. Tool calls are tracked by the SDK internally.
            # We store tool_calls in MongoDB for our own tracking, but don't send them to the API.
            history = []
            for msg in messages:
                message_dict = {"role": msg.role, "content": msg.content}
                history.append(message_dict)

            logger.info(
                f"Retrieved {len(history)} messages from conversation {self.conversation_id_str}"
            )
            return history

        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}", exc_info=True)
            return []

    async def add_items(self, items: List[Any]) -> None:
        """Add new conversation items to MongoDB.

        Args:
            items: List of conversation items from Agents SDK (messages, function calls, etc.)
        """
        try:
            # Ensure conversation exists
            conversation = await self._ensure_conversation()

            saved_count = 0

            logger.info(f"add_items called with {len(items)} items")

            for item in items:
                # Handle different item types from Agents SDK
                if hasattr(item, "type"):
                    item_type = item.type
                elif isinstance(item, dict):
                    item_type = item.get("type")
                else:
                    item_type = None

                # Debug logging
                logger.info(f"Processing item - type: {item_type}, has_role: {hasattr(item, 'role')}, is_dict: {isinstance(item, dict)}, class: {type(item).__name__}")
                if hasattr(item, "__dict__"):
                    logger.info(f"  Item attributes: {list(item.__dict__.keys())}")
                elif isinstance(item, dict):
                    logger.info(f"  Dict keys: {list(item.keys())}")

                # Save text messages (user or assistant)
                # Handle both dict and object formats from Agents SDK
                is_message = item_type == "message" or item_type == "text"
                has_role_attr = hasattr(item, "role") and item.role in ["user", "assistant"]
                has_role_dict = isinstance(item, dict) and item.get("role") in ["user", "assistant"]

                if is_message or has_role_attr or has_role_dict:
                    # Extract role and content from dict or object
                    if isinstance(item, dict):
                        role = item.get("role", "assistant")
                        content_raw = item.get("content", "")

                        # Content might be a list of content blocks or a string
                        if isinstance(content_raw, list):
                            # Extract text from content blocks
                            text_parts = []
                            for block in content_raw:
                                if isinstance(block, dict):
                                    if block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                    # Could be other types like "input_text"
                                    elif "text" in block:
                                        text_parts.append(block.get("text", ""))
                            content = " ".join(text_parts).strip()
                        else:
                            content = content_raw
                    else:
                        role = getattr(item, "role", "assistant")
                        content = getattr(item, "text", None) or getattr(item, "content", "")

                    if content:
                        msg = ConversationMessage(
                            conversation_id=conversation.id,
                            role=role,
                            content=content,
                        )
                        await msg.insert()
                        saved_count += 1

                # Handle function call results by attaching to last assistant message
                elif item_type == "function_call":
                    func_name = getattr(item, "name", None)
                    func_args = getattr(item, "arguments", None)

                    if func_name:
                        # Find the last assistant message and update its tool_calls
                        last_msg = (
                            await ConversationMessage.find(
                                ConversationMessage.conversation_id == conversation.id,
                                ConversationMessage.role == "assistant",
                            )
                            .sort(-ConversationMessage.timestamp)
                            .limit(1)
                            .to_list()
                        )

                        if last_msg:
                            msg = last_msg[0]
                            tool_calls = msg.tool_calls or []
                            tool_calls.append(
                                {
                                    "tool": func_name,
                                    "args": func_args,
                                    "result": {},  # Will be filled by function_call_output
                                }
                            )
                            msg.tool_calls = tool_calls
                            await msg.save()

            # Update conversation metadata
            conversation.message_count += saved_count
            conversation.updated_at = datetime.utcnow()
            conversation.is_active = True
            await conversation.save()

            logger.info(
                f"Saved {saved_count} messages to conversation {self.conversation_id_str}"
            )

        except Exception as e:
            logger.error(f"Error saving conversation items: {e}", exc_info=True)

    async def clear_session(self) -> None:
        """Clear all items for this session."""
        try:
            if not self.conversation:
                await self._ensure_conversation()

            # Delete all messages in this conversation
            await ConversationMessage.find(
                ConversationMessage.conversation_id == self.conversation.id
            ).delete()

            # Reset conversation metadata
            self.conversation.message_count = 0
            self.conversation.updated_at = datetime.utcnow()
            await self.conversation.save()

            logger.info(f"Cleared conversation {self.conversation_id_str}")

        except Exception as e:
            logger.error(f"Error clearing conversation: {e}", exc_info=True)

    async def pop_item(self) -> Optional[Dict[str, Any]]:
        """Remove and return the most recent item from the session.

        Returns:
            The most recent item if it exists, None if the session is empty
        """
        try:
            if not self.conversation:
                await self._ensure_conversation()

            # Find the most recent message
            last_message = (
                await ConversationMessage.find(
                    ConversationMessage.conversation_id == self.conversation.id
                )
                .sort(-ConversationMessage.timestamp)  # Reverse chronological
                .limit(1)
                .to_list()
            )

            if not last_message:
                return None

            msg = last_message[0]

            # Convert to SDK format (only role and content)
            message_dict = {"role": msg.role, "content": msg.content}

            # Delete the message
            await msg.delete()

            # Update conversation metadata
            self.conversation.message_count = max(0, self.conversation.message_count - 1)
            self.conversation.updated_at = datetime.utcnow()
            await self.conversation.save()

            logger.info(
                f"Popped most recent message from conversation {self.conversation_id_str}"
            )
            return message_dict

        except Exception as e:
            logger.error(f"Error popping item from conversation: {e}", exc_info=True)
            return None
