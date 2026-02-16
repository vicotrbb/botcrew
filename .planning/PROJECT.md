# Botcrew

## What This Is

Botcrew is a Kubernetes-native autonomous AI workforce operating system and orchestrator. It runs a team of AI agents — each with their own identity, personality, memory, and heartbeat — as individual pods in a K8s cluster. Agents collaborate with each other and with human users on projects, communicate via chat rooms and direct messages, and evolve over time through their work and interactions. Think of it as an always-on AI team that works for and with humans.

## Core Value

Autonomous AI agents that genuinely collaborate — with each other and with humans — as an always-on, self-evolving workforce. If the agents can't work independently, communicate fluidly, and produce real output, nothing else matters.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Orchestrator manages agent pod lifecycle (creation, deletion, self-healing) via K8s API
- [ ] Each agent runs as its own always-running K8s pod (agent container + browser sidecar)
- [ ] Agents have configurable heartbeats — periodic wake-up prompts that trigger work cycles
- [ ] Agents have freeform text memory stored in Postgres, readable/writable by agent and user
- [ ] Agents can modify their own identity, personality, heartbeat, and memory via Agno tools
- [ ] Agents are powered by Agno framework with configurable AI model per agent
- [ ] Agent tools (v1): file management, web search, shell access, browser use, coding tools, reasoning
- [ ] Browser use via Playwright sidecar container (adapted from HAAT), accessed through BrowserTools Agno toolkit
- [ ] Global skills library — markdown-based instructions (name, description, body) accessible by all agents
- [ ] Direct messaging between agents (triggers immediate processing) + shared chat rooms
- [ ] Native web chat UI (browser-based) for user-agent and agent-agent communication
- [ ] Discord integration via webhooks — agents post with custom names/avatars per channel
- [ ] Projects with shared filesystem workspaces accessible by all assigned agents
- [ ] Projects sync to GitHub
- [ ] Creating a project auto-creates a chat channel with assigned agents
- [ ] UI: create/manage agents (born, view, edit, delete, duplicate)
- [ ] UI: chat — shared channel (all agents) + custom channels with specific agents
- [ ] UI: manage integrations (Discord per agent, AI providers, GitHub)
- [ ] UI: create/manage projects and assign agents
- [ ] UI: manage secrets (key-value pairs accessible by agents for external services)
- [ ] Users can create new agents ("born") with a name; defaults for identity, personality, heartbeat; empty memory
- [ ] Users can duplicate existing agents
- [ ] Hybrid work model — users set high-level goals, agents self-organize and coordinate
- [ ] Agents born as generalists, evolve into specialists through work and interactions
- [ ] Celery + Redis queue system for async task processing

### Out of Scope

- Multi-tenancy — single tenant deployment for now, simplicity first
- Mobile app — web UI only
- Agent-to-agent memory access — memory is strictly private per agent
- Scale-to-zero agent pods — pods are always running
- Custom agent container images — all agents use the same base image

## Context

- **Prior art:** HAAT project (`/Users/victorbona/Personal/HAAT`) — browser-use container and BrowserTools Agno toolkit are direct references for Botcrew's browser sidecar pattern
- **Inspiration:** OpenClaw.ai (https://openclaw.ai/) — reference for multi-agent orchestration UX and capabilities
- **Agent framework:** Agno (https://www.agno.com/) — all agent capabilities are implemented as Agno toolkits; agents are Agno agents
- **Heartbeat model:** A configurable prompt sent to the agent on a schedule. The agent wakes, checks messages, reviews projects, and does work. Both agent and user can modify the heartbeat prompt
- **Memory model:** Freeform text blob in a Postgres row per agent. Agent manages its own memory, user can also edit. No structure imposed — agent decides what to remember
- **Self-evolution:** Agents can modify their own name, identity, personality, heartbeat, and memory via dedicated Agno tools. It's under the agent's discretion to evolve itself to better fit its work
- **Communication architecture:** Separate communication layer abstracting native chat and Discord. Discord uses webhooks (no bot tokens). Direct messages between agents trigger immediate processing; shared rooms are checked during heartbeats
- **Browser sidecar:** Each agent pod includes a Playwright-based browser container (adapted from HAAT's `haat-browser-use`). Agent accesses it via `BrowserTools` Agno toolkit at `localhost:8001`. Session-based, token-authenticated, REST API for all browser operations
- **Skills system:** Global markdown files with frontmatter (name, description up to 250 chars) and body (instructions). All agents access the same skill library
- **Projects:** Not limited to software — can be marketing campaigns, creative work, anything. Each project gets a shared workspace directory and a dedicated chat channel

## Constraints

- **Tech stack (backend):** Python + FastAPI — chosen for Agno compatibility and ecosystem
- **Tech stack (frontend):** TypeScript, React + Vite, TanStack Query — modern, fast, proven
- **Agent framework:** Agno — all agent tools must be Agno toolkits
- **Database:** PostgreSQL — agent memory, project data, system state
- **Cache:** Redis — session management, ephemeral data
- **Queue:** Celery + Redis — async task processing, heartbeat scheduling
- **Infrastructure:** Kubernetes — pods, services, PVCs; must be K8s-native, not just K8s-compatible
- **Browser sidecar:** Playwright base image (`mcr.microsoft.com/playwright/python:v1.50.0-noble`) — proven from HAAT

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Always-running agent pods (no scale-to-zero) | Simplicity, instant responsiveness, agents are "always on" | — Pending |
| Agno as agent framework | Toolkit abstraction, model flexibility, proven in HAAT | — Pending |
| Browser as sidecar container (not baked into agent) | Clean separation, independent resource management, K8s-native pattern | — Pending |
| Discord via webhooks (not bot accounts) | No token management per agent, custom names/avatars per message | — Pending |
| Freeform text memory (not structured) | Agent autonomy — let agents decide what and how to remember | — Pending |
| Global skills library (not per-agent) | Simplicity, any agent can learn anything | — Pending |
| Single tenant first | Start simple, elegant, working — complexity later | — Pending |
| Celery + Redis for queues | Proven Python async pattern, Redis already in stack | — Pending |

---
*Last updated: 2026-02-16 after initialization*
