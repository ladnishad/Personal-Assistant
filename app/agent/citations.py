"""Citation processing utilities for OpenAI Agents SDK web search results."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_citations(result: Any) -> List[Dict[str, Any]]:
    """Extract URL citations from OpenAI Agents SDK result.

    Args:
        result: The result object from Runner.run()

    Returns:
        List of citation dictionaries with url, title, start_index, end_index, and text
    """
    citations = []

    try:
        # Iterate through new_items to find message_output_item
        for item in reversed(result.new_items):
            if hasattr(item, "type") and item.type == "message_output_item":
                # Get raw_item content
                raw_item = getattr(item, "raw_item", None)
                if not raw_item:
                    continue

                content_list = getattr(raw_item, "content", [])

                for content in content_list:
                    # Check if content has annotations
                    if not hasattr(content, "annotations"):
                        continue

                    # Get the text for context
                    content_text = getattr(content, "text", None)
                    text_value = getattr(content_text, "value", "") if content_text else ""

                    # Extract URL citations
                    for ann in content.annotations:
                        if getattr(ann, "type", None) == "url_citation":
                            citation = {
                                "url": getattr(ann, "url", ""),
                                "title": getattr(ann, "title", ""),
                                "start_index": getattr(ann, "start_index", 0),
                                "end_index": getattr(ann, "end_index", 0),
                                "text": text_value,
                            }
                            citations.append(citation)
                            logger.debug(f"Extracted citation: {citation['title']} -> {citation['url']}")

    except Exception as e:
        logger.error(f"Error extracting citations: {e}", exc_info=True)

    return citations


def build_citation_mapping(text: str, citations: List[Dict[str, Any]]) -> Dict[str, str]:
    """Build a mapping of citation placeholders to markdown links.

    Args:
        text: The text containing citation placeholders
        citations: List of citation dictionaries from extract_citations()

    Returns:
        Dictionary mapping citation placeholder -> markdown link
    """
    mapping = {}

    # Find all citation placeholders in the text (e.g., citeturn3search1, cite123, etc.)
    # Common patterns: cite, citeturn, citation followed by numbers/text
    citation_pattern = r'cite[a-z]*\d+[a-z]*\d*'

    placeholders = re.findall(citation_pattern, text, re.IGNORECASE)

    # Create mapping from placeholders to citations
    # Since we don't have a direct mapping, we'll try to match based on position or frequency
    for placeholder in set(placeholders):
        # For now, create a simple sequential mapping
        # This can be improved if we find a pattern in how placeholders correlate to citations
        pass

    # Alternative approach: replace all citation placeholders with footnote-style links
    # Build citation list at the end
    for i, citation in enumerate(citations, 1):
        # Create markdown link
        if citation["url"] and citation["title"]:
            md_link = f"[{citation['title']}]({citation['url']})"
            # We'll need to figure out which placeholder maps to which citation
            # For now, store by index
            mapping[f"cite_{i}"] = md_link

    return mapping


def replace_citations_with_links(text: str, citations: List[Dict[str, Any]]) -> str:
    """Replace citation placeholders with dual format: inline links + sources section.

    Args:
        text: The text containing citation placeholders (e.g., citeturn3search1)
        citations: List of citation dictionaries from extract_citations()

    Returns:
        Text with inline markdown links and a sources section at the bottom
    """
    if not citations:
        return text

    # More comprehensive pattern to catch all citation variations
    # Matches: cite, citeturn, citation followed by any combination of letters and numbers
    citation_pattern = r'\bcite[a-z0-9]*(?:turn[a-z0-9]*)*(?:search[a-z0-9]*)*\b'

    # Find all citation placeholders
    placeholders = []
    for match in re.finditer(citation_pattern, text, re.IGNORECASE):
        placeholders.append({
            'text': match.group(),
            'start': match.start(),
            'end': match.end()
        })

    if not placeholders:
        # No citations to replace, just return original text
        return text

    # Sort placeholders by position (reverse order to maintain indices)
    placeholders.sort(key=lambda x: x['start'], reverse=True)

    # Create mapping of citations with improved titles
    citation_mapping = {}
    for i, citation in enumerate(citations, 1):
        # Clean up title - use domain as fallback if title is empty
        title = citation.get("title", "").strip()
        url = citation.get("url", "").strip()

        if not title and url:
            # Extract domain name as fallback title
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain_match:
                title = domain_match.group(1).replace('.com', '').replace('.in', '').title()

        citation_mapping[i] = {
            "title": title or f"Source {i}",
            "url": url
        }

    # Build a mapping of unique placeholders to citations
    # Sort unique placeholders for consistent mapping
    unique_placeholders = sorted(list(set([p['text'].lower() for p in placeholders])))
    placeholder_to_citation = {}

    for i, unique_placeholder in enumerate(unique_placeholders):
        # Map each unique placeholder to a citation (cycling if needed)
        citation_num = (i % len(citations)) + 1
        placeholder_to_citation[unique_placeholder] = citation_num

    # Replace each placeholder with inline link
    result_text = text
    used_citations = set()

    for placeholder in placeholders:
        citation_num = placeholder_to_citation[placeholder['text'].lower()]
        used_citations.add(citation_num)

        citation = citation_mapping[citation_num]

        # Create inline markdown link
        if citation["url"] and citation["title"]:
            inline_link = f"[{citation['title']}]({citation['url']})"
        else:
            inline_link = ""  # Remove placeholder if no valid citation

        # Replace the placeholder with inline link
        result_text = result_text[:placeholder['start']] + inline_link + result_text[placeholder['end']:]

    # Build sources section with all used citations
    if used_citations:
        sources_section = "\n\n---\n\n### Sources\n"
        for num in sorted(used_citations):
            citation = citation_mapping[num]
            if citation["url"]:
                sources_section += f"\n{num}. [{citation['title']}]({citation['url']})"

        return result_text + sources_section

    return result_text


def process_content_with_citations(content: str, citations: List[Dict[str, Any]]) -> str:
    """Process content to replace citation placeholders with links.

    This is a wrapper function that handles the full citation replacement flow.

    Args:
        content: The content string (potentially from update_task_content)
        citations: List of citations from extract_citations()

    Returns:
        Processed content with citations replaced
    """
    if not citations:
        return content

    return replace_citations_with_links(content, citations)
