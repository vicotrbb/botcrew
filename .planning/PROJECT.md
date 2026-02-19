# Botcrew

## What This Is

Botcrew is a Kubernetes-native autonomous AI workforce operating system. It runs a team of AI agents -- each with their own identity, personality, memory, and heartbeat -- as individual pods in a K8s cluster. Agents collaborate with each other and with human users on projects, communicate via chat rooms and direct messages, and evolve over time through their work and interactions. A complete React frontend makes the system fully operable without API calls.

## Core Value

Autonomous AI agents that genuinely collaborate -- with each other and with humans -- as an always-on, self-evolving workforce. If the agents can't work independently, communicate fluidly, and produce real output, nothing else matters.

## Requirements

### Validated

- Orchestrator manages agent pod lifecycle (creation, deletion, self-healing) via K8s API -- v1.0
- Each agent runs as its own always-running K8s pod (agent container + browser sidecar) -- v1.0
- Agents have configurable heartbeats -- periodic wake-up prompts that trigger work cycles -- v1.0
- Agents have freeform text memory stored in Postgres, readable/writable by agent and user -- v1.0
- Agents can modify their own identity, personality, heartbeat, and memory via Agno tools -- v1.0
- Agents are powered by Agno framework with configurable AI model per agent -- v1.0
- Agent tools (v1): file management, web search, shell access, browser use, coding tools -- v1.0
- Browser use via Playwright sidecar container, accessed through BrowserTools Agno toolkit -- v1.0
- Global skills library -- markdown-based instructions accessible by all agents -- v1.0
- Direct messaging between agents + shared chat rooms with real-time WebSocket -- v1.0
- Native web chat UI for user-agent and agent-agent communication -- v1.0
- Projects with shared filesystem workspaces and GitHub sync -- v1.0
- Creating a project auto-creates a chat channel with assigned agents -- v1.0
- UI: create/manage agents (born, view, edit, delete, duplicate) -- v1.0
- UI: chat -- shared channel (all agents) + custom channels with specific agents -- v1.0
- UI: manage integrations (AI providers, GitHub) -- v1.0
- UI: create/manage projects and assign agents -- v1.0
- UI: manage secrets (key-value pairs accessible by agents) -- v1.0
- UI: manage skills (create, edit, delete markdown skills) -- v1.0
- Users can create new agents ("born") with a name; defaults for identity, personality, heartbeat -- v1.0
- Users can duplicate existing agents -- v1.0
- Hybrid work model -- users set high-level goals, agents self-organize and coordinate -- v1.0
- Agents born as generalists, evolve into specialists through work and interactions -- v1.0
- Celery + Redis queue system for async task processing -- v1.0

### Active

#### Tasks System
- [ ] Tasks with names, descriptions, and directive bodies
- [ ] Completable vs regular (recurring) task types
- [ ] Assign agents to tasks (triggers agent to work on directive)
- [ ] Assign secrets and skills to tasks (injected into agent context)
- [ ] Task channels auto-created with assigned agents
- [ ] Agent access to tasks via Agno toolkit

#### Agent Collaboration & Autonomy
- [ ] Agent self-invocation tool (spawn focused LLM call with scoped instruction)
- [ ] Improved heartbeat with dynamic objective discovery (tasks, projects)
- [ ] Heartbeat spawns sub-instances for each directive
- [ ] Agents auto-start collaboration when assigned to projects
- [ ] Shared coordination mechanism for multi-agent project work
- [ ] Agents discuss and divide work like a real engineering team
- [ ] Instant replies on channel messages (LLM-driven relevance decision)
- [ ] Agent DMs with instant response

#### Chat & UX Improvements
- [ ] Channel sections: Projects → Tasks → Custom → DMs
- [ ] Chat management: delete channels, add/remove agents (restricted for project/task channels)
- [ ] Resizable chat panel (horizontal)
- [ ] Project secrets assignment (secrets available in project context)

#### Kubernetes Integration
- [ ] K8s cluster integration type for managing the cluster Botcrew runs on
- [ ] Safe permissions and boundaries for K8s management
- [ ] Agent tools for K8s monitoring, management, and modification

#### Bug Fixes
- [ ] Fix secrets page (frontend broken)
- [ ] Fix agents unable to access project directories
- [ ] Fix frontend fields not populated from backend values (providers, agent edit panel)
- [ ] Fix agent removal from projects (visual feedback)
- [ ] Fix delete agent visual feedback (return to agents page)

#### Quality
- [ ] Validation phase: AI tests all features, generates fix report

### Out of Scope

