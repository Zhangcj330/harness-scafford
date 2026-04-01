# Harness References

This scaffold is informed by:

- OpenAI, "Harness engineering"
- Anthropic, "How we built our multi-agent research system"
- OpenAI, "Unlocking the Codex harness"
- Anthropic quickstart for long-running autonomous coding
- AGENTS.md conventions

Distilled takeaways applied here:

- keep long-lived state off ephemeral clients
- checkpoint aggressively
- treat artifacts and docs as first-class system interfaces
- prefer deterministic environment scaffolding over prompt-only orchestration
