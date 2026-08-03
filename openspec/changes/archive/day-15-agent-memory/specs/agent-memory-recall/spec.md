## ADDED Requirements

### Requirement: Fresh-session turns with no threaded history
Every turn (seed, filler, or recall question) SHALL be issued as an independent LLM call carrying no prior conversation history, for both the no-memory and memory-backed lanes.

#### Scenario: A turn cannot see a prior turn's content directly
- **WHEN** a filler or recall-question turn is issued
- **THEN** the LLM call SHALL contain only that turn's own message, with no messages from any earlier turn in the pair

### Requirement: Per-pair fact/question recall test
The system SHALL run 3 independent fact/question pairs, each consisting of a seed fact, 3 unrelated filler turns, and a recall question requiring the seeded fact to answer correctly.

#### Scenario: A pair's turns run in order
- **WHEN** a fact/question pair is executed
- **THEN** the system SHALL issue the seed turn, then the 3 filler turns, then the recall question, in that order, for both lanes

### Requirement: No-memory baseline lane
The system SHALL run a no-memory lane per pair that never stores or retrieves via Mem0 — the recall-question turn is a bare fresh-session call with no injected context.

#### Scenario: No-memory lane cannot recall the seeded fact
- **WHEN** the no-memory lane's recall-question turn is issued
- **THEN** the system SHALL NOT query Mem0 or inject any memory content into that call's prompt

### Requirement: Memory-backed lane with per-pair isolation
The system SHALL run a memory-backed lane per pair using a local Mem0 instance, storing the seed turn and all 3 filler turns under a `user_id` unique to that pair, and retrieving from Mem0 before the recall question.

#### Scenario: Memory-backed lane stores every turn
- **WHEN** the memory-backed lane's seed or filler turn completes
- **THEN** the system SHALL call Mem0's add operation with that turn's content, scoped to the pair's own `user_id`

#### Scenario: Memory-backed lane retrieves before answering
- **WHEN** the memory-backed lane's recall-question turn is about to run
- **THEN** the system SHALL search Mem0 scoped to the pair's own `user_id`, and prepend the retrieved memories to that call's prompt

#### Scenario: One pair's memory is invisible to another pair
- **WHEN** pair B's memory-backed lane searches Mem0
- **THEN** the system SHALL NOT return any memory stored under pair A's `user_id`

### Requirement: Fully local Mem0 configuration
Mem0 SHALL be configured to use Ollama (`mistral`) as both its internal LLM and the demo's own agent LLM, `nomic-embed-text` as its embedder, and a local Chroma vector store — with no Mem0 Cloud API key and no `MemoryClient` usage.

#### Scenario: No network calls to Mem0 Cloud
- **WHEN** any part of the demo runs, including Mem0's add and search operations
- **THEN** the system SHALL NOT make any request to Mem0's hosted/cloud API or require a Mem0 API key

### Requirement: Deterministic pass/fail grading
Each pair SHALL define an expected keyword; a lane's answer to the recall question SHALL be graded Pass if that keyword appears in the answer text (case-insensitive substring match), Fail otherwise.

#### Scenario: Keyword present
- **WHEN** a lane's recall-question answer contains the pair's expected keyword (any case)
- **THEN** the system SHALL grade that lane's result as Pass for that pair

#### Scenario: Keyword absent
- **WHEN** a lane's recall-question answer does not contain the pair's expected keyword
- **THEN** the system SHALL grade that lane's result as Fail for that pair

### Requirement: Pass/fail report across all pairs and lanes
After all 3 pairs run through both lanes, the system SHALL print a report showing each pair's no-memory result, memory-backed result, and a totals row.

#### Scenario: End-of-run report
- **WHEN** all 3 fact/question pairs have completed both lanes
- **THEN** the system SHALL print a table with one row per pair (no-memory Pass/Fail + truncated answer, memory-backed Pass/Fail + truncated answer) and a totals row summing Pass counts per lane