- Multi-tenancy -- single tenant deployment for now, simplicity first
- Mobile app -- web UI only
- Agent-to-agent memory access -- memory is strictly private per agent
- Scale-to-zero agent pods -- pods are always running
- Custom agent container images -- all agents use the same base image
- Self-evolution guardrails -- evolution is permanent, agent's full discretion
- Visual workflow builder -- agents self-organize, not pipeline-driven
- Manager/hierarchy agents -- flat structure, peer-to-peer communication
- Real-time streaming of all agent thought -- overwhelming at scale; use on-demand logs instead
- Per-agent memory types (structured) -- freeform text only
- Discord integration -- dropped during v1.0 development (Phase 10 removed)

## Current Milestone: v2.0 — Agents That Actually Work

**Goal:** Make agents autonomously useful -- they find work, coordinate with each other, execute tasks, and deliver real output on projects.

**Target features:**
- Tasks system (regular + completable directives with secrets, skills, channels)
- Agent self-invocation (spawn focused LLM calls for parallel work)
- Multi-agent project collaboration (auto-start, shared coordination, full lifecycle)
- Instant replies with LLM-driven relevance filtering
- Kubernetes cluster integration
- Chat UX overhaul (sections, management, DMs, resizable panel)
- Bug fixes and validation phase

## Context

- **Shipped:** v1.0 MVP (2026-02-18) -- 9 phases, 50 plans, ~19,476 LOC
- **Tech stack (backend):** Python 3.12, FastAPI, Agno, Celery, SQLAlchemy 2.0, Alembic
- **Tech stack (frontend):** TypeScript, React 19, Vite, Tailwind v4, shadcn/ui, TanStack Query, Zustand
- **Infrastructure:** Kubernetes (kind for dev), PostgreSQL, Redis, Gateway API, Helm charts
- **Agent framework:** Agno -- 8 toolkits, 38 tools per agent
- **Prior art:** HAAT project -- browser sidecar pattern adapted from HAAT's browser-use container
- **Heartbeat model:** Configurable prompt on a schedule; agent wakes, checks messages, reviews projects, does work
- **Memory model:** Freeform text blob in Postgres per agent; no structure imposed
- **Self-evolution:** Agents modify own identity, personality, heartbeat, memory -- permanent, no guardrails
- **Communication:** WebSocket + Redis pub/sub for real-time; Celery for async DM delivery
- **Known issues:** model_factory.py duplicated between orchestrator and agent; no automated tests; frontend uses polling for some data

## Constraints

- **Agent framework:** Agno -- all agent tools must be Agno toolkits
- **Database:** PostgreSQL -- agent memory, project data, system state
- **Cache:** Redis -- session management, ephemeral data, pub/sub
- **Queue:** Celery + Redis -- async task processing, heartbeat scheduling
- **Infrastructure:** Kubernetes -- must be K8s-native
- **Browser sidecar:** Playwright base image (mcr.microsoft.com/playwright/python:v1.50.0-noble)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Always-running agent pods (no scale-to-zero) | Simplicity, instant responsiveness, agents are "always on" | Good -- agents respond instantly to DMs and heartbeats |
| Agno as agent framework | Toolkit abstraction, model flexibility, proven in HAAT | Good -- 38 tools across 8 toolkits working |
| Browser as sidecar container | Clean separation, independent resource management, K8s-native | Good -- native sidecar ordering, health probes |
| Freeform text memory (not structured) | Agent autonomy -- let agents decide what to remember | Good -- simple, flexible |
| Global skills library (not per-agent) | Simplicity, any agent can learn anything | Good -- CRUD API + UI working |
| Single tenant first | Start simple, elegant, working | Good -- entire v1 shipped in 3 days |
| Celery + Redis for queues | Proven Python async pattern, Redis already in stack | Good -- DM delivery, heartbeats, project sync |
| Bare K8s pods (not Deployments) | Each agent is unique; orchestrator as custom controller | Good -- reconciliation loop handles self-healing |
| Hub-and-spoke architecture | Single orchestrator as control plane | Good -- clean separation of concerns |
| Gateway API (not Ingress NGINX) | NGINX retiring March 2026 | Good -- future-proof |
| Custom Helm charts (no Bitnami) | Bitnami behind paywall since Sept 2025 | Good -- simple, maintainable |
| Tailwind v4 CSS-first | Modern approach, no JS config needed | Good -- cleaner setup |
| Discord integration dropped | User decision during v1.0 development | Accepted -- focus on core value |
| Redis pub/sub for WebSocket fan-out | Fire-and-forget, Postgres for durability | Good -- <500ms latency achieved |
| Transport abstraction for communication | Future extensibility without touching core | Good -- clean interface |

| Agent self-invocation (not new pods) | Lightweight parallel work without infrastructure cost; agent calls its own LLM with scoped instruction | — Pending |
| LLM-driven reply filtering (not programmatic) | Agents decide whether to respond based on context, like humans in Slack | — Pending |
| Shared coordination file for project collaboration | Agents need more than chat to coordinate; structured state prevents duplicate work | — Pending |

---
*Last updated: 2026-02-18 after v2.0 milestone started*
