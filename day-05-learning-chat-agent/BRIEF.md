# Learning Chat Agent — Demo Brief

**Hook:** An AI agent that learns your preferences instantly — without fine-tuning, without training data, without retraining the model.

## What it proves (the trust story)
Not "an agent remembered something." Three beats that make this a practical alternative to fine-tuning:
1. **No fine-tuning** — uses base model unchanged, zero training cost or compute. Learning happens through feedback + memory storage, not model weights.
2. **Human-guided** — you control exactly what it learns through explicit feedback. No black-box adaptation, no unintended side effects.
3. **Reversible** — preferences can be reset or changed instantly without retraining. `--fresh` flag clears memory; different thread_ids isolate users.

## Why this approach works
Traditional fine-tuning requires training data, compute cost, and model retraining for every preference change. This agent demonstrates that base models can adapt through:
- **Memory persistence** via LangGraph's SqliteSaver (stores preferences in local SQLite database)
- **Human-in-the-loop feedback** that extracts and stores preferences from natural language
- **Context injection** that loads learned preferences into the system prompt for subsequent responses

The result: instant adaptation without touching model weights.

## Real-world use case
You're a developer who needs the AI to explain code in a specific way for your team — step-by-step for juniors, high-level for seniors. Instead of fine-tuning a model for each audience, you teach the preference once and it persists across sessions. Change your mind? Reset with `--fresh` and start over — no retraining required.

## Record-time setup
- Ollama running with `qwen3:14b` pulled, reachable at `http://localhost:11434` (recommended over llama3.2 for better tool behavior)
- `checkpoints.db` is `.gitignore`d and accumulates real runs — clear or delete it before recording so the demo doesn't imply prior fake history
- Have two clear preference examples ready:
  - Cover letters: "I prefer bullet points instead of long paragraphs"
  - Code explanations: "I prefer step-by-step explanations instead of high-level overviews"

## Behaviors that can appear on screen (know these before recording)
Fully local, fully live — every response streams as it's generated.

- **Live streaming:** Agent responses appear token-by-token, not all at once. Let them finish before cutting.
- **Preference extraction:** When you give feedback, the agent explicitly acknowledges learning: "Preference learned: [preference text]" — this is the money shot for the human-in-the-loop beat.
- **Memory persistence:** The `checkpoints.db` file is created/updated in real-time. You can show this file exists between sessions to prove persistence.
- **Thread isolation:** Using `--thread-id user-1` vs `--thread-id user-2` creates separate memory spaces. Don't mix thread_ids mid-demo unless demonstrating isolation.
- **Tool calling:** qwen3:14b has better tool behavior than llama3.2, but may still call tools unnecessarily. If the agent tries to write files unprompted, that's expected behavior — not a bug.
- **Ollama down:** Agent fails with clear error "Ollama isn't responding. Start it with `ollama serve`..." — verify Ollama is running before recording.
- **Fresh start:** `--fresh` flag clears memory by using a new thread_id. The agent won't remember previous preferences after this flag.
- **No piped input:** The interactive session uses rich console input and requires manual terminal input. Do not pipe input (e.g., `echo | uv run main.py`) as this will cause "EOF when reading a line" errors. Type prompts directly in the terminal.

## Graphical explanation (animated sequence, ~10s)
Start the demo with a simple animated diagram showing the learning loop:
1. **User request** → Agent responds with default behavior
2. **User feedback** → Agent extracts preference → Stores in memory
3. **Subsequent request** → Agent loads preferences from memory → Responds with adapted behavior

Use simple boxes and arrows. Color-code: User (blue), Agent (green), Memory (yellow). Animation should loop once, then fade out as the terminal demo begins.

## Shot list (~90s total)

### Graphical explanation (10s)
1. **Animated diagram (10s):** Learning loop animation plays. Caption: *how agents learn without fine-tuning*.

### Cover letter mini-demo (35s)
2. **Cold open (5s):** `uv run main.py --model qwen3:14b` → header appears. Caption: *base model, unmodified*.
3. **Default response (10s):** "Write a cover letter for a software engineering job" → agent writes standard paragraph-style letter. Caption: *default behavior*.
4. **Teach preference (10s):** "I prefer bullet points instead of long paragraphs" → agent responds "Preference learned: bullet points instead of long paragraphs". Caption: *human-in-the-loop feedback*.
5. **Apply preference (10s):** "Write a cover letter for a software engineering job" → agent writes bullet-point style letter. Caption: *preference applied instantly*.

### Code explanation mini-demo (35s)
6. **Fresh start (5s):** `uv run main.py --model qwen3:14b --fresh` → new session, memory cleared. Caption: *reversible learning*.
7. **Default response (10s):** "Explain how a hash table works" → agent gives high-level overview. Caption: *back to default behavior*.
8. **Teach preference (10s):** "I prefer step-by-step explanations instead of high-level overviews" → agent responds "Preference learned: step-by-step explanations". Caption: *teaching a different preference*.
9. **Apply preference (10s):** "Explain how a hash table works" → agent gives detailed step-by-step explanation. Caption: *learning works for any preference type*.

### Close (10s)
10. **Memory proof (5s):** Show `checkpoints.db` file exists and has recent timestamp. Caption: *preferences persist in SQLite, not model weights*.
11. **Clean exit (5s):** Ctrl-D → "Goodbye."

## Frame
- Start with graphical explanation (full screen or overlay), then switch to terminal for live demo
- Terminal: dark theme, large font, no IDE chrome
- Let each agent response complete before cutting — the streaming is part of the story
- End on "Goodbye." held for 1–2s

## Checks referenced
- `uv run main.py --self-check` (verifies Ollama connection and dependencies)
- `uv run main.py --model qwen3:14b --fresh` (clears memory for clean demo starts)
