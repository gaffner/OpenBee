# Claude Code — Deep Dive Findings

**Project Path:** `C:\projects\Discovery`
**Source analyzed:** Claude Code internal source (`c:\Users\galtshuler\OneDrive - Microsoft\Desktop\code\src`)
**Date:** April 2, 2026

---

## Table of Contents

1. [Thinking Mode](#1-thinking-mode)
2. [Context Preservation](#2-context-preservation)
3. [Query Engine](#3-query-engine)
4. [Tools System](#4-tools-system)
5. [Session Management](#5-session-management)
6. [POC Code](#6-poc-code)

---

## 1. Thinking Mode

### What It Is

Claude Code uses "extended thinking" — the model reasons internally before producing a visible response. This reasoning is streamed in real-time as `thinking` content blocks, separate from the final `text` response.

### Three Configuration Types

```typescript
type ThinkingConfig =
  | { type: 'adaptive' }                        // Claude 4.6+ — unlimited, model decides how much to think
  | { type: 'enabled'; budgetTokens: number }    // Legacy — fixed token budget for thinking
  | { type: 'disabled' }                         // No thinking at all
```

### How to Enable Thinking via the API

**Budget mode (Claude Sonnet 4, legacy models):**

```typescript
const response = await client.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 16000,
  thinking: {
    type: "enabled",
    budget_tokens: 10000   // Max tokens the model can use for thinking
  },
  messages: [{ role: "user", content: prompt }],
  stream: true,
});
```

**Adaptive mode (Claude 4.6+ — Opus 4.6, Sonnet 4.6):**

```typescript
const response = await client.messages.create({
  model: "claude-opus-4-6-...",
  max_tokens: 128000,
  thinking: {
    type: "enabled_by_default"  // No budget_tokens — model allocates freely
  },
  messages: [{ role: "user", content: prompt }],
  stream: true,
});
```

### Model Compatibility

| Model | Thinking | Adaptive Thinking |
|-------|----------|-------------------|
| Claude 3.x | No | No |
| Claude Haiku 4.5 | Yes (1P/Foundry only) | No |
| Claude Sonnet 4 | Yes | No |
| Claude Opus 4 | Yes | No |
| Claude Sonnet 4.6 | Yes | Yes |
| Claude Opus 4.6 | Yes | Yes |

### Interleaved Thinking

When using streaming, the model can think **multiple rounds** (think → respond → think again → respond more). Enable it with a beta header:

```typescript
const response = await client.messages.create(
  {
    model: "claude-sonnet-4-20250514",
    max_tokens: 16000,
    thinking: { type: "enabled", budget_tokens: 10000 },
    messages: [{ role: "user", content: prompt }],
    stream: true,
  },
  {
    headers: {
      "anthropic-beta": "interleaved-thinking-2025-05-14",
    },
  },
);
```

### Streaming Event Types for Thinking

```
content_block_start  → type: "thinking"     → Thinking round begins
content_block_delta  → type: "thinking_delta" → Thinking text chunk
content_block_start  → type: "text"          → Response begins
content_block_delta  → type: "text_delta"    → Response text chunk
message_delta        → usage info
```

### Budget Calculation

Claude Code calculates max thinking tokens as:

```typescript
maxThinkingTokens = model.maxOutputTokens.upperLimit - 1
// Sonnet 4.6 / Opus 4.6: 128,000 - 1 = 127,999 thinking tokens
```

### Environment Overrides

| Variable | Effect |
|----------|--------|
| `MAX_THINKING_TOKENS` | Override budget globally (number) |
| `CLAUDE_CODE_DISABLE_THINKING` | Disable all thinking |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | Force budget mode on adaptive models |

### "Ultrathink" Feature

A special keyword `ultrathink` in user prompts triggers enhanced thinking. Gated by:
- Build-time feature flag (`ULTRATHINK`)
- Runtime feature flag (`tengu_turtle_carbon` via GrowthBook)

When detected, the UI renders the keyword with rainbow colors.

---

## 2. Context Preservation

### How Claude Code Maintains Conversation State

Claude Code preserves context across messages through multiple layers:

#### A. Message History (In-Memory)

The `QueryEngine` maintains a `mutableMessages: Message[]` array that persists across turns within a session. Every user message, assistant response, and tool result is appended to this array and sent with each subsequent API call.

#### B. System Context (Rebuilt Per-Turn)

Each API call rebuilds system context from:

```
1. Git status snapshot (branch, commits, dirty files)
2. Claude.md files from memory directories
3. Tool availability list
4. Permission context
5. Injected system prompt parts
```

#### C. Local History Persistence

Conversation history is stored in `~/.config/Claude/history.jsonl` as NDJSON:

```typescript
{
  display: string,           // What the user typed
  pastedContents: string[],  // Large pastes stored separately (>1024 chars → hash refs)
  timestamp: number,
  project: string,           // Working directory
  sessionId: string          // Links turns to sessions
}
```

- Max 100 items, newest-first
- Session-scoped: concurrent sessions don't interleave during replay (ctrl+r)

#### D. Remote History (Bridge Sessions)

For remote/bridge sessions, history is fetched via REST:

```typescript
// Fetch latest N events
GET /v1/sessions/{id}/events?anchor_to_latest=true&limit=100

// Paginate backwards
GET /v1/sessions/{id}/events?before_id={cursor}
```

#### E. Application State

Persistent state tracked via `AppStateStore` (immutable pattern):

```
- settings (user prefs)
- mainLoopModel (current model)
- toolPermissionContext (granted permissions)
- thinkingEnabled (thinking mode toggle)
- tasks, plugins, mcp state
```

### Auto-Compaction

When context grows too large, Claude Code runs automatic compaction:
- Tracks `AutoCompactTrackingState` across iterations
- Attempts reactive compaction when `maxOutputTokens` is exceeded
- Summarizes older conversation turns to free context window space

---

## 3. Query Engine

### Architecture

The `QueryEngine` is the core orchestrator — it manages the conversation loop between the user, the model, and tools.

```
User Input → QueryEngine.submitMessage()
                ↓
         Build System Prompt (context, permissions, claude.md)
                ↓
         Build Messages (history + new prompt)
                ↓
         Call queryModel() (streaming)
                ↓
         Process Response (text blocks + tool_use blocks)
                ↓
         Execute Tools (StreamingToolExecutor)
                ↓
         Append Results → Loop or Return
```

### Configuration

```typescript
type QueryEngineConfig = {
  cwd: string
  tools: Tool[]
  commands: Command[]
  mcpClients: McpClient[]
  agents: Agent[]
  canUseTool: CanUseToolFn          // Permission callback per tool
  getAppState: () => AppState
  setAppState: (state: AppState) => void
  initialMessages: Message[]        // Seed conversation history
  customSystemPrompt?: string       // Override system prompt
  appendSystemPrompt?: string       // Append to system prompt
  userSpecifiedModel?: string       // Model override
  thinkingConfig?: ThinkingConfig   // Thinking mode
  maxTurns?: number                 // Max agentic loops
  maxBudgetUsd?: number             // Cost limit
  taskBudget?: TaskBudget           // Task-level budget
}
```

### Continuation Logic

The query loop continues iterating (model → tools → model) until:

```typescript
// Token budget check
const COMPLETION_THRESHOLD = 0.9      // 90% of budget used → stop
const DIMINISHING_THRESHOLD = 500     // <500 new tokens per iteration → stop

// Also stops when:
// - No tool_use blocks in response (model is done)
// - maxTurns reached
// - Budget (USD) exceeded
// - User abort signal
```

---

## 4. Tools System

### Tool Interface

```typescript
type Tool = {
  name: string                          // e.g., 'Bash', 'Read', 'Agent'
  inputSchema: ZodSchema                // Input validation via Zod
  isEnabled(): boolean                  // Runtime availability
  isConcurrencySafe(input): boolean     // Can run in parallel?
  execute(input, ctx): AsyncGenerator<ToolProgress | Result>
}
```

### Available Tools

| Tool | Purpose |
|------|---------|
| BashTool | Execute shell commands |
| FileReadTool | Read files |
| FileWriteTool | Write/create files |
| FileEditTool | Patch existing files |
| GlobTool | Search files by pattern |
| GrepTool | Search file contents |
| AgentTool | Spawn sub-agents |
| WebFetchTool | Fetch web content |
| WebSearchTool | Search the web |
| NotebookEditTool | Edit Jupyter notebooks |
| BriefTool | Compact context |
| SkillTool | Load project skills |
| ToolSearchTool | Search MCP tools |

### Concurrency Control

```typescript
// Non-concurrent tools (e.g., Bash, FileWrite): execute one at a time
// Concurrent-safe tools (e.g., Read, Glob, Grep): can run in parallel

// The StreamingToolExecutor manages a queue:
// 1. Check if tool is concurrency-safe
// 2. If current executing tools are all concurrent-safe → run in parallel
// 3. Otherwise → queue and wait
```

### Execution Flow

```
1. Model returns tool_use block
2. Validate input against Zod schema
3. Call permission callback (canUseTool)
4. Execute tool → yields progress + final result
5. Append tool result to messages
6. Continue query loop
```

---

## 5. Session Management

### Session Types

Claude Code supports two session modes:

**Local Sessions:**
- Direct API calls from the CLI
- State in memory + local history file
- No remote bridge

**Bridge Sessions (Remote):**
- Connects to a remote server via bridge
- Session created via `POST /v1/sessions`
- Messages exchanged via polling or streaming
- Supports reconnection to existing sessions

### Session Creation

```typescript
// Bridge session creation
POST /v1/sessions
Body: {
  project_path: string,      // Working directory
  user_uuid: string,         // User identifier
  max_turns?: number,
  model?: string,
  session_type?: string      // 'bridge', 'sdk', etc.
}
```

### Session Runner

The `sessionRunner` orchestrates the full lifecycle:

```
1. Create/resume session
2. Initialize QueryEngine with session config
3. Enter message loop:
   a. Receive inbound message
   b. Submit to QueryEngine
   c. Stream responses back via bridge transport
4. Handle disconnects/reconnects
5. Cleanup on session end
```

### Transport Layer

Messages between local and remote use `replBridgeTransport`:
- Inbound: user messages, control requests (abort, set model, set thinking)
- Outbound: assistant messages, tool progress, status updates
- Polling-based with configurable intervals

---

## 6. POC Code

A working proof-of-concept demonstrating both Anthropic (with extended thinking) and OpenAI streaming is located in:

```
C:\projects\Discovery\poc\
```

### Running the POC

```bash
cd C:\projects\Discovery\poc
npm install
npm start
```

### Setup

1. Create a `.env` file with your Anthropic key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

2. Place your OpenAI key in:
   ```
   ~/Desktop/openai_key.txt
   ```

3. Run `npm start` — select a model and enter a prompt.

### Key Implementation Details

The POC demonstrates:

- **Streaming with thinking blocks:** The Anthropic path streams `thinking_delta` and `text_delta` separately, showing reasoning in real-time
- **Interleaved thinking:** Multiple thinking rounds are tracked and labeled (`∴ Thinking...`, `∴ Thinking again (round 2)...`)
- **Multi-provider support:** Same interface for Anthropic and OpenAI models
- **Secure key loading:** Keys read from files/env vars, never hardcoded

See `poc/index.ts` for the full implementation.
