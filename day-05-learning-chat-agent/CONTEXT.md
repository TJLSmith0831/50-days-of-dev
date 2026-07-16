# Context — Day 06: Learning Chat Agent

## Glossary

**Learning Chat Agent** — A conversational agent that adapts its responses based on user feedback across sessions. Unlike stateless chatbots, it maintains memory of user preferences and applies them to future interactions without being re-taught.

**Session** — A single conversation interaction with the agent, from initial greeting to termination. Sessions are isolated by default but share access to persistent memory.

**Preference** — A user's stylistic or behavioral requirement for how the agent should respond. Examples: "casual language," "short responses," "don't use the word 'utilize'." Preferences are learned through explicit feedback and implicit observation.

**Memory System** — The persistence layer that stores and retrieves preferences across sessions. Memory enables the agent to recall what it learned in previous sessions and apply it to new conversations.

**Human-in-the-Loop Feedback** — The mechanism by which users correct or guide the agent's behavior. Feedback can be explicit ("that's too formal") or implicit (providing a good example). The system must distinguish between feedback to learn from and normal conversation to respond to.

**Tool Usage** — The agent's ability to take actions beyond text generation, such as writing files to a sandbox. Tools extend the agent's capabilities while maintaining the learning loop.

**Sandbox** — A temporary directory where the agent can write files during tool usage. Files in the sandbox are not persisted between sessions and serve as ephemeral workspace.

**Style Adaptation** — The process by which the agent adjusts its output to match learned preferences. This includes sentence structure, vocabulary choice, phrasing patterns, and formatting conventions.

**Learning vs Responding** — The core decision boundary: when should the agent update its memory (learn) versus when should it simply process the request (respond)? This distinction prevents the agent from treating every utterance as a preference to store.
