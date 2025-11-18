# OpenAI Agents SDK - Comprehensive Guide

## Table of Contents
1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Core Concepts](#core-concepts)
4. [Agents](#agents)
5. [Runner](#runner)
6. [Sessions](#sessions)
7. [Results](#results)
8. [Tools](#tools)
9. [Handoffs](#handoffs)
10. [Guardrails](#guardrails)
11. [Streaming](#streaming)
12. [Tracing](#tracing)
13. [Models](#models)
14. [Model Context Protocol (MCP)](#model-context-protocol-mcp)
15. [Multi-Agent Patterns](#multi-agent-patterns)
16. [Examples & Use Cases](#examples--use-cases)
17. [Best Practices](#best-practices)

---

## Overview

The OpenAI Agents SDK is a lightweight, Python-first framework for building agentic AI applications. It provides essential primitives for creating sophisticated AI agents with minimal boilerplate.

### Key Primitives
- **Agents**: Core building blocks configured with LLMs, instructions, and tools
- **Handoffs**: Mechanism for agents to delegate tasks to specialized agents
- **Guardrails**: Input/output validation to prevent misuse
- **Sessions**: Automatic conversation history management

### Key Features
- Built-in agent execution loop
- Automatic conversation history management
- Function tools with automatic schema generation
- Comprehensive tracing capabilities
- Support for streaming responses
- Multi-agent orchestration
- Context management via dependency injection

---

## Installation & Setup

### Installation
```bash
pip install openai-agents
```

### Basic Setup
```bash
# Create project structure
mkdir my_project
cd my_project
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the SDK
pip install openai-agents

# Set API key
export OPENAI_API_KEY=sk-...  # On Windows: set OPENAI_API_KEY=sk-...
```

### Hello World
```python
from agents import Agent, Runner

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant"
)

result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
print(result.final_output)
```

---

## Core Concepts

### Agent Execution Flow
1. User provides input to an agent
2. Agent processes input with LLM
3. LLM may call tools or hand off to other agents
4. Process continues until final output is generated
5. Result is returned with conversation history

### Key Components Interaction
- **Agent** defines behavior and capabilities
- **Runner** executes the agent with provided input
- **Session** maintains conversation history across runs
- **Tools** extend agent capabilities
- **Guardrails** validate inputs and outputs
- **Tracing** records execution for debugging

---

## Agents

Agents are the core building blocks of AI applications in this SDK. Each agent is configured with an LLM, instructions, and optional tools.

### Basic Agent Configuration

```python
from agents import Agent

agent = Agent(
    name="Weather Agent",           # Unique identifier
    instructions="Retrieve weather details.",  # System prompt
    model="gpt-4.1",                # LLM to use
    tools=[get_weather],            # Available functions
)
```

### Agent Properties

| Property | Description | Type |
|----------|-------------|------|
| `name` | Unique identifier for the agent | `str` |
| `instructions` | System prompt/developer message | `str` or `callable` |
| `model` | Specifies which LLM to use | `str` or `Model` |
| `tools` | Functions the agent can utilize | `list[Tool]` |
| `context` | Dependency-injection for shared state | `dict` |
| `output_type` | Defines structured output format | `type` (Pydantic model) |
| `handoffs` | Other agents this agent can delegate to | `list[Agent]` |
| `input_guardrails` | Validation for user input | `list[Guardrail]` |
| `output_guardrails` | Validation for agent output | `list[Guardrail]` |
| `model_settings` | Additional model configuration | `ModelSettings` |

### Dynamic Instructions

Instructions can be a function that generates prompts dynamically:

```python
def get_instructions(context):
    user_name = context.get("user_name", "User")
    return f"You are a helpful assistant for {user_name}."

agent = Agent(
    name="Dynamic Agent",
    instructions=get_instructions,
    context={"user_name": "Alice"}
)
```

### Structured Output

Use Pydantic models to enforce structured responses:

```python
from pydantic import BaseModel

class WeatherResponse(BaseModel):
    temperature: float
    conditions: str
    humidity: int

agent = Agent(
    name="Weather Agent",
    instructions="Provide weather information",
    output_type=WeatherResponse
)
```

### Tool Use Behaviors

Control how agents handle tool results:

```python
from agents import ModelSettings

# Default: LLM processes tool results
agent = Agent(
    name="Default Agent",
    tools=[my_tool],
    # tool_use_behavior="run_llm_again" is default
)

# Alternative: Use first tool output as final response
agent = Agent(
    name="Direct Tool Agent",
    tools=[my_tool],
    model_settings=ModelSettings(
        tool_choice="my_tool"  # Force specific tool
    )
)
```

### Lifecycle Hooks

Agents support hooks for custom behavior at different stages:
- Pre-execution processing
- Post-execution processing
- Error handling

### Cloning Agents

Create variations of agents without duplicating configuration:

```python
base_agent = Agent(name="Base", instructions="Help users")
specialized_agent = base_agent.clone(
    name="Specialized",
    tools=[specialized_tool]
)
```

---

## Runner

The Runner is responsible for executing agents. It provides both synchronous and asynchronous execution methods.

### Synchronous Execution

```python
from agents import Runner, Agent

agent = Agent(name="Assistant", instructions="Be helpful")
result = Runner.run_sync(agent, "Hello!")
print(result.final_output)
```

### Asynchronous Execution

```python
import asyncio
from agents import Runner, Agent

async def main():
    agent = Agent(name="Assistant", instructions="Be helpful")
    result = await Runner.run(agent, "Hello!")
    print(result.final_output)

asyncio.run(main())
```

### Streaming Execution

```python
async def main():
    agent = Agent(name="Assistant", instructions="Be helpful")
    result = await Runner.run_streamed(agent, "Tell me a story")

    async for event in result.stream_events():
        # Process streaming events
        print(event)

asyncio.run(main())
```

### Run Configuration

Pass additional configuration to runs:

```python
from agents import RunConfig

result = await Runner.run(
    agent,
    "Hello!",
    config=RunConfig(
        tracing_disabled=True,
        trace_include_sensitive_data=False,
        max_turns=10
    )
)
```

---

## Sessions

Sessions automatically manage conversation history across multiple agent interactions, eliminating the need for manual memory management.

### How Sessions Work

1. **Before Run**: Automatically retrieve and prepend conversation history
2. **After Run**: Automatically store new conversation items
3. **Result**: Context is preserved across interactions

### SQLite Sessions (Default)

```python
from agents import SQLiteSession, Runner

# In-memory session
session = SQLiteSession("conversation_123")

# File-based session
session = SQLiteSession("conversation_123", db_path="./conversations.db")

result = await Runner.run(
    agent,
    "What city is the Golden Gate Bridge in?",
    session=session
)

# Next interaction uses same session
result = await Runner.run(
    agent,
    "What's the population?",  # Knows we're talking about San Francisco
    session=session
)
```

### SQLAlchemy Sessions (Production)

For production deployments with PostgreSQL, MySQL, etc.:

```python
from agents import SQLAlchemySession
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:password@localhost/dbname")
session = SQLAlchemySession("conversation_456", engine=engine)

result = await Runner.run(agent, "Hello!", session=session)
```

### OpenAI Conversations API Sessions

Leverage OpenAI's hosted conversation storage:

```python
from agents import OpenAIConversationsSession

session = OpenAIConversationsSession("conversation_789")
result = await Runner.run(agent, "Hello!", session=session)
```

### Encrypted Sessions

For sensitive conversations:

```python
from agents import EncryptedSession

session = EncryptedSession(
    "conversation_secure",
    encryption_key="your-encryption-key"
)
result = await Runner.run(agent, "Sensitive data", session=session)
```

### Session Best Practices

- Use meaningful session IDs (e.g., user IDs, conversation IDs)
- Choose appropriate persistence strategy for your use case
- Consider encryption for sensitive conversations
- Support multiple concurrent sessions per user if needed
- Implement session cleanup/archival for old conversations

### Custom Sessions

Implement custom session types by following the `SessionABC` protocol:

```python
from agents import SessionABC

class CustomSession(SessionABC):
    async def get_history(self):
        # Retrieve conversation history
        pass

    async def save_items(self, items):
        # Store new conversation items
        pass
```

---

## Results

Results contain the output and metadata from agent runs.

### Result Types

1. **`RunResult`**: Returned by `run()` or `run_sync()`
2. **`RunResultStreaming`**: Returned by `run_streamed()`
3. Both inherit from **`RunResultBase`**

### Key Result Properties

```python
result = await Runner.run(agent, "Hello!")

# Final agent output (string or custom type)
print(result.final_output)

# The last agent that executed
print(result.last_agent.name)

# New items generated during run
for item in result.new_items:
    print(item)

# Convert result to input for next run
next_input = result.to_input_list()

# Guardrail results
print(result.input_guardrail_results)
print(result.output_guardrail_results)

# Raw LLM responses
print(result.raw_responses)

# Original input
print(result.input)
```

### New Items Types

Items generated during execution:
- **`MessageOutputItem`**: Text messages from agent
- **`HandoffCallItem`**: Handoff was initiated
- **`HandoffOutputItem`**: Result from handoff
- **`ToolCallItem`**: Tool was called
- **`ToolCallOutputItem`**: Tool result
- **`ReasoningItem`**: Reasoning content (for reasoning models)

### Chaining Agent Runs

```python
# First run
result1 = await Runner.run(agent1, "Calculate 15 + 27")

# Use result as input to next agent
result2 = await Runner.run(
    agent2,
    result1.to_input_list()
)
```

---

## Tools

Tools extend agent capabilities by allowing them to call functions, access APIs, and perform actions.

### Tool Types

1. **Function Tools**: Python functions callable by agents
2. **Hosted Tools**: OpenAI-provided tools (web search, code interpreter, etc.)
3. **Agents as Tools**: Use other agents as callable tools

### Function Tools

#### Basic Function Tool

```python
from agents import function_tool

@function_tool
def get_weather(location: str) -> str:
    """Fetch the weather for a given location."""
    # Implementation
    return f"Weather in {location}: Sunny, 72°F"

agent = Agent(
    name="Weather Assistant",
    instructions="Help with weather queries",
    tools=[get_weather]
)
```

#### Function Tool with Complex Types

```python
from pydantic import BaseModel
from agents import function_tool

class Location(BaseModel):
    city: str
    country: str

@function_tool
async def fetch_weather(location: Location) -> str:
    """Fetch the weather for a given location."""
    return f"Weather in {location.city}, {location.country}: Sunny"
```

#### Automatic Schema Generation

The SDK automatically:
- Extracts tool name from function name
- Uses docstring as tool description
- Generates input schema from type hints

#### Manual Tool Creation

```python
from agents import FunctionTool

def my_function(param: str) -> str:
    return f"Result: {param}"

tool = FunctionTool(
    name="custom_name",
    description="Custom description",
    fn=my_function,
    # Optional: custom error handling
)
```

### Hosted Tools

OpenAI-provided tools that run on their servers:

```python
from agents import Agent, WebSearchTool, CodeInterpreterTool

agent = Agent(
    name="Research Agent",
    tools=[
        WebSearchTool(),           # Web search capability
        CodeInterpreterTool(),     # Python code execution
        # Also available:
        # FileSearchTool()
        # ImageGenerationTool()
        # ComputerUseTool()
    ]
)
```

### Agents as Tools

Use agents as callable tools within other agents:

```python
from agents import Agent

# Create specialized agent
math_agent = Agent(
    name="Math Expert",
    instructions="Solve mathematical problems"
)

# Use it as a tool in another agent
general_agent = Agent(
    name="General Assistant",
    instructions="Help with various tasks",
    tools=[math_agent]  # Agent can now "call" math_agent
)
```

### Conditional Tool Enabling

Enable/disable tools dynamically:

```python
@function_tool
def premium_feature(user_id: str) -> str:
    """Premium-only feature."""
    return "Premium result"

def should_enable_premium(context):
    return context.get("is_premium", False)

agent = Agent(
    name="Assistant",
    tools=[
        (premium_feature, should_enable_premium)  # Conditionally enabled
    ],
    context={"is_premium": True}
)
```

### Tool Error Handling

```python
from agents import FunctionTool, ToolError

@function_tool
def risky_operation() -> str:
    """May fail."""
    try:
        # Operation
        return "Success"
    except Exception as e:
        raise ToolError(f"Operation failed: {e}")
```

### Returning Images/Files from Tools

```python
@function_tool
def generate_chart() -> dict:
    """Generate a chart image."""
    return {
        "type": "image",
        "url": "https://example.com/chart.png"
    }
```

---

## Handoffs

Handoffs allow agents to delegate tasks to specialized agents, enabling complex multi-agent workflows.

### What are Handoffs?

Handoffs are represented as tools to the LLM with names like `transfer_to_<agent_name>`. When the LLM decides to use this "tool," control transfers to the specified agent.

### When to Use Handoffs

- Different agents specialize in distinct domains
- Complex workflows requiring multiple expertise areas
- Customer support with specialized agents (billing, refunds, FAQs)
- Routing/triage patterns

### Basic Handoff

```python
from agents import Agent

# Create specialized agents
billing_agent = Agent(
    name="Billing Agent",
    instructions="Handle billing inquiries"
)

refund_agent = Agent(
    name="Refund Agent",
    instructions="Process refund requests"
)

# Create triage agent with handoffs
triage_agent = Agent(
    name="Triage Agent",
    instructions="Route customer to appropriate specialist. Always transfer to the right agent.",
    handoffs=[billing_agent, refund_agent]
)
```

### Custom Handoff Configuration

```python
from agents import handoff

custom_handoff = handoff(
    refund_agent,
    tool_name="transfer_to_refunds",  # Custom tool name
    tool_description="Transfer to refund specialist for refund-related issues",
    # Optional: filter conversation history during transfer
)

triage_agent = Agent(
    name="Triage Agent",
    handoffs=[billing_agent, custom_handoff]
)
```

### Handoffs with Input Data

```python
from pydantic import BaseModel

class HandoffData(BaseModel):
    priority: str
    summary: str

custom_handoff = handoff(
    specialist_agent,
    input_type=HandoffData
)
```

### Filtering Conversation History

Control what conversation history is transferred:

```python
def filter_history(items):
    # Only include last 5 messages
    return items[-5:]

custom_handoff = handoff(
    agent,
    conversation_history_filter=filter_history
)
```

### Dynamic Handoff Conditions

```python
def should_allow_handoff(context):
    return context.get("user_tier") == "premium"

conditional_handoff = handoff(
    premium_agent,
    enabled=should_allow_handoff
)
```

### Handoff Best Practices

1. **Clear Instructions**: Include handoff instructions in agent prompts
   ```python
   instructions = """
   Route users based on their query:
   - Billing questions → transfer to Billing Agent
   - Refund requests → transfer to Refund Agent
   - General questions → answer directly
   """
   ```

2. **Use Handoff Descriptions**: Help the LLM understand when to handoff
   ```python
   Agent(
       name="Specialist",
       handoff_description="Expert in technical troubleshooting"
   )
   ```

3. **Recommended Prompt Prefix**:
   ```
   "You can transfer to specialized agents. Always transfer when appropriate."
   ```

---

## Guardrails

Guardrails enable validation and checks on user inputs and agent outputs to prevent misuse and ensure quality.

### Guardrail Types

1. **Input Guardrails**: Run on initial user input (before agent processing)
2. **Output Guardrails**: Run on final agent output (after agent processing)

### Input Guardrail Example

```python
from agents import input_guardrail, GuardrailFunctionOutput, Agent

@input_guardrail
async def check_homework_request(input_data) -> GuardrailFunctionOutput:
    """Check if user is requesting math homework help."""

    # Analyze input
    is_homework = "homework" in input_data.lower()

    return GuardrailFunctionOutput(
        output="Detected homework request" if is_homework else "OK",
        tripwire=is_homework  # Halt execution if True
    )

agent = Agent(
    name="Math Tutor",
    instructions="Help with math, but not homework",
    input_guardrails=[check_homework_request]
)
```

### Output Guardrail Example

```python
from agents import output_guardrail, GuardrailFunctionOutput

@output_guardrail
async def verify_no_math_content(output_data) -> GuardrailFunctionOutput:
    """Verify response doesn't contain mathematical solutions."""

    # Check for mathematical symbols
    has_math = any(symbol in output_data for symbol in ['+', '-', '=', '∫'])

    return GuardrailFunctionOutput(
        output="Mathematical content detected" if has_math else "OK",
        tripwire=has_math
    )

agent = Agent(
    name="Non-Math Assistant",
    instructions="Help with tasks except math",
    output_guardrails=[verify_no_math_content]
)
```

### Tripwires

Tripwires immediately halt agent execution when triggered:

```python
# When tripwire=True is returned:
# - Raises InputGuardrailTripwireTriggered (for input guardrails)
# - Raises OutputGuardrailTripwireTriggered (for output guardrails)
# - Agent execution stops immediately

try:
    result = await Runner.run(agent, "Help with my homework")
except InputGuardrailTripwireTriggered as e:
    print("Input blocked by guardrail:", e)
```

### Guardrail Execution Rules

- **Input guardrails**: Only run if the agent is the **first** in a sequence
- **Output guardrails**: Only run if the agent is the **last** in a sequence

### Use Cases

- Content moderation
- PII detection and redaction
- Compliance verification
- Request validation
- Response quality checks
- Resource consumption optimization

---

## Streaming

Streaming enables real-time updates during agent execution, providing visibility into the agent's progress.

### Streaming Modes

1. **Raw Response Events**: Token-by-token LLM output
2. **Run Item Events**: Higher-level agent workflow events
3. **Agent Events**: Agent state updates

### Basic Streaming

```python
from agents import Runner

async def stream_example():
    agent = Agent(name="Assistant", instructions="Be helpful")
    result = await Runner.run_streamed(agent, "Tell me a story")

    async for event in result.stream_events():
        print(event)
```

### Streaming Event Types

```python
from agents import (
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    AgentUpdatedStreamEvent
)

async def handle_stream():
    result = await Runner.run_streamed(agent, "Query")

    async for event in result.stream_events():
        if isinstance(event, RawResponsesStreamEvent):
            # Token-level updates
            print(event.token, end='', flush=True)

        elif isinstance(event, RunItemStreamEvent):
            # Workflow events: message, tool call, etc.
            print(f"Event: {event.item_type}")

        elif isinstance(event, AgentUpdatedStreamEvent):
            # Agent state changes
            print(f"Agent: {event.agent.name}")
```

### Token-by-Token Streaming

```python
async def stream_tokens():
    result = await Runner.run_streamed(agent, "Write a poem")

    async for event in result.stream_events():
        if isinstance(event, RawResponsesStreamEvent):
            if hasattr(event, 'delta'):
                print(event.delta, end='', flush=True)
```

### Tracking Tool Calls

```python
async def track_tools():
    result = await Runner.run_streamed(agent, "What's the weather?")

    async for event in result.stream_events():
        if isinstance(event, RunItemStreamEvent):
            if event.item_type == "tool_call":
                print(f"Calling tool: {event.tool_name}")
            elif event.item_type == "tool_output":
                print(f"Tool result: {event.output}")
```

### Use Cases

- Real-time UI updates
- Progress indicators
- Showing partial responses
- Debugging agent behavior
- User engagement during long operations

---

## Tracing

Tracing automatically records comprehensive events during agent execution for debugging and analysis.

### What Tracing Captures

- Entire Runner execution flow
- Agent runs and state transitions
- LLM generations and token usage
- Function tool calls and results
- Guardrail executions
- Handoffs between agents
- Audio inputs/outputs (for voice agents)
- Custom events

### Tracing Components

- **Traces**: Represent end-to-end workflow operations
- **Spans**: Represent time-bounded operations with start/end timestamps

### Enabling Tracing

Tracing is **enabled by default**. View traces in the OpenAI Traces dashboard.

### Disabling Tracing

#### Globally (via environment variable)
```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

#### For a Single Run
```python
from agents import RunConfig

result = await Runner.run(
    agent,
    "Hello",
    config=RunConfig(tracing_disabled=True)
)
```

### Sensitive Data Handling

Exclude sensitive data from traces:

```python
result = await Runner.run(
    agent,
    "Process credit card 1234-5678-9012-3456",
    config=RunConfig(trace_include_sensitive_data=False)
)
```

### Custom Trace Processors

Add custom trace processing:

```python
from agents import add_trace_processor, TraceProcessor

class CustomTraceProcessor(TraceProcessor):
    def process_trace(self, trace):
        # Custom trace handling
        print(f"Trace: {trace.id}")
        # Send to your analytics system
        pass

add_trace_processor(CustomTraceProcessor())
```

### Replace Default Processors

```python
from agents import set_trace_processors

set_trace_processors([CustomTraceProcessor()])
```

### Zero Data Retention (ZDR) Policy

**Important**: For organizations using OpenAI's APIs under a Zero Data Retention (ZDR) policy, tracing is **unavailable** (as traces are stored by OpenAI).

### Use Cases

- Debugging agent behavior
- Performance analysis
- Token usage tracking
- Audit logs
- Quality assurance
- Cost optimization

---

## Models

The SDK supports various OpenAI models and can integrate with non-OpenAI models via LiteLLM.

### Supported OpenAI Models

#### Recommended Interface
```python
# Uses OpenAI Responses API (recommended)
agent = Agent(
    name="Assistant",
    model="gpt-4.1"  # Default model
)
```

#### Alternative Interface
```python
# Uses Chat Completions API
from agents import OpenAIChatCompletionsModel

agent = Agent(
    name="Assistant",
    model=OpenAIChatCompletionsModel("gpt-4.1")
)
```

### Default Model

- Current default: **`gpt-4.1`**
- Offers strong balance of predictability and low latency
- Can override via environment variable:
  ```bash
  export OPENAI_DEFAULT_MODEL=gpt-4-turbo
  ```

### GPT-5 Models

```python
# GPT-5 variants
agent = Agent(model="gpt-5")        # Full model
agent = Agent(model="gpt-5-mini")   # Smaller, faster
agent = Agent(model="gpt-5-nano")   # Smallest, fastest

# GPT-5 has reasoning.effort and verbosity set to "low" by default
# Customize if needed:
from agents import ModelSettings

agent = Agent(
    model="gpt-5",
    model_settings=ModelSettings(
        reasoning_effort="high",
        verbosity="high"
    )
)
```

### Model Settings

```python
from agents import ModelSettings

agent = Agent(
    name="Assistant",
    model="gpt-4.1",
    model_settings=ModelSettings(
        temperature=0.7,
        max_tokens=1000,
        top_p=0.9,
        tool_choice="auto",  # or specific tool name
        # Additional parameters as needed
    )
)
```

### Non-OpenAI Models (via LiteLLM)

Integrate models from Anthropic, Google, Cohere, etc.:

```bash
# Install LiteLLM support
pip install "openai-agents[litellm]"
```

```python
# Use with litellm/ prefix
agent = Agent(
    name="Assistant",
    model="litellm/anthropic/claude-3-5-sonnet-20240620"
)

# Other examples:
# model="litellm/gemini/gemini-pro"
# model="litellm/cohere/command-r-plus"
```

### Custom Model Providers

```python
from agents import ModelProvider

class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str):
        # Return custom model implementation
        pass

agent = Agent(
    name="Assistant",
    model=CustomModelProvider()
)
```

### Model Considerations

**Feature Differences Between Providers**:
- Some providers lack structured output support
- Multimodal input support varies
- Tool calling capabilities differ

**Best Practice**: Use consistent model "shape" (similar capabilities) within a workflow for reliable behavior.

---

## Model Context Protocol (MCP)

MCP is a standardized method for connecting AI models to tools and data sources. It's described as "like a USB-C port for AI applications."

### What is MCP?

A universal protocol enabling:
- Tool exposure to language models
- Dynamic tool discovery
- Standardized tool execution
- Flexible integration patterns

### Integration Options

1. **Hosted MCP server tools**
2. **Streamable HTTP MCP servers**
3. **HTTP with Server-Sent Events (SSE)**
4. **stdio (standard input/output) servers**

### Hosted MCP Tool Example

```python
from agents import Agent, HostedMCPTool

agent = Agent(
    name="Git Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "gitmcp",
                "server_url": "https://gitmcp.io/openai/codex"
            }
        )
    ]
)
```

### HTTP MCP Server Example

```python
from agents import Agent, HTTPMCPTool

agent = Agent(
    name="Assistant",
    tools=[
        HTTPMCPTool(
            server_url="https://api.example.com/mcp",
            # Optional configuration
        )
    ]
)
```

### stdio MCP Server Example

```python
from agents import Agent, StdioMCPTool

agent = Agent(
    name="Assistant",
    tools=[
        StdioMCPTool(
            command="python",
            args=["mcp_server.py"]
        )
    ]
)
```

### Dynamic Tool Filtering

```python
def filter_mcp_tools(tools):
    # Only include certain tools
    return [t for t in tools if t.name.startswith("safe_")]

mcp_tool = HostedMCPTool(
    tool_config={...},
    tool_filter=filter_mcp_tools
)
```

### Approval Workflows

```python
async def approve_tool_call(tool_name, arguments):
    # Custom approval logic
    if tool_name in ["delete", "modify"]:
        # Request user approval
        return await get_user_approval(tool_name, arguments)
    return True

mcp_tool = HostedMCPTool(
    tool_config={...},
    approval_callback=approve_tool_call
)
```

### Use Cases

- Connecting to filesystem tools
- Integrating external APIs
- Database access
- Version control integration (Git)
- Cloud service integration
- Custom tool ecosystems

---

## Multi-Agent Patterns

The SDK supports multiple design patterns for orchestrating multiple agents.

### Pattern 1: Manager Pattern

A central agent invokes specialized sub-agents as tools.

```python
from agents import Agent

# Create specialized agents
code_expert = Agent(
    name="Code Expert",
    instructions="Review and analyze code"
)

security_expert = Agent(
    name="Security Expert",
    instructions="Identify security vulnerabilities"
)

# Manager agent uses specialists as tools
manager = Agent(
    name="Manager",
    instructions="Coordinate code review by using specialized agents",
    tools=[code_expert, security_expert]
)

# Manager decides when to invoke each specialist
result = await Runner.run(manager, "Review this code for security issues")
```

**Characteristics**:
- Manager maintains control
- Sub-agents are tools, not conversational
- Useful for task decomposition

### Pattern 2: Handoff Pattern

Agents delegate full conversation control to specialized agents.

```python
# Create specialized agents
billing_agent = Agent(
    name="Billing Agent",
    instructions="Handle all billing inquiries",
    # Can have its own tools, handoffs, etc.
)

technical_agent = Agent(
    name="Technical Agent",
    instructions="Provide technical support"
)

# Triage agent routes to specialists
triage_agent = Agent(
    name="Triage Agent",
    instructions="""
    Route customers to appropriate specialist:
    - Billing questions → Billing Agent
    - Technical issues → Technical Agent
    """,
    handoffs=[billing_agent, technical_agent]
)

# Triage transfers control completely
result = await Runner.run(triage_agent, "I have a billing question")
# billing_agent handles the conversation from here
```

**Characteristics**:
- Full conversation delegation
- Specialized agents maintain context
- Useful for domain-specific expertise

### Pattern 3: Sequential Chain

Agents process tasks in sequence, each building on the previous result.

```python
# Research agent
researcher = Agent(
    name="Researcher",
    instructions="Research the topic and gather information",
    tools=[web_search]
)

# Analyzer agent
analyzer = Agent(
    name="Analyzer",
    instructions="Analyze the research and extract insights"
)

# Writer agent
writer = Agent(
    name="Writer",
    instructions="Write a comprehensive report based on analysis"
)

# Chain execution
research_result = await Runner.run(researcher, "Research AI agents")
analysis_result = await Runner.run(analyzer, research_result.to_input_list())
final_result = await Runner.run(writer, analysis_result.to_input_list())
```

**Characteristics**:
- Linear workflow
- Each agent processes previous output
- Useful for multi-stage transformations

### Pattern 4: Parallel Execution

Multiple agents work independently on different aspects.

```python
import asyncio

# Different specialized agents
summary_agent = Agent(name="Summarizer", instructions="Summarize content")
sentiment_agent = Agent(name="Sentiment", instructions="Analyze sentiment")
keyword_agent = Agent(name="Keywords", instructions="Extract keywords")

# Run in parallel
results = await asyncio.gather(
    Runner.run(summary_agent, text),
    Runner.run(sentiment_agent, text),
    Runner.run(keyword_agent, text)
)

summary, sentiment, keywords = results
```

**Characteristics**:
- Independent processing
- Faster execution
- Useful for multi-faceted analysis

### Pattern 5: Hierarchical Organization

Multiple layers of agents with different responsibilities.

```python
# Layer 3: Specialists
db_specialist = Agent(name="DB Specialist", instructions="Database queries")
api_specialist = Agent(name="API Specialist", instructions="API integration")

# Layer 2: Department agents
backend_agent = Agent(
    name="Backend Agent",
    instructions="Handle backend tasks",
    tools=[db_specialist, api_specialist]
)

frontend_agent = Agent(
    name="Frontend Agent",
    instructions="Handle frontend tasks"
)

# Layer 1: Top-level coordinator
coordinator = Agent(
    name="Coordinator",
    instructions="Coordinate software development",
    handoffs=[backend_agent, frontend_agent]
)
```

**Characteristics**:
- Multiple levels of delegation
- Clear responsibility separation
- Useful for complex domains

### Best Practices for Multi-Agent Systems

1. **Clear Responsibilities**: Each agent should have a well-defined purpose
2. **Minimal Overlap**: Avoid agents with duplicate capabilities
3. **Explicit Instructions**: Clearly document when to handoff/delegate
4. **Context Management**: Use sessions to maintain state across agents
5. **Error Handling**: Implement fallback mechanisms
6. **Testing**: Test handoff logic thoroughly
7. **Monitoring**: Use tracing to understand agent interactions

---

## Examples & Use Cases

### Customer Service System

```python
# Specialized agents
order_status_agent = Agent(
    name="Order Status",
    instructions="Check order status",
    tools=[check_order_status]
)

refund_agent = Agent(
    name="Refund Processor",
    instructions="Process refund requests",
    tools=[process_refund]
)

faq_agent = Agent(
    name="FAQ",
    instructions="Answer frequently asked questions"
)

# Main support agent
support_agent = Agent(
    name="Customer Support",
    instructions="""
    Help customers with:
    - Order status → transfer to Order Status agent
    - Refunds → transfer to Refund Processor
    - General questions → answer using FAQ agent
    """,
    handoffs=[order_status_agent, refund_agent, faq_agent]
)
```

### Research Bot with Web Search

```python
from agents import WebSearchTool

research_agent = Agent(
    name="Research Assistant",
    instructions="""
    Research topics thoroughly:
    1. Use web search to find recent information
    2. Synthesize findings
    3. Cite sources
    4. Provide balanced perspective
    """,
    tools=[WebSearchTool()]
)
```

### Financial Analysis Agent

```python
# Analysis tool
@function_tool
def analyze_stock(ticker: str) -> dict:
    """Get stock analysis."""
    # Implementation
    return {"price": 150.0, "change": "+2.5%"}

# Visualization tool
@function_tool
def create_chart(data: dict) -> str:
    """Create financial chart."""
    # Implementation
    return "chart_url"

financial_agent = Agent(
    name="Financial Analyst",
    instructions="Provide financial analysis and visualizations",
    tools=[analyze_stock, create_chart]
)
```

### Code Review System

```python
# Linting agent
linter = Agent(
    name="Linter",
    instructions="Check code style and formatting",
    tools=[run_linter]
)

# Security agent
security = Agent(
    name="Security Checker",
    instructions="Identify security vulnerabilities",
    tools=[security_scan]
)

# Performance agent
performance = Agent(
    name="Performance Analyzer",
    instructions="Analyze code performance",
    tools=[profile_code]
)

# Main reviewer
code_reviewer = Agent(
    name="Code Reviewer",
    instructions="Coordinate comprehensive code review",
    tools=[linter, security, performance]
)
```

### Educational Tutor

```python
# Math tutor
math_tutor = Agent(
    name="Math Tutor",
    instructions="""
    Help with math:
    - Explain step-by-step
    - Provide examples
    - Check understanding
    """,
    tools=[calculate, plot_graph]
)

# History tutor
history_tutor = Agent(
    name="History Tutor",
    instructions="Teach historical topics with context and timelines"
)

# Main tutor router
tutor = Agent(
    name="Education Tutor",
    instructions="Route students to appropriate subject tutor",
    handoffs=[math_tutor, history_tutor]
)
```

### Content Moderation System

```python
# Moderation guardrails
@input_guardrail
async def check_profanity(text) -> GuardrailFunctionOutput:
    has_profanity = contains_profanity(text)
    return GuardrailFunctionOutput(
        output="Profanity detected" if has_profanity else "OK",
        tripwire=has_profanity
    )

@output_guardrail
async def check_pii(text) -> GuardrailFunctionOutput:
    has_pii = contains_pii(text)
    return GuardrailFunctionOutput(
        output="PII detected" if has_pii else "OK",
        tripwire=has_pii
    )

moderated_agent = Agent(
    name="Moderated Assistant",
    instructions="Help users while maintaining safety",
    input_guardrails=[check_profanity],
    output_guardrails=[check_pii]
)
```

### Workflow Automation

```python
# Task breakdown
@function_tool
def create_tasks(project: str) -> list:
    """Break project into tasks."""
    return ["task1", "task2", "task3"]

# Assignment
@function_tool
def assign_task(task: str, person: str) -> str:
    """Assign task to person."""
    return f"{task} assigned to {person}"

# Tracking
@function_tool
def update_status(task: str, status: str) -> str:
    """Update task status."""
    return f"{task} status: {status}"

workflow_agent = Agent(
    name="Workflow Manager",
    instructions="Manage project workflows",
    tools=[create_tasks, assign_task, update_status]
)
```

---

## Best Practices

### Agent Design

1. **Single Responsibility**: Each agent should have one clear purpose
   ```python
   # Good
   billing_agent = Agent(name="Billing", instructions="Handle billing only")

   # Avoid
   everything_agent = Agent(name="All", instructions="Do everything")
   ```

2. **Clear Instructions**: Be specific and detailed
   ```python
   # Good
   instructions = """
   You are a technical support agent.
   - Diagnose technical issues step-by-step
   - Ask clarifying questions
   - Provide solutions with explanations
   - If you cannot solve, transfer to human support
   """

   # Avoid
   instructions = "Help with tech support"
   ```

3. **Appropriate Tool Selection**: Only include tools the agent needs
   ```python
   # Good - focused tools
   math_agent = Agent(tools=[calculate, plot_graph])

   # Avoid - too many unrelated tools
   agent = Agent(tools=[calculate, send_email, book_flight, translate])
   ```

### Tool Design

1. **Descriptive Docstrings**: Help the LLM understand when to use tools
   ```python
   @function_tool
   def get_weather(location: str) -> str:
       """
       Fetch current weather conditions for a specific location.

       Use this when the user asks about current weather.

       Args:
           location: City name or zip code

       Returns:
           Weather description including temperature and conditions
       """
       pass
   ```

2. **Type Hints**: Enable automatic schema generation
   ```python
   @function_tool
   def process_order(order_id: str, quantity: int, urgent: bool = False) -> dict:
       """Process an order."""
       pass
   ```

3. **Error Handling**: Provide clear error messages
   ```python
   @function_tool
   def api_call(endpoint: str) -> str:
       """Call external API."""
       try:
           return call_api(endpoint)
       except APIError as e:
           raise ToolError(f"API call failed: {e}. Please try again later.")
   ```

### Session Management

1. **Use Meaningful Session IDs**:
   ```python
   # Good
   session = SQLiteSession(f"user_{user_id}_conversation_{conv_id}")

   # Avoid
   session = SQLiteSession("session1")
   ```

2. **Choose Right Storage Backend**:
   - Development: SQLite in-memory
   - Production: SQLAlchemy with PostgreSQL/MySQL
   - Sensitive data: Encrypted sessions

3. **Session Cleanup**:
   ```python
   # Implement periodic cleanup
   async def cleanup_old_sessions():
       # Delete sessions older than 30 days
       cutoff_date = datetime.now() - timedelta(days=30)
       # Cleanup logic
   ```

### Handoff Strategy

1. **Document Handoff Logic in Instructions**:
   ```python
   triage_agent = Agent(
       instructions="""
       Route users based on query type:
       - Billing/payment → Billing Agent
       - Technical problems → Technical Agent
       - General questions → answer directly

       Always explain why you're transferring.
       """
   )
   ```

2. **Use Handoff Descriptions**:
   ```python
   specialist = Agent(
       name="Database Specialist",
       handoff_description="Expert in database optimization and query performance"
   )
   ```

3. **Test Handoff Triggers**: Ensure agents handoff appropriately
   ```python
   # Test various inputs
   test_cases = [
       ("billing question", should_handoff_to="Billing"),
       ("general question", should_handoff_to=None),
   ]
   ```

### Guardrails

1. **Layer Multiple Guardrails**:
   ```python
   agent = Agent(
       input_guardrails=[
           check_profanity,
           check_spam,
           validate_language
       ],
       output_guardrails=[
           check_pii,
           verify_accuracy,
           ensure_helpfulness
       ]
   )
   ```

2. **Use Tripwires Judiciously**: Only for critical violations
   ```python
   @input_guardrail
   async def check_critical(input) -> GuardrailFunctionOutput:
       is_critical_violation = check_violation(input)
       return GuardrailFunctionOutput(
           output="Critical violation",
           tripwire=is_critical_violation  # Halts execution
       )
   ```

3. **Log Guardrail Triggers**: Monitor what's being caught
   ```python
   @input_guardrail
   async def logged_guardrail(input) -> GuardrailFunctionOutput:
       result = check_input(input)
       if result.tripwire:
           log_violation(input, result.output)
       return result
   ```

### Tracing and Monitoring

1. **Enable Tracing in Development**: Always trace during development
2. **Disable Sensitive Data in Production**:
   ```python
   config = RunConfig(trace_include_sensitive_data=False)
   ```

3. **Custom Trace Processors for Analytics**:
   ```python
   class AnalyticsProcessor(TraceProcessor):
       def process_trace(self, trace):
           # Send to analytics platform
           send_to_analytics({
               "duration": trace.duration,
               "tokens": trace.token_count,
               "agent": trace.agent_name
           })
   ```

### Performance Optimization

1. **Use Streaming for Long Responses**: Improve perceived performance
2. **Parallel Agent Execution**: When agents are independent
   ```python
   results = await asyncio.gather(
       Runner.run(agent1, input1),
       Runner.run(agent2, input2)
   )
   ```

3. **Appropriate Model Selection**:
   - Quick tasks: Use faster, smaller models (gpt-4-mini)
   - Complex reasoning: Use capable models (gpt-4, gpt-5)

4. **Tool Response Optimization**: Keep tool responses concise
   ```python
   @function_tool
   def get_data(query: str) -> str:
       data = fetch_large_dataset(query)
       return summarize(data)  # Don't return entire dataset
   ```

### Testing

1. **Test Individual Agents**:
   ```python
   async def test_billing_agent():
       result = await Runner.run(billing_agent, "What's my bill?")
       assert "bill" in result.final_output.lower()
   ```

2. **Test Handoff Logic**:
   ```python
   async def test_handoff():
       result = await Runner.run(triage, "Billing question")
       assert result.last_agent.name == "Billing Agent"
   ```

3. **Test Guardrails**:
   ```python
   async def test_guardrail():
       with pytest.raises(InputGuardrailTripwireTriggered):
           await Runner.run(agent, "inappropriate input")
   ```

4. **Test Tool Calls**:
   ```python
   async def test_tool_usage():
       result = await Runner.run(agent, "What's the weather?")
       assert any(item.tool_name == "get_weather" for item in result.new_items)
   ```

### Security

1. **Validate Tool Inputs**: Never trust LLM-generated tool arguments blindly
2. **Use Guardrails**: Prevent injection attacks and misuse
3. **Encrypt Sensitive Sessions**: Use encrypted sessions for PII
4. **Audit Tool Calls**: Log all tool executions for security review
5. **Limit Tool Permissions**: Use conditional tool enabling
   ```python
   agent = Agent(
       tools=[
           (admin_tool, lambda ctx: ctx.get("is_admin"))
       ]
   )
   ```

### Error Handling

1. **Graceful Degradation**:
   ```python
   @function_tool
   def external_service() -> str:
       """Call external service with fallback."""
       try:
           return call_service()
       except ServiceError:
           return "Service temporarily unavailable. Using cached data."
   ```

2. **User-Friendly Error Messages**:
   ```python
   try:
       result = await Runner.run(agent, input)
   except Exception as e:
       logger.error(f"Agent error: {e}")
       return "I encountered an issue. Please try again or contact support."
   ```

### Documentation

1. **Document Agent Purposes**: Maintain registry of agents and their roles
2. **Document Tool Behaviors**: Clear documentation of what each tool does
3. **Document Handoff Flows**: Diagram multi-agent workflows
4. **Keep Examples Updated**: Maintain working example code

### Cost Optimization

1. **Monitor Token Usage**:
   ```python
   result = await Runner.run(agent, input)
   total_tokens = sum(r.usage.total_tokens for r in result.raw_responses)
   ```

2. **Use Appropriate Models**: Don't use expensive models for simple tasks
3. **Optimize Prompts**: Keep instructions concise yet clear
4. **Cache When Possible**: Reuse results for identical queries
5. **Limit Conversation History**: Trim old messages in sessions
   ```python
   def filter_history(items):
       return items[-20:]  # Keep only last 20 items
   ```

---

## Additional Resources

### Official Documentation
- [OpenAI Agents Python SDK Docs](https://openai.github.io/openai-agents-python/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [OpenAI Traces Dashboard](https://platform.openai.com/traces)

### Key Concepts to Remember

1. **Agents** are configured with LLMs, instructions, and tools
2. **Runner** executes agents synchronously, asynchronously, or with streaming
3. **Sessions** automatically manage conversation history
4. **Tools** extend agent capabilities (functions, hosted tools, or agents)
5. **Handoffs** enable multi-agent orchestration
6. **Guardrails** validate inputs and outputs
7. **Tracing** provides visibility into agent execution
8. **Streaming** enables real-time updates

### Quick Reference

```python
# Basic agent setup
from agents import Agent, Runner, SQLiteSession

# Create agent
agent = Agent(
    name="Assistant",
    instructions="Be helpful",
    tools=[my_tool],
    model="gpt-4.1"
)

# Run with session
session = SQLiteSession("conv_123")
result = await Runner.run(agent, "Hello!", session=session)

# Access result
print(result.final_output)
print(result.new_items)
```

This comprehensive guide covers all major aspects of creating AI agents with the OpenAI Agents SDK. Refer to specific sections as needed when building your agent applications.
