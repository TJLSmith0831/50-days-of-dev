## 1. Project Setup

- [x] 1.1 Create day-06-coding-agent-repl-harness/ directory structure
- [x] 1.2 Create pyproject.toml with dependencies (Rich, ollama-python, anthropic, ddgs, langgraph, langchain-ollama, tiktoken)
- [x] 1.3 Set [tool.uv] package = false in pyproject.toml
- [x] 1.4 Create AGENTS.md with commands and gotchas
- [x] 1.5 Create README.md with project description
- [x] 1.6 Create .env.example for API keys (ANTHROPIC_API_KEY)
- [x] 1.7 Create src/ directory with module structure

## 2. Tool System

- [x] 2.1 Implement tool registry with JSON schema generation
- [x] 2.2 Implement Read tool (file reading via pathlib)
- [x] 2.3 Implement Glob tool (file pattern matching)
- [x] 2.4 Implement Grep tool (content search via re/ripgrep)
- [x] 2.5 Implement Web Search tool (ddgs integration)
- [x] 2.6 Implement openspec CLI tool (subprocess wrapper)
- [x] 2.7 Add parameter validation for all tools

## 3. Agent Loop

- [x] 3.1 Implement LangGraph state definition (AgentState with messages)
- [x] 3.2 Implement LLM invocation with Ollama (Qwen3:14b)
- [x] 3.3 Implement tool dispatch logic
- [x] 3.4 Implement tool result processing
- [x] 3.5 Implement loop continuation logic (stop when no tool calls)
- [x] 3.6 Add streaming token display support
- [x] 3.7 Add error handling for LLM failures

## 4. REPL Interface

- [x] 4.1 Implement Rich-based REPL with Console
- [x] 4.2 Implement streaming token display with live rendering
- [x] 4.3 Implement thinking spinner during LLM processing
- [x] 4.4 Implement speaker layout (agent in green, user in blue)
- [x] 4.5 Implement @file mention expansion
- [x] 4.6 Implement slash commands: /help, /save, /sessions, /exit, /handoff
- [x] 4.7 Implement rich panels for tool outputs (syntax highlighting)
- [x] 4.8 Implement user input handling

## 5. Session Management

- [x] 5.1 Implement SQLite database initialization (~/.coding-agent-harness/sessions.db)
- [x] 5.2 Implement LangGraph SqliteSaver integration
- [x] 5.3 Implement session creation and metadata storage
- [x] 5.4 Implement session update logic
- [x] 5.5 Implement mid-turn checkpointing
- [x] 5.6 Implement session resume by ID/thread_id
- [x] 5.7 Implement /sessions command to list sessions
- [x] 5.8 Implement /save command to persist session
- [x] 5.9 Implement session deletion

## 6. Context Management

- [x] 6.1 Implement token counting (tiktoken with character fallback)
- [x] 6.2 Implement context truncation logic
- [x] 6.3 Implement system prompt preservation
- [x] 6.4 Implement recent message preservation (last N messages)
- [x] 6.5 Implement tool result preservation
- [x] 6.6 Add max context tokens configuration
- [x] 6.7 Add truncation notification to user

## 7. Grilling Integration

- [x] 7.1 Implement grill-with-docs skill invocation
- [x] 7.2 Implement grill-me skill invocation
- [x] 7.3 Implement conversation context passing to skills
- [x] 7.4 Implement skill output incorporation into agent context
- [x] 7.5 Add skill availability checks
- [x] 7.6 Add error handling for skill failures

## 8. Claude Code Handoff

- [x] 8.1 Implement /handoff command trigger
- [x] 8.2 Implement user confirmation dialog
- [x] 8.3 Implement Claude Code headless API call
- [x] 8.4 Implement Claude Code output display in REPL
- [x] 8.5 Implement return to REPL after handoff
- [x] 8.6 Add Claude Code availability check
- [x] 8.7 Add API key validation
- [x] 8.8 Implement manual opsx:apply fallback instructions

## 9. Main Entry Point

- [x] 9.1 Implement main.py with CLI argument parsing
- [x] 9.2 Add --model argument (default: qwen3:14b)
- [x] 9.3 Add --thread-id argument for session selection
- [x] 9.4 Add --fresh argument for new session
- [x] 9.5 Add --self-check argument for preflight checks
- [x] 9.6 Implement preflight check (Ollama connection, model availability)
- [x] 9.7 Integrate all modules into main REPL loop

## 10. Testing and Verification

- [ ] 10.1 Test tool system (Read, Glob, Grep, Web Search, openspec CLI)
- [ ] 10.2 Test agent loop with tool calls
- [ ] 10.3 Test REPL UI (streaming, slash commands, @file expansion)
- [ ] 10.4 Test session persistence (save, resume, list)
- [ ] 10.5 Test context truncation
- [ ] 10.6 Test grill skill integration
- [x] 10.7 Test Claude Code handoff (if available)
- [x] 10.8 Verify uv run main.py works
- [x] 10.9 Verify --self-check works
- [x] 10.10 Update README with verified commands
