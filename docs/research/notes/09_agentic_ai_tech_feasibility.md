# Agentic AI in 2026: technical building blocks, Vietnamese-language capability, platform integrations, legal constraints and unit economics for a student MVP (TECH STARTUP CHALLENGER 2027, TDTU, MVP window 23/11/2026 – 10/01/2027)

Research date: 2026-10-04. All prices were read on that date unless a page date is given. FX used for conversions: 1 USD = 25,939.86 VND (open.er-api.com, last updated 04 Oct 2026 00:02 UTC) — [open.er-api.com](https://open.er-api.com/v6/latest/USD). Items older than 2025 are tagged [BACKGROUND]. Claims taken from search-engine result summaries rather than a fetched page are tagged "(search-result summary)" and are lower-confidence. Method note: the session's shared web-search budget ran out partway through, so later items were checked only by fetching known primary URLs. Some vendor pricing pages could not be retrieved, and the Gaps sections list them.

---

## 1. State of the art (2026): agent frameworks, protocols, production architectures, evaluation/guardrails/observability, and what separates a "real" agent from a chatbot wrapper

### Takeaway
By late 2026 the agent stack has consolidated. A small set of frameworks lead: LangGraph for stateful graphs with durable execution and human-in-the-loop (HITL) interrupts; the OpenAI Agents SDK for fast, provider-agnostic agents with realtime voice; Google ADK 2.x (graph runtime with native A2A); the Claude Agent SDK (Claude Code's agent loop with permissions, hooks, subagents and MCP); CrewAI; and the Microsoft Agent Framework. Two open protocols now sit under the Linux Foundation's Agentic AI Foundation: MCP (agent→tool, spec 2026-07-28) and A2A (agent→agent, v1.0). What separates an agent from a wrapper is that the LLM controls workflow execution and calls tools that change external state, inside guardrails, with human approval for high-risk actions, plus tracing and evaluations. Technical judges increasingly expect to see observability and evaluation evidence.

### Cited Findings

#### Frameworks (status mid/late 2026)
- **LangGraph**: graph-based, with durable execution and checkpointing, HITL interrupts and short/long-term memory. About 34.5M monthly downloads and 33.9K GitHub stars, and more than 400 companies run it in production (e.g., Klarna, Replit, Elastic, Cisco, Uber, LinkedIn, BlackRock, JPMorgan). This is a secondary blog dated 23 Jul 2026 — [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/)
- **OpenAI Agents SDK**: v0.18 as of July 2026, with 26.9K stars and 10.3M monthly downloads. Its primitives are agents, handoffs, guardrails and sessions, with built-in tracing and realtime voice agents. It works with 100+ models via LiteLLM despite the name — [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/). The official docs list agents, handoffs, guardrails, a sessions layer for persistent memory, human-in-the-loop mechanisms, built-in tracing, MCP server tool calling, sandbox agents, realtime agents on `gpt-realtime-2.1` with automatic interruption detection, voice pipelines (STT → agent → TTS) and support for non-OpenAI model providers — [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/)
- **Claude Agent SDK** (Python and TypeScript) is Claude Code's agent loop offered as a library. Capabilities:
  - built-in tools (files, commands, web search), hooks and subagents
  - MCP
  - permissions that set which tools run automatically and which need approval
  - sessions that can be resumed or forked
  - skills/memory and plugins

  Anthropic separately offers "Managed Agents", a hosted harness that runs in an Anthropic-managed or self-hosted sandbox — [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview). The SDK is limited to Claude models — [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/). Managed Agents runtime costs $0.08 per session-hour, counted only while running — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- **Google ADK 2.x** has a graph-based workflow runtime (routing, loops, retries, nested workflows), a Task API for multi-turn delegation, native A2A, native multimodality via Gemini, and a CLI plus web UI for local testing — [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/)
- **CrewAI 1.0+** pairs autonomous "Crews" with event-driven "Flows". It has 52.8K stars and 5.2M monthly downloads and is model-agnostic. **Microsoft Agent Framework 1.x** succeeds AutoGen and Semantic Kernel (merged Oct 2025); it offers graph workflows, middleware, YAML definitions, OpenTelemetry and Python/.NET support. **AutoGen** has been in "maintenance mode" since Oct 2025. Other options:
  - **Pydantic AI 2.x**: durable execution, OpenTelemetry
  - **Mastra 1.x**: TypeScript, with suspend/resume for HITL, evals and 40+ providers
  - **Smolagents**: CodeAgent
  - **Vercel AI SDK v7**: ToolLoopAgent, HarnessAgent and WorkflowAgent
  - **Dify**: 144K stars, low-code

  Source: [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/)
- The same source groups frameworks into three paradigms: graph-based (LangGraph, ADK, MS Agent Framework), role-based (CrewAI, AutoGen) and loop/handoff-based (OpenAI Agents SDK, Smolagents, Strands). It also cites, second-hand, Gartner's forecast that 40% of enterprise apps will have task-specific agents by the end of 2026, up from under 5% in 2025 — [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/)

#### Protocols (MCP, A2A, AAIF)
- The **MCP specification is at version 2026-07-28**. It uses JSON-RPC 2.0 with "stateless, self-contained requests" and per-request capability negotiation. Servers offer Resources, Prompts and Tools; clients offer Elicitation (server-initiated requests for more input from the user). Optional extensions include:
  - **Tasks**: async long-running operations with polling, mid-flight input and durable handles
  - **Skills over MCP**
  - **MCP Apps**: interactive UI such as charts and forms rendered inline

  Under the security principles, hosts must get explicit user consent before invoking any tool, and tool annotations should be treated as untrusted unless they come from a trusted server — [MCP spec](https://modelcontextprotocol.io/specification/latest)
- MCP adoption stood at 110M+ monthly SDK downloads and 10,000+ public servers in April 2026, and MCP Apps launched in January 2026. Anthropic open-sourced MCP in November 2024 [BACKGROUND] — [IntuitionLabs, updated 15 Sep 2026](https://intuitionlabs.ai/articles/agentic-ai-foundation-open-standards)
- The **Agentic AI Foundation (AAIF)** was announced on 9 Dec 2025 as a Linux Foundation directed fund. Its co-founding stewards are Anthropic, OpenAI and Block, and it hosts MCP, goose and AGENTS.md. Membership was 170+ in April 2026 — [IntuitionLabs](https://intuitionlabs.ai/articles/agentic-ai-foundation-open-standards). Another source reports more than 250 members by August 2026, with platinum members AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft and OpenAI — [FlowHunt](https://www.flowhunt.io/blog/agentic-ai-foundation-a2a-mcp-standards/). The two counts were taken at different dates.
- **A2A** has a "What's New in v1.0" page. Its Technical Steering Committee comes from AWS, Cisco, Google, IBM Research, Microsoft, Salesforce, SAP and ServiceNow, and there are official SDKs for Python, JavaScript, Java, C#/.NET, Go and Rust. The project describes MCP as "agent-to-tool" and A2A as "agent-to-agent". The site carries an announcement dated 27 Aug 2026 titled "A2A joins the Agentic AI Foundation" — [a2a-protocol.org](https://a2a-protocol.org/latest/). FlowHunt dates Google's donation of A2A to AAIF as 20 Aug 2026 — [FlowHunt](https://www.flowhunt.io/blog/agentic-ai-foundation-a2a-mcp-standards/). The week's difference between the two dates is unresolved.

#### Production architecture patterns
- **Core components**: OpenAI describes an agent as three parts: a model, tools (external functions/APIs used to take action) and instructions. Every orchestration needs a "run" loop that ends on an exit condition: a final-output tool, a response with no tool calls, an error, or a maximum number of turns — [OpenAI, "A practical guide to building agents" (2025)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) pp. 7, 14–15
- **Single agent first**: OpenAI recommends getting the most out of one agent before adding more. Split into multiple agents when instructions have complex branching logic or tools overlap ("some implementations successfully manage more than 15 well-defined, distinct tools while others struggle with fewer than 10 overlapping tools") — [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) pp. 13, 16
- **HITL triggers**: escalate to a human (1) when failure thresholds are exceeded, such as retry or action limits, and (2) for high-risk actions that are sensitive, irreversible or high-stakes, such as "canceling user orders, authorizing large refunds, or making payments" — [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) p. 31
- **Workflows vs agents** [BACKGROUND, Dec 2024]: in workflows, "LLMs and tools are orchestrated through predefined code paths"; in agents, LLMs "dynamically direct their own processes and tool usage". Anthropic lists five patterns: prompt chaining, routing, parallelization, orchestrator-workers and evaluator-optimizer. Its advice is to add complexity only when it demonstrably improves outcomes and to invest in tool design (the "agent-computer interface", including poka-yoke) — [Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- **HITL and durable state are now first-class framework features**: LangGraph has interrupts and checkpointing, Mastra has suspend/resume, the OpenAI Agents SDK has human-in-the-loop and sessions, and the Claude Agent SDK has permission approvals, hooks and resumable sessions — [The Agent Report](https://the-agent-report.com/2026/07/ai-agent-frameworks-comparison-2026-langgraph-crewai-autogen/), [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/), [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)

#### Evaluation, observability, guardrails, security
- LangChain's "State of Agent Engineering" survey (fielded 18 Nov – 2 Dec 2025, n=1,340) — [LangChain](https://www.langchain.com/state-of-agent-engineering):
  - **Adoption**: 57.3% have agents in production and 30.4% are building toward deployment.
  - **Top use cases**: customer service 26.5%, research and data analysis 24.4%, internal workflow automation 18%.
  - **Barriers**: quality 33% (accuracy, consistency, tone) and latency 20%; cost is a declining concern.
  - **Observability**: 89% have some observability and 62% have detailed step tracing. Among teams with agents in production the figures are 94% and 71.5%.
  - **Evaluation methods**: offline evals 52.4%, online evals 37.3%, human review 59.8%, LLM-as-judge 53.3%.
  - **Models**: 75%+ use multiple models, and 57% do not fine-tune.
- OpenAI's guardrail taxonomy: relevance classifier; safety classifier (jailbreak/prompt injection); PII filter; moderation; tool safeguards (rate each tool low/medium/high by read-only vs write, reversibility, permissions and financial impact, then pause or escalate before high-risk calls); rules-based protections (blocklists, regex, input limits); and output validation. Guardrails are layered, and the Agents SDK runs them concurrently ("optimistic execution") — [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) pp. 24–31
- The **OWASP Top 10 for Agentic Applications for 2026** was released on 9 Dec 2025 and peer-reviewed by 100+ experts. It covers risks of agents that "plan, act, and make decisions across complex workflows" — [OWASP GenAI](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- Vietnamese media in Oct 2026 are covering agent-safety incidents, e.g. "Tác nhân AI Trung Quốc gian lận trong thử nghiệm" and "OpenAI thừa nhận tác nhân truy cập trái phép hệ thống chính phủ" (headline-level only) — [VnExpress AI section](https://vnexpress.net/khoa-hoc-cong-nghe/ai), [article 1](https://vnexpress.net/tac-nhan-ai-trung-quoc-gian-lan-trong-thu-nghiem-5126382.html), [article 2](https://vnexpress.net/openai-thua-nhan-tac-nhan-truy-cap-trai-phep-he-thong-chinh-phu-5126135.html)

#### What counts as "real" agentic AI (definitions judges can be pointed to)
- OpenAI: "Applications that integrate LLMs but don't use them to control workflow execution—think simple chatbots, single-turn LLMs, or sentiment classifiers—are not agents." Under this definition a real agent:
  - uses the LLM to manage workflow execution
  - recognizes when the workflow is complete and corrects its own actions
  - halts and hands control back to the user when it fails
  - dynamically chooses tools both to gather context and to take actions, "always operating within clearly defined guardrails"

  Source: [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) p. 4
- Anthropic: "An agent is an application that completes a task by planning its own steps and calling tools…" — [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- Vietnam's AI Law requires high-risk AI systems to have risk management, technical documentation, activity logs and human supervision/intervention capability (Art. 14) — [AI Law 134/2025/QH15, LuatVietnam English summary](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html)

### Inferences
- **Recommended MVP stack for a 5-person team over 7 weeks.** Use one orchestrator: LangGraph if the product is a multi-step business process with approvals and must survive restarts (checkpointing plus interrupts), or the OpenAI Agents SDK / Google ADK if voice is central (realtime agents, Gemini Live and A2A). Avoid AutoGen, which is in maintenance mode. Avoid elaborate multi-agent designs: both OpenAI and Anthropic advise starting with one agent and adding tools.
- **Wrap each Vietnamese integration as an MCP server**: Zalo OA send/receive, payOS/SePay payment link and webhook, e-invoice issue, calendar or booking. This shows protocol fluency, makes tools reusable across frameworks, and maps onto MCP's consent rule for tool invocation. Use MCP Elicitation or framework interrupts for payment and invoice approvals. Add A2A only if a second, independently deployed agent exists (e.g., an "accounting agent" called by a "sales agent"). Otherwise it reads as buzzword-stacking.
- **What judges will likely probe ("agent vs wrapper" checklist):**
  1. Does the LLM pick and sequence tools at runtime, or is the flow hard-coded?
  2. Do tools write to real systems (send a ZBS message, create a VietQR/payOS link, issue an e-invoice), not just read?
  3. Is there a plan → act → verify loop? For example, issue the invoice only after a bank-webhook payment confirmation.
  4. Is there memory across sessions (customer profile, past orders)?
  5. Are high-risk actions gated by human approval inside Zalo (buttons) or a dashboard?
  6. Is there a trace viewer for each run?
  7. Is there a Vietnamese eval set with task-success, tool-accuracy, escalation-rate, p95-latency and cost-per-task metrics?
  8. Are there guardrails for PII and prompt injection?
  9. Does the agent disclose that it is AI (AI Law Art. 11) and keep consent logs (PDPL)?
- A live demo that shows a trace, an approval step and an eval dashboard will look more "real" to judges than a polished chat UI. The LangChain data shows that teams with production agents almost always have observability (94%).

### Gaps
- Gartner's June 2025 "agent washing" press release, often cited as "over 40% of agentic AI projects will be canceled by 2027", returned HTTP 403 and Reuters could not be fetched, so the figures are unverified here.
- The OWASP Agentic Top-10 item list (IDs and titles) was not extractable from the landing page.
- Framework download and star counts and version numbers come from a single secondary blog (The Agent Report), not from PyPI/npm/GitHub directly.
- Google ADK's GA date (reported in one search summary as 19 May 2026) and A2A v1.0's release date could not be attributed to a fetched primary source.
- No Vietnam-specific published judging rubric for "agentic AI" in student competitions was found.

---

## 2. Vietnamese-language capabilities and prices: frontier and Vietnamese LLMs, speech recognition (dialects, noise), TTS, real-time voice agents, OCR

### Takeaway
Frontier APIs are cheap enough that cost is not the binding constraint for an MVP. Small "flash/mini/haiku-class" models run roughly $0.10–$1 per 1M input tokens. Gemini Live supports Vietnamese for real-time voice at about $0.005/min of audio in and $0.018/min out. The hard technical risks are Vietnamese speech quality (Central accents are measurably hardest) and formatting accuracy of transcripts. Vietnamese vendors (Viettel AI, FPT.AI, VNPT AI) offer domestic hosting and dialect-tuned speech, but their 2026 public price lists are hard to obtain. Viettel announced a 120B Vietnamese LLM in June 2026, but no public API or pricing was found.

### Cited Findings

#### Frontier LLM API prices (USD per 1M tokens; read 2026-10-04)
- **Anthropic Claude** — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing); [claude.com/pricing](https://claude.com/pricing):

  | Model | Input | Cache hit | Output |
  |---|---|---|---|
  | Opus 5.5 | $4 | $0.20 | $20 |
  | Sonnet 5.5 | $2 | $0.20 | $10 |
  | Sonnet 5 | $2 | $0.20 | $10 |
  | Haiku 4.5 | $1 | $0.10 | $5 |
  | Fable 5.1 (top tier) | $10 | — | $50 |

  - Sonnet 5's $2/$10 launch price is now standard; the increase to $3/$15 planned for 1 Sep 2026 "will not occur".
  - Batch API gives 50% off.
  - The tokenizer used by Claude 4.7 and later produces "approximately 30% more tokens for the same text".
  - US-only inference costs 1.1x.
  - Web search costs $10 per 1,000 searches; web fetch costs nothing beyond tokens.
  - New users get "a small amount of free credits".
- **OpenAI**, as listed on the pricing page (2026-10-04) — [OpenAI API pricing](https://developers.openai.com/api/docs/pricing):

  | Model | Input | Cached input | Output |
  |---|---|---|---|
  | gpt-6.1-sol | $2.00 | $0.10 | $10.00 |
  | gpt-6-luna | $0.10 | $0.01 | $0.50 |
  | gpt-6-astra | $10 | $1 | $50 |
  | gpt-5.4-mini | $0.75 | — | $4.50 |
  | gpt-5-nano | $0.05 | — | $0.40 |

  - Realtime audio: `gpt-realtime-2.1` $32 in / $64 out per 1M audio tokens; `gpt-realtime-2.1-mini` $10 / $20.
  - Transcription: `gpt-transcribe` $0.0045/min; Whisper $0.006/min.
  - TTS: `tts-1` $15 per 1M characters.
  - Web search: $10 per 1,000 calls.
- **Google Gemini** (page last updated 2026-10-01) — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing):

  | Model | Input | Output |
  |---|---|---|
  | Gemini 3.8 Flash, through 31 Dec 2026 | $0.75 | $3.75 |
  | Gemini 3.8 Flash, from 1 Jan 2027 | $1.50 | $7.50 |
  | Gemini 3.5 Flash-Lite | $0.30 | $2.50 |
  | Gemini 3.1 Flash-Lite | $0.25 (audio $0.50) | $1.50 |
  | Gemini 3.1 Pro Preview (≤200k context) | $2 | $12 |

  - Gemini 3.7 and 3.6 Flash also double in price on 1 Jan 2027.
  - Most Flash, Flash-Lite, Live and TTS models have a **free tier**.
  - Google Search grounding: 5,000 free requests per month, then $14 per 1,000.

#### Real-time voice agents in Vietnamese
- **Gemini Live API**:
  - Supports 99 languages including Vietnamese (`vi`).
  - Handles voice activity detection and barge-in (interruptions), and supports function calling and tool use in Live sessions.
  - Audio-only sessions are limited to 15 minutes; native-audio models have a 128k context window.
  - Recommended models are `gemini-3.8-live` and `gemini-3.8-live-extended-thinking`.

  Page updated 2026-09-18 — [Gemini Live guide](https://ai.google.dev/gemini-api/docs/live-guide)
- **Gemini 3.8 Live pricing**: audio input $3.00/1M tokens (about $0.005/min), audio output $12.00/1M (about $0.018/min), text input $0.75, text output $4.50.
  - Gemini 3.5 Transcribe: $0.003/min audio in plus $0.002/min text out.
  - Gemini 3.5 Live Translate: about $0.0053/min in and $0.0315/min out.

  Source: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **ElevenLabs API**:
  - TTS: Flash/Turbo $0.04 per 1K characters; Multilingual v2/v3 $0.08 per 1K.
  - STT: Scribe v2 $0.22/hour; Scribe v2 Realtime $0.39/hour.
  - Agents "Speech Engine": $0.08/min beyond included minutes.
  - "90+ languages" are claimed, but Vietnamese is not named on the page.

  Source: [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)
- **Latency target and dialect accuracy claims**: a Vietnamese implementer's blog says the STT → LLM → TTS cycle must finish within about 800 ms to avoid call abandonment. It claims dialect accuracy of North 92–95%, South 88–92% and Central 80–88% for 2026 voice AI. These are marketing claims with no third-party citation (dated 1 Jun 2026) — [MONA Media](https://mona.media/voice-ai-tieng-viet-callbot-tong-dai-doanh-nghiep/)
- **VNPT AI's iSense Agentic CX Platform** (voice agents) uses the VNPT LLM, RAG, speech recognition, emotion detection and SIP-trunk integration. At VinaPhone it handles about 100,000 calls per day, auto-scores 100% of calls (about 30M a year), saved about 5.8 billion VND in 2025 and reduced the workload of about 180 operators. Article dated 24 Sep 2026 — [CafeBiz](https://cafebiz.vn/vietnam-digital-finance-2026-agentic-ai-la-buoc-nhay-vot-tai-thiet-trai-nghiem-tai-chinh-so-176260924192827572.chn)

#### Vietnamese speech recognition (research evidence on dialects)
- **"Vietnamese ASR: A Revisit"** (Qualcomm AI Research Vietnam, EACL 2026 Findings, March 2026) built PhoASR, a high-quality 502.67-hour dataset — [ACL Anthology PDF](https://aclanthology.org/2026.findings-eacl.345.pdf)
  - **Data imbalance**: North 286 h, South 146 h, Central 70 h.
  - **Central is hardest**: models trained on a single accent do worse on the others, and "the Central accent is consistently the most difficult". A Whisper-small trained on Northern data scored O-WER 19.89% on North vs 26.16% on Central.
  - **Fine-tuning is essential**:
    - Pretrained whisper-small: O-WER 70.16% / N-WER 64.07%.
    - PhoWhisper-small: N-WER 8.97% but O-WER 33.90%.
    - ChunkFormer-large-vi (trained on 25K h): N-WER 6.89% but O-WER 32.43%.
    - PhoASR-whisper-small-3100h: O-WER 11.70% / N-WER 8.20%.
  - O-WER (orthographic, with punctuation and capitalisation) is the metric that matters for usable transcripts.
- **Other benchmark resources** include UIT-ViMD (multi-dialect), LSVSC and VietMed (medical ASR). PhoWhisper (2024) [BACKGROUND] was fine-tuned on 844 h of accent-diverse data — [PhoWhisper arXiv](https://arxiv.org/pdf/2406.02555); [VietMed arXiv](https://arxiv.org/pdf/2404.05659) (search-result summary)

#### Vietnamese TTS / STT vendor prices
- **Viettel AI official price list** [BACKGROUND, dated 27 Dec 2022, VAT excluded] — [Viettel IDC](https://viettel-idc.com.vn/index.php/tin-tuc/tin-cong-nghe/bang-gia-dich-vu-viettel-ai-text-to-speech-speech-to-text-viettel-ai-61.html):
  - **TTS**: 320,000 VND per 1M characters pay-as-you-go; packages of 3.2M VND/month (10M chars) and 15M VND/month (50M chars).
  - **STT**: 600 VND/min pay-as-you-go, billed in 15-second blocks; packages of 12M VND per 20,000 min and 25M VND per 50,000 min.
- **FPT.AI** markets TTS and STT ("the best integrated system of Vietnamese language voice in the market"), with free evaluation at voicemaker.fpt.ai. No prices are shown on the docs page — [FPT.AI docs](https://docs.fpt.ai/docs/en/speech/documentation/text-to-speech/). A search-result summary says FPT TTS gives 100,000 free characters per month, paid plans start at 500,000 VND/month, and FPT.TTS-pro has 5 premium voices with Northern and Southern accents (unverified; search-result summary of [FPT.AI docs](https://docs.fpt.ai/docs/en/speech/documentation/text-to-speech/)).
- **Vbee** shows "Bảng giá dịch vụ" for Studio and API, monthly or yearly, but the prices are rendered interactively and could not be extracted. Enterprises are asked to request a quote — [Vbee](https://vbee.vn/bang-gia)

#### Vietnamese LLMs and domestic hosting
- **Viettel AI's VT-Super-120B-A12B** (120B parameters, built on NVIDIA's open Nemotron 3 Super architecture, long context) was announced around 5 Jun 2026. Viettel says it is building an "AI Agent ecosystem for Vietnamese users", starting with a Legal AI Assistant. The article gives no API, pricing, benchmark or open-weights details — [CafeF](https://cafef.vn/cong-nghe-5-6-viettel-ai-tang-cuong-suc-manh-voi-mo-hinh-ngon-ngu-120b-tham-so-188260605074535525.chn)
- **FPT** aims for at least 100 billion uses of its Vietnamese LLM once widely deployed, targeting the public sector, finance-banking and retail from 2026 (headline plus search-result summary) — [CafeBiz, 31 Dec 2025](https://cafebiz.vn/fpt-dat-muc-tieu-trien-khai-mo-hinh-ngon-ngu-lon-tieng-viet-voi-toi-thieu-100-ty-luot-su-dung-176251231091408349.chn)
- **FPT AI Factory** has data centres in Hanoi, Ho Chi Minh City and Tokyo, with Malaysia coming soon.
  - It sells GPU containers, VMs, bare metal and clusters, with RTX Pro 6000 Blackwell "from $2.19/hour" (early access).
  - "FPT Token Factory" offers serverless inference for 20+ models via marketplace.fptcloud.com.
  - The footer links to a "Startups Program".

  Source: [FPT AI Factory](https://factory.fpt.ai/). A search-result summary of an FPT AI Factory blog lists hosted open models such as GLM-5.2 ($1.4 in / $4.4 out / $0.26 cached) and Qwen3.8-Max (unverified) — [FPT AI Factory blog](https://factory.fpt.ai/ai-insights/top-list-of-large-language-models)
- Zalo is reportedly developing LLMs from 1B to 30B parameters, and VinBigData runs ViGPT. The dates are unclear and probably 2023–24 [BACKGROUND] (search-result summary) — [VietnamNet](https://vietnamnet.vn/nguoi-viet-phat-trien-mo-hinh-ngon-ngu-lon-tieng-viet-2237808.html)

#### Vietnamese OCR / document AI
- Vendor accuracy claims are around 98% for FPT.AI Reader (150+ enterprise clients, 50+ templates) and around 99% for Vietnamese handwriting with RUNSYSTEM OCR Studio. Typical cloud subscriptions cost about 5–50M VND a year. All of these are vendor claims, unsourced (dated 5 Mar 2026) — [RUNSYSTEM](https://runsystem.net/vi/tin-tuc/ai-ocr)
- FPT.AI's current product line includes FPT AI Read (OCR), FPT AI eKYC, FPT AI Agents and FPT AI Voice Agent, with 3,000+ enterprise clients — [FPT.AI](https://fpt.ai/)
- VNPT SmartReader is said to recognise printed text, vouchers, contracts and handwriting (search-result summary) — [VNPT AI blog](https://vnptai.io/en/blog/detail/ocr-la-gi)

### Inferences
- **Model choice by job**: use a "Flash/mini/Haiku-class" model for the tool-calling loop. Escalate to Sonnet 5.5, gpt-6.1-sol or Gemini 3.1 Pro only for hard planning or verification steps (a router or evaluator-optimizer pattern). The price spread between small and large models is about 10–40x.
- **MVP timing trap**: Gemini 3.x Flash and Flash TTS prices **double on 1 Jan 2027**, which falls inside the MVP window (23/11/2026–10/01/2027). Any cost slide built on 2026 Gemini prices should show both price points.
- **Voice**: Gemini Live is the quickest path to a Vietnamese real-time voice demo because it has native audio, VAD/barge-in and function calling. Mitigate the 15-minute session cap and test Central and Southern speakers explicitly. If the product depends on regional dialects (e.g., Mekong Delta farmers, Central-region callers), budget time to compare a Vietnamese STT (Viettel, FPT or VNPT) against Gemini/OpenAI transcription on 30–50 recorded samples per region. The PhoASR results show accent mismatch can add 5–7 WER points.
- **Data residency**: if the product handles sensitive data (health, finance), FPT AI Factory, Viettel or VNPT hosting inside Vietnam is a credible "PDPL-friendly" pitch point. Frontier APIs are processed abroad (see section 4).
- **OCR**: for printed forms and invoices, a frontier vision-language model plus schema extraction is likely enough for an MVP. For handwriting (prescriptions, notebooks), domestic OCR such as FPT AI Read or VNPT SmartReader is a safer bet. No head-to-head benchmark was found.

### Gaps
- No 2026 public price list was retrieved for Viettel AI (homepage content truncated), VNPT AI (pricing URL 404), FPT.AI speech/OCR (pricing URL 404) or Vbee (prices rendered client-side). The Viettel 2022 list is the only official figure, and it is old.
- No public API or pricing was found for VT-Super-120B, the VNPT LLM, or Zalo/VinBigData LLMs.
- No independent benchmark was found comparing frontier models (GPT/Claude/Gemini) on Vietnamese tasks, Vietnamese tokenization overhead, or Vietnamese real-time voice latency.
- Neither OpenAI Realtime nor ElevenLabs explicitly confirms Vietnamese support on the pages fetched.
- No published benchmark was found on noisy-environment Vietnamese ASR (markets, motorbike traffic, call-centre noise), apart from the dialect results above.
- No published benchmark was found on Vietnamese handwriting OCR comparing VLMs (Gemini/GPT/Claude/Vintern) with FPT/VNPT. The accuracy figures above are vendor claims.
- Gemini Live may bill accumulated context per turn, which would raise long-call costs. This was not verified.

---

## 3. Vietnamese platform integrations available to a startup (Zalo OA/ZBS/Mini App/Bot, Messenger, VietQR/NAPAS, bank-webhook services, e-invoice APIs, eTax, VNeID, Open API banking)

### Takeaway
Messaging and payments integrations are cheap and accessible. The pieces:
- **Zalo OA API**: needs a *verified* OA on at least the "Growth" package (2.5M VND/year).
- **ZBS Template Message**: 200–300 VND per message.
- **Zalo Bot Platform**: has a free tier open to individuals.
- **Payment confirmation**: free or near-free via payOS, SePay (free 50 transactions/month) or Casso (free 30/month).
- **E-invoicing**: costs roughly 100–600 VND per invoice through MISA or SePay.

The harder layers are regulated identity and banking:
- **VNeID integration** requires registration with the Ministry of Public Security (C06), VPN links and HSMs.
- **Open API payment initiation** under Circular 64/2024 is limited to banks and licensed payment intermediaries, and full bank compliance is due only on 1 Mar 2027.

### Cited Findings

#### Zalo
- **Zalo OA packages** (effective 1 Jun 2026, prices include 10% VAT; **OA verification is mandatory** before buying):

  | Package | Price | Staff | Chatbot | API | Consultation messages |
  |---|---|---|---|---|---|
  | Standard | 1,000,000 VND/yr | 5 | No | No | 500 free per month |
  | Growth | 1,400,000 VND per 6 months, or 2,500,000 VND/yr | 15 | 10 scenarios | 100 requests/min, up to 3 apps | 2,000 free per month |
  | Comprehensive | 3,400,000 VND per 6 months, or 6,000,000 VND/yr | 100 | 50 scenarios | 2,000 requests/min, unlimited apps | unlimited |

  - Consultation messages follow a 48-hour interaction rule; beyond the package quota they cost 55 VND each.
  - Only verified business OAs on Growth or Comprehensive can send ZBS Template Messages via API.

  Source: [Zalo OA pricing](https://zalo.solutions/oa/pricing)
- **ZBS Template Message pricing** (VAT excluded):

  | Item | Price |
  |---|---|
  | Authentication/OTP, payment-request, voucher and bus-ticket (beta) templates | 300 VND |
  | Other templates | 200 VND |
  | "Journey" templates (delivery, logistics, passenger transport) | from 200 VND |
  | First action button | free |
  | Each additional button | 100 VND |
  | Feedback button (beta) | 100 VND |
  | Permission-request command | 400 VND |

  Sending by Zalo UID costs less than sending to a phone number — [ZBS pricing](https://zalo.solutions/business-message/pricing)
- **ZBS Template Message rules**: server-to-server API for customer-care messaging. It needs a linked ZBS account, OA and App. Templates are reviewed "within 2–3 business days", and a quality system rewards or penalises senders based on recipient feedback — [ZBS intro](https://zalo.solutions/business-message/guidelines/en/intro)
- On 1 Jan 2026 Zalo Business Solutions launched ZBS Template Message, merging "UID Giao dịch", "UID Truyền thông" and ZNS messages into one standard (search-result summary) — [Zalo Solutions news](https://zalo.solutions/news/thong-bao-ra-mat-zbs-template-message-giai-phap-tin-nhan-doanh-nghiep-theo-mau/cp1zx4bq8mzhhszgz0br1ocd); [Mini AI](https://miniai.vn/zbs-template-message/)
- **Zalo Bot Platform**: a chatbot integration platform for individuals and businesses that supports "kết nối với các AI Agent". Plans:
  - **Basic (free)**: 3 bots per account, 50 users per bot, 3,000 messages per month, 3 chat groups (beta).
  - **Pro**: 129,000 VND/month, marked "coming soon".
  - **Enterprise**: custom pricing via OA.

  Source: [Zalo Bot Platform](https://bot.zaloplatforms.com/)
- **Zalo Mini App**: the developer portal (now at miniapp.zaloplatforms.com) lists ZaUI components, APIs, Payment, DevTools, Open APIs and **eKYC APIs**. Specific API, fee and review details were not extractable — [Zalo Mini App docs](https://miniapp.zaloplatforms.com/documents/)

#### Facebook Messenger
- Messenger policy:
  - Businesses can reply, including with promotions, within **24 hours** of a user-initiated message.
  - Outside that window, only approved message tags are allowed. HUMAN_AGENT allows manual replies within 7 days.
  - Promotions outside the window require Sponsored Messages.
  - Bots must **disclose that they are automated** at the start of a conversation or when switching from a human.

  Source: [Meta Messenger Platform policy](https://developers.facebook.com/docs/messenger-platform/policy/policy-overview/)

#### VietQR / NAPAS and bank-transaction webhooks
- **VietQR.io**, operated by CASSO; NAPAS owns the VietQR™ standard:
  - Free public APIs: QR "Quicklink" generation, a bank database and Deeplink.
  - A free "Registered" tier adds account lookup and integrations.
  - "Verified Company" and self-hosted tiers are quote-based.
  - Payment confirmation is handled by the separate payOS product.

  Source: [VietQR.io](https://www.vietqr.io/)
- **payOS (Casso Co., Ltd.)** markets itself as a **free** gateway, "sponsored by Vietnamese banks", claiming 99% savings vs traditional gateways.
  - It supports VietQR across 50+ banks, payment links, dynamic QR and API/web integration, and has a new payout channel ("Kênh chi").
  - A BIDV-1K SME offer (1,000 transactions/year free plus Soundbox devices) runs until 31 Dec 2026.

  Sources: [payOS](https://payos.vn/); free model since launch per [payOS 2023 launch post](https://payos.vn/cong-thanh-toan-mien-phi/). Individuals can register with only a CCCD (citizen ID card) — [payOS 2023 launch post](https://payos.vn/cong-thanh-toan-mien-phi/)
- **SePay**:
  - **FREE**: 0 VND/month, 50 transactions/month, overage allowed and billed. Webhook/API and payment gateway included. Covers 11 banks (Vietcombank, VPBank, ACB, Sacombank, VietinBank, MB, BIDV, MSB, TPBank, KienLongBank, OCB).
  - **STARTUP**: 120,000 VND/month, up to 20% annual discount.
  - **SHOP**: 99,000 VND/month per store, no payment-gateway integration.
  - Personal and business accounts are supported, with unlimited bank accounts and users.
  - Bank promotions: VPBank 500 free transactions/month for a year; BIDV VIP package; MSB 3 months free.

  Source: [SePay pricing](https://sepay.vn/bang-gia.html)
- **Casso** — [Casso pricing](https://api.casso.vn/pricing-table):

  | Plan | Price | Transactions/month | Bank accounts |
  |---|---|---|---|
  | Free | 0 | 30 | 1 |
  | Starter | 99k VND/month (annual) or 129k (monthly) | 100–700 | 2 |
  | Pro | 379k/489k VND/month | 340–10,000 | 5 |
  | Team | 3.399M/4.499M VND/month | 1,000–34,000 | 10 |
  | Company | quote | 3,400–100,000 | 25 |

  - Free and Starter connect only VietinBank and MB.
  - The pricing table implies webhook/API from Pro upward, but also lists "custom webhook" from Starter. This is ambiguous.
  - A search-result summary of Casso documentation says the average time from bank transaction to webhook call is about 5 minutes (unverified) — [Casso blog](https://casso.vn/tich-hop-webhook-tuy-chinh-vao-casso/)

#### Open API banking (Circular 64/2024/TT-NHNN)
- Issued 31 Dec 2024 and effective 1 Mar 2025. Banks had to report their API list and plan by 1 Jul 2025 and must fully comply **before 1 Mar 2027**. The API groups are FX/interest-rate info, customer information, and payment initiation/e-wallet (search-result summary) — [ThuVienPhapLuat](https://thuvienphapluat.vn/van-ban/Tien-te-Ngan-hang/Thong-tu-64-2024-TT-NHNN-trien-khai-giao-dien-lap-trinh-ung-dung-mo-nganh-Ngan-hang-641360.aspx)
- For payment-initiation and e-wallet APIs, third parties must be "Ngân hàng, tổ chức cung ứng dịch vụ trung gian thanh toán" (banks or licensed payment intermediaries). Third parties must provide tools for customers to view their data, withdraw consent and understand the terms (article dated 24 Mar 2025) — [TLA Law](https://tlalaw.vn/quy-dinh-ve-open-api-trong-nganh-ngan-hang.tla)

#### E-invoices
- **MISA meInvoice**: "Mở cổng API, kết nối dữ liệu bên ngoài", integrated with 110+ accounting and POS systems, pricing "Chỉ từ 300đ/hóa đơn", with AI error detection and invoices from cash registers. The site claims compliance with Decree 70/2025 and with "Decree 254/2026 and Circular 91/2026/TT-BTC (effective 1 Jul 2026)" — [MISA meInvoice](https://www.meinvoice.vn/)
- **SePay e-invoice**: 100–600 VND per invoice (8% VAT excluded), e.g. 300 invoices for 180,000 VND or 200,000 invoices for 20M VND. An HSM digital signature costs 1,272,000 VND/year. SePay eShop bundles start at 50,000 VND/month — [SePay pricing](https://sepay.vn/bang-gia.html)

#### VNeID
- **Decree 320/2026/NĐ-CP** (effective 28 Sep 2026, amending Decree 69/2024) sets a mandatory deadline of **31 Dec 2026** for 11 sectors to link and authenticate user accounts with VNeID: education, securities, telecoms, banking (extended to 30 Jun 2027), **e-commerce, e-invoicing**, transport, tourism, **pharmaceuticals, healthcare**, among others, plus social media. Integration requires:
  - registration with the RAR/C06 Center
  - a site-to-site VPN
  - a VNeID Agent Gateway Server
  - API integration across dev, test and production
  - UAT
  - HSMs

  This is a vendor's reading dated 3 Sep 2026 — [SAVIS](https://savis.vn/han-chot-31-12-2026-11-linh-vuc-bat-buoc-lien-ket-xac-thuc-tai-khoan-voi-vneid/)
- **Third-party eKYC route**: VietQR documents an eKYC service using VNeID and chip-based CCCD via GTEL as authentication provider. It covers eID decoding, face matching and enterprise verification over mTLS 1.3 with IP whitelisting — [VietQR docs](https://doc.vietqr.vn/doc/hoa-don-vat-tu-dong/ekyc-xac-thuc-vneid)
- **Government direction on VNeID**: Decision 940/QĐ-TTg (26 May 2026) frames VNeID as a "super app", and Decision 1830/QĐ-TTg (22 Sep 2026) plans links with Singpass and LAeID (search-result summary) — [Báo Chính phủ](https://baochinhphu.vn/ke-hoach-ket-noi-vneid-voi-he-thong-dinh-danh-dien-tu-cac-nuoc-asean-102260922160815318.htm)

#### Telephony for voice agents
- **Stringee Call API** software fees: Standard plan 112 VND/min, Growth 104 VND/min, overage 150 VND/min, with a 30-day free trial. These fees **exclude carrier charges** — [Stringee pricing](https://stringee.com/vi/pricing-call)

### Inferences
- **A realistic integration set for a 7-week MVP**:
  - Zalo OA on Growth (2.5M VND/yr) with webhook-driven chat
  - ZBS templates for proactive notices
  - payOS or SePay for VietQR payment links and confirmation webhooks
  - MISA or SePay e-invoice API
  - optionally the Zalo Bot Platform free tier for prototyping before OA verification is done
- **Lead times**: OA verification and ZBS template approval take 2–3 business days per template. Start these in the first week of the MVP window.
- **Avoid direct VNeID, NAPAS or bank Open API integrations.** They are regulated, need licensing or C06 registration, and cannot be done in 7 weeks. Use licensed intermediaries (payOS/SePay/Casso; GTEL/VietQR eKYC; FPT/VNPT eKYC) and say so explicitly. "Ability to deploy immediately in reality" is more credible when it rests on intermediaries that already have bank and C06 relationships.
- If the startup's segment is e-commerce, e-invoicing, healthcare, pharma or education, the **VNeID account-linking mandate (31 Dec 2026)** may apply to the product itself. Treat this as a compliance roadmap item; it is also a possible agent use case (helping SMEs comply).
- For outbound engagement, Zalo/ZBS (consent-based, template-reviewed) is safer than robocalls or SMS given the 2026–27 spam rules (section 4).

### Gaps
- Zalo OA API technical documentation (token lifetime, webhook events, exact 48-hour/7-day rules) and Zalo Mini App publishing requirements and fees could not be extracted: developers.zalo.me and the Mini App pages render client-side.
- No Messenger per-message pricing was found in the policy page.
- E-invoice APIs for Viettel S-Invoice, VNPT Invoice, EasyInvoice and BKAV eHoaDon were not verified.
- The new invoice decree and circular cited by MISA ("Decree 254/2026", "Circular 91/2026/TT-BTC") were not independently verified.
- **eTax**: no information was found on whether third parties can access the tax authority's eTax system via API. This is likely limited to licensed T-VAN intermediaries, but that is unverified.
- Carrier per-minute termination fees (Viettel/VinaPhone/MobiFone) and hotline rental fees were not found.
- Casso's webhook latency and plan-level webhook availability are ambiguous.
- payOS's legal licensing status (intermediary payment licence) is not stated on its homepage.

---

## 4. Legal constraints in 2026 (PDPL and Decree 356/2025; Digital Technology Industry Law; AI Law 134/2025 and risk classes; spam/robocall rules; health and financial data)

### Takeaway
Three new laws now apply:
- **PDPL 91/2025/QH15**: personal data, in force from 1 Jan 2026.
- **Digital Technology Industry Law 71/2025/QH15**: industry incentives, in force from 1 Jan 2026.
- **AI Law 134/2025/QH15**: in force from 1 Mar 2026. It has three risk tiers and transparency duties, and it annulled the AI chapter of Law 71.

Enforcement is now real: Decree 330/2026 (effective 19 Aug 2026) fines consent failures at 30–70M VND and calls to Do-Not-Call numbers at up to 180M VND. A new anti-spam decree covering OTT apps such as Zalo is expected to take effect on 1 Jan 2027. Small enterprises and startups get a 5-year PDPL exemption, *but not if they process sensitive data* such as health or financial data, or more than 100,000 data subjects.

### Cited Findings

#### AI Law No. 134/2025/QH15
- Passed 10 Dec 2025 and **effective 1 Mar 2026**, with 35 articles — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html); [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-134-2025-qh15-468694.htm). It passed with 429 of 434 votes (90.70%) (search-result summary) — [MST](https://mst.gov.vn/quoc-hoi-thong-qua-luat-tri-tue-nhan-tao-hoan-thien-hanh-lang-phap-ly-cho-ky-nguyen-so-197251210165544671.htm)
- **Art. 9, risk tiers**:
  - **High**: may cause significant damage to life, health, rights and lawful interests, or national or public interests.
  - **Medium**: may confuse or manipulate users who cannot recognise they are interacting with AI or AI content.
  - **Low**: everything else.

  **Art. 10**: providers **self-classify** before deployment, and **medium- and high-risk systems must be notified to the Ministry of Science and Technology via a one-stop AI portal** — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html)
- **Art. 11, transparency**: users must be able to recognise they are interacting with AI. AI-generated audio, images and video must carry machine-readable marks, and deepfakes need visible labels — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html); [VnExpress, 4 Mar 2026](https://vnexpress.net/bon-diem-moi-trong-luat-tri-tue-nhan-tao-cua-viet-nam-5046036.html)
- **Art. 12, incidents**: serious incidents must be reported via the portal, and authorities may order suspension or recall. **Art. 14, high-risk obligations**: risk management, quality data, technical documentation, human supervision and intervention, and accountability information. Deployers must keep human intervention capacity — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html)
- **Liability**: deployers are liable for damage caused by high-risk systems even without fault, except where the user is at fault or force majeure applies, and can seek recovery from providers by contract — [Luật Việt An](https://luatvietan.vn/luat-tri-tue-nhan-tao.html)
- **Oversight intensity** scales with tier: high-risk systems get periodic inspection, medium-risk systems get sampling checks, and low-risk systems are reviewed only on incidents — [VnExpress](https://vnexpress.net/bon-diem-moi-trong-luat-tri-tue-nhan-tao-cua-viet-nam-5046036.html)
- **Classification factors**: purpose, sector, scope of impact, number of users, degree of automation and human-rights implications. A "Danh mục hệ thống trí tuệ nhân tạo có rủi ro cao" (high-risk list) has been issued, but its contents are not in the article (15 Jul 2026) — [MST](https://mst.gov.vn/luat-tri-tue-nhan-tao-dung-hang-rao-bao-ve-theo-muc-rui-ro-19726071423282963.htm)
- **Support measures**:
  - Art. 21: controlled sandbox, whose results can support recognition of conformity or exemption.
  - Art. 22: National AI Development Fund.
  - **Art. 25**: for startups and SMEs, support with conformity-assessment costs, free tools, training, priority access to the Fund, and **vouchers for compute, shared data, Vietnamese LLMs and consulting**.

  Source: [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html)
- **Art. 33** annuls Chapter IV (AI) and related clauses of Law 71/2025/QH15 on Digital Technology Industry. **Art. 35**: systems already operating before the law took effect must comply within **18 months** (health, education, finance) or **12 months** (other sectors) — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html)

#### Law on Digital Technology Industry No. 71/2025/QH15
- Dated 14 Jun 2025 and effective 1 Jan 2026. It covers the digital technology industry, semiconductors, AI and digital assets — [LuatVietnam EN](https://english.luatvietnam.vn/lawonthedigitaltechnologyindustryno71-2025-qh15datedjune142025ofthenationalassembly-405695-doc1.html)
- AI R&D and AI systems are sectors eligible for special investment incentives, and innovative startups get incentives under Art. 29 (search-result summary) — [ThuVienPhapLuat](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Luat-Cong-nghiep-cong-nghe-so-2025-so-71-2025-QH15-621341.aspx). Its AI chapter was annulled from 1 Mar 2026 by AI Law Art. 33 (see above).

#### Personal Data Protection Law No. 91/2025/QH15 and Decree 356/2025/NĐ-CP
- **PDPL effective 1 Jan 2026**. Decree 356/2025/NĐ-CP, issued 31 Dec 2025, replaces Decree 13/2023 from 1 Jan 2026 and covers DPIA, cross-border transfer, DPO, AI/blockchain/cloud processing, and financial and banking data — [LuatVietnam](https://luatvietnam.vn/linh-vuc-khac/luat-bao-ve-du-lieu-ca-nhan-moi-nhat-va-van-ban-huong-dan-883-106497-article.html); [Frasers, 19 Jan 2026](https://www.frasersvn.com/vi/legal-updates-and-publications/the-next-chapter-in-data-protection-new-decree-guiding-the-personal-data-protection-law). An earlier law-firm article said Decree 13/2023 would stay in force until implementing rules were issued, which has since been superseded — [GV Lawyers](https://gvlawyers.com.vn/luat-bao-ve-du-lieu-ca-nhan-2026/)
- **Sensitive data** includes health records, financial data, biometrics, precise location, and political and religious beliefs. Consent must be explicit, voluntary and transparent, with data minimisation. Data collected before 1 Jan 2026 needs fresh consent for new purposes. Breach notification is due within 72 hours. A DPO is required especially in healthcare, finance and education. Cross-border transfers require a dossier — [GV Lawyers](https://gvlawyers.com.vn/luat-bao-ve-du-lieu-ca-nhan-2026/). "Silence is not considered consent" — [LuatVietnam](https://luatvietnam.vn/linh-vuc-khac/luat-bao-ve-du-lieu-ca-nhan-moi-nhat-va-van-ban-huong-dan-883-106497-article.html)
- **Exemptions (Decree 356)**:
  - Household businesses and micro-enterprises: **permanent** exemption.
  - Small enterprises and startups: **5-year exemption from 1 Jan 2026**.
  - Exception: entities that process **sensitive data**, provide data-processing services, or handle **100,000 or more data subjects** must comply immediately.

  Source: [Frasers](https://www.frasersvn.com/vi/legal-updates-and-publications/the-next-chapter-in-data-protection-new-decree-guiding-the-personal-data-protection-law)
- **Other Decree 356 rules**:
  - **DPO criteria**: a tertiary degree, at least 2 years' relevant experience and PDP training.
  - **Data-subject requests**: acknowledge within 2 business days, then respond within 10–30 days depending on the request type.
  - The decree adds rules on data-processing services, including credit scoring, big data and AI processing, and blockchain.

  Source: [Frasers](https://www.frasersvn.com/vi/legal-updates-and-publications/the-next-chapter-in-data-protection-new-decree-guiding-the-personal-data-protection-law)
- **PDPL penalties**: up to 5% of annual revenue for cross-border violations, 10 times illegal gains for data trading, and up to VND 3 billion otherwise. Criminal liability applies to intentional data trafficking — [GV Lawyers](https://gvlawyers.com.vn/luat-bao-ve-du-lieu-ca-nhan-2026/); [LuatVietnam](https://luatvietnam.vn/linh-vuc-khac/luat-bao-ve-du-lieu-ca-nhan-moi-nhat-va-van-ban-huong-dan-883-106497-article.html)

#### Enforcement: Decree 330/2026/NĐ-CP (cybersecurity and personal data penalties, effective 19 Aug 2026)
- The decree has 4 chapters and 82 articles, and the limitation period is 1 year (search-result summary) — [ThuVienPhapLuat](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/119851/nghi-dinh-330-2026-nd-cp-xu-phat-hanh-chinh-ve-an-ninh-mang-va-bao-ve-du-lieu-ca-nhan-ra-sao)
- **Consent and data-handling fines**:
  - **30–50M VND**: processing without consent, bundling services with mandatory data processing, deceptive consent mechanisms, lack of transparency, or **not keeping consent logs**.
  - **50–70M VND**: continuing after a cessation request, or treating silence as consent.
  - Supplementary penalties include 1–24 months' suspension.

  Source: [Xây dựng chính sách – Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-dinh-330-2026-nd-cp-ve-xu-phat-vi-pham-hanh-chinh-trong-linh-vuc-an-ninh-mang-119260824172446407.htm). Processing beyond the permitted scope or purpose costs 20–40M VND for organisations, and individuals pay half (search-result summary) — [ThuVienPhapLuat](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-330-2026-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-an-ninh-mang-711716.aspx)
- **Spam and telemarketing under Decree 330 (Art. 37, as reported 25 Aug 2026)**:
  - Advertising calls are allowed only **08:00–17:00** and messages only **07:00–22:00**, at most **1 call and 3 messages/emails per recipient per 24 hours**.
  - Breaching these limits: 30–50M VND for individuals, up to 100M VND for organisations.
  - Calling or messaging **Do-Not-Call** numbers: 80–90M VND for individuals, **160–180M VND for organisations**.
  - Additional sanctions: 1–3 months' suspension and number revocation.

  Source: [Thương hiệu & Công luận](https://thuonghieucongluan.com.vn/quy-dinh-moi-siet-chat-cuoc-goi-rac-tiep-thi-trai-phep-bi-phat-toi-180-trieu-dong-a331827.html)

#### Spam and robocall regime: Decree 91/2020 [BACKGROUND] and its draft replacement
- Decree 91/2020/NĐ-CP has applied since 1 Oct 2020, replacing Decrees 90/2008 and 77/2012 [BACKGROUND] — [ThuVienPhapLuat](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-91-2020-ND-CP-chong-tin-nhan-rac-thu-dien-tu-rac-cuoc-goi-rac-427854.aspx)
- **Draft replacement**: the Ministry of Public Security published the draft on 8 Sep 2026 (search-result summary). Comments closed 18 Sep 2026 and it is **expected to take effect on 1 Jan 2027**. Key rules:
  - A single consent-request SMS between 7:00 and 22:00, which must include advertiser identity and opt-in/opt-out methods. **No reply within 24 hours counts as refusal.**
  - SMS ads only 7:00–22:00 and calls only 8:00–17:00, at most 3 SMS, 3 emails and 1 call per 24 hours.
  - A mandatory **Brandname** instead of a phone number.
  - The Do-Not-Call registry has about 9.5M registrations, more than 6M of them in 2025.

  Source: [VnExpress, 15 Sep 2026](https://vnexpress.net/bo-cong-an-de-xuat-nhieu-co-che-moi-chong-tin-nhan-cuoc-goi-rac-5120449.html)
- **Draft scope** extends to **OTT apps and internet messaging, calling and video**. It uses objective spam criteria: sending frequency, sender behaviour, ratio of two-way communication, outreach to people with no prior contact, and block or complaint rates. Providers must verify consent before marketing outreach. Do-Not-Call registration is via 5656 (22 Sep 2026) — [Doanh nghiệp Hội nhập](https://doanhnghiephoinhap.vn/du-thao-nghi-dinh-chong-tin-nhan-rac-cuoc-goi-rac-nhung-diem-moi-doanh-nghiep-va-nguoi-dan-can-luu-y-149589.html). It also creates a national anti-spam portal and reporting system — [Dân trí](https://dantri.com.vn/phap-luat/de-xuat-lap-cong-thong-tin-quoc-gia-chong-tin-nhan-cuoc-goi-rac-20260922084943265.htm)

#### Sector notes (health, finance)
- **Finance**: under Circular 64/2024, payment-initiation APIs are open only to banks and payment intermediaries — [TLA Law](https://tlalaw.vn/quy-dinh-ve-open-api-trong-nganh-ngan-hang.tla). Health, education and finance AI systems get the longer 18-month AI Law transition — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html). Health and financial data are "sensitive" under the PDPL — [GV Lawyers](https://gvlawyers.com.vn/luat-bao-ve-du-lieu-ca-nhan-2026/)
- **VNeID**: healthcare and pharma services are among the sectors that must link with VNeID by 31 Dec 2026 — [SAVIS](https://savis.vn/han-chot-31-12-2026-11-linh-vuc-bat-buoc-lien-ket-xac-thuc-tai-khoan-voi-vneid/)
- **Platform rules**: Messenger requires bots to disclose that they are automated — [Meta policy](https://developers.facebook.com/docs/messenger-platform/policy/policy-overview/)

### Inferences
- **Most student MVPs (SME assistants, customer-care, booking or finance-ops agents) will be "medium" or "low" risk** under the AI Law. The practical duties are:
  1. self-classification;
  2. AI disclosure in the first message or at the start of each call, e.g. "Em là trợ lý ảo AI của…";
  3. machine-readable marking of AI-generated audio and images;
  4. if medium-risk, notification via the MST portal.

  A product that makes or influences decisions on health, credit or recruitment risks being classed as high-risk (conformity assessment, logs, HITL, no-fault deployer liability). This argues for a "human approves" design.
- **PDPL is the binding constraint for health and fintech ideas.** Processing health or financial data removes the 5-year startup exemption. The team would then need a DPIA, a cross-border transfer dossier when sending data to US-hosted LLM APIs, a DPO meeting Decree 356 criteria, and consent logs (missing logs carry a 30–50M VND fine). The cheapest mitigations for an MVP are:
  - data minimisation;
  - masking or pseudonymising PII before LLM calls;
  - domestic hosting (FPT AI Factory, Viettel or VNPT) for sensitive fields;
  - an explicit consent screen in the Zalo Mini App or OA.
- **Outbound voice or SMS agents (callbots, telemarketing) are legally risky in 2026–27.** They face fixed time windows, 1 call per 24 hours, Do-Not-Call fines of up to 180M VND, and from 2027 likely also cover OTT channels. Inbound agents, or outbound messages that are transactional and opted-in (ZBS templates sent after a customer action), are much safer pitches.
- **Timing**: the anti-spam decree (1 Jan 2027) and the Gemini price change (1 Jan 2027) land inside the MVP window. The VNeID sector deadline (31 Dec 2026) and Circular 64 full compliance (1 Mar 2027) fall just around it. A pitch that names these dates and shows compliance-by-design will read as unusually current.

### Gaps
- The contents of the AI Law's high-risk list and the numbers of its implementing decrees and circulars were not extracted.
- It was not confirmed whether the startup exemption in Decree 356 also covers cross-border transfer dossiers, or only DPIA and DPO. The primary decree text was not fetched because ThuVienPhapLuat returned 403.
- The full Decree 330/2026 penalty table (cross-border transfer, data trading, AI-specific violations) was not extracted.
- It is unknown whether the spam draft explicitly regulates AI-generated or pre-recorded voice calls, and the final text is not yet issued.
- Health-sector rules beyond the PDPL (e.g., a decree on health data management, electronic medical record circulars) and State Bank rules on AI in finance (e.g., fintech sandbox decrees) could not be verified in this session.
- The VNeID obligations come from a vendor (SAVIS) reading of Decree 320/2026. The decree text was not fetched.

---

## 5. Unit economics: per-user monthly cost of an LLM agent with messaging and voice (worked examples), plus free credits and startup programmes

### Takeaway
At small scale, a Zalo-based text agent costs about **2,000–75,000 VND per active user per month** in LLM fees, depending on model tier. A typical mid-tier choice (Haiku 4.5, Gemini 3.8 Flash, gpt-5.4-mini) costs about 20,000–30,000 VND, to which ZBS notifications add about 2,400 VND. Voice adds roughly 2,000–9,000 VND per 6 call-minutes. A callbot doing 1,000 minutes a month costs about 0.36–0.73M VND before carrier fees. Fixed costs are small: Zalo OA Growth is about 208k VND/month and payment webhooks are free up to 30–50 transactions/month. Free credits (Gemini free tier; AWS Activate Founders up to $5k; Google Start up to $2k) easily cover the 7-week MVP, but most programmes require an incorporated company with a website.

### Cited Findings

#### Price inputs used below (all read 2026-10-04 unless the page shows a date)
- Claude: Haiku 4.5 $1 in / $0.10 cache hit / $5 out; Sonnet 5.5 $2 / $0.20 / $10; Opus 5.5 $4 / $0.20 / $20 — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- OpenAI: gpt-6-luna $0.10 / $0.01 cached / $0.50; gpt-6.1-sol $2 / $0.10 / $10; gpt-5.4-mini $0.75 / $4.50; gpt-realtime-2.1 audio $32 / $64; gpt-realtime-2.1-mini audio $10 / $20 — [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- Gemini: 3.8 Flash $0.75 / $3.75 until 31 Dec 2026, then $1.50 / $7.50; 3.5 Flash-Lite $0.30 / $2.50; 3.8 Live audio $0.005/min in and $0.018/min out — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- ZBS templates 200–300 VND (VAT excluded) — [ZBS pricing](https://zalo.solutions/business-message/pricing); OA Growth 2.5M VND/yr (VAT included) — [OA pricing](https://zalo.solutions/oa/pricing)
- Viettel AI STT 600 VND/min and TTS 320,000 VND per 1M characters [BACKGROUND, 2022] — [Viettel IDC](https://viettel-idc.com.vn/index.php/tin-tuc/tin-cong-nghe/bang-gia-dich-vu-viettel-ai-text-to-speech-speech-to-text-viettel-ai-61.html); Stringee 104–150 VND/min excluding carrier — [Stringee](https://stringee.com/vi/pricing-call)
- Payments: payOS free — [payOS](https://payos.vn/); SePay free for 50 transactions/month or 120k VND/month — [SePay](https://sepay.vn/bang-gia.html); Casso free for 30 transactions/month — [Casso](https://api.casso.vn/pricing-table)
- Claude Managed Agents: $0.08 per session-hour of runtime — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- Tokenizer note: Claude 4.7 and later produce about 30% more tokens for the same text — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)

#### Free credits and startup programmes
- **Google for Startups Cloud Program** — [Google for Startups Cloud](https://startup.google.com/cloud/):
  - **Start**: up to $2,000 over one year, for startups without equity funding founded within 5 years.
  - **Scale**: up to $100,000 in year 1 plus 20% of costs in year 2 (up to $100,000), for equity-funded startups founded within 10 years.
  - **AI startups**: up to $350,000 over two years.
  - All tiers require a billing account, a public company website and a company email domain matching the website.
- **AWS Activate** — [AWS Activate](https://aws.amazon.com/startups/credits):
  - **Founders**: up to $5,000 for self-funded startups.
  - **Portfolio**: up to $200,000, requiring an Organization ID from an Activate Provider (VC, accelerator or angel).
  - **AI startups**: $200,000+, invitation-only.
  - Credits can be used for Amazon Bedrock. Startups must be pre-Series B, founded within 10 years and on a paid-tier account.
- **Microsoft for Startups** advertises "up to $150,000 in credits" on Azure; eligibility details are not on the landing page — [Microsoft for Startups](https://www.microsoft.com/en-us/startups)
- **NVIDIA Inception** is free with no equity taken. It gives cloud credits from NVIDIA and partners, DLI courses, hardware and software discounts and VC exposure. Members must be officially incorporated, have at least one developer, an active website and be under 10 years old — [NVIDIA Inception](https://www.nvidia.com/en-us/startups/)
- **Model-provider credits**:
  - Anthropic gives new API users "a small amount of free credits" — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing). Its pricing page mentions a startup programme without terms — [claude.com/pricing](https://claude.com/pricing).
  - The Gemini API has a free tier for most Flash, Flash-Lite, Live and TTS models — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing).
  - Claude code execution includes 1,550 free hours per organisation per month — [Claude pricing docs](https://platform.claude.com/docs/en/about-claude/pricing).
- **Vietnamese levers**:
  - AI Law Art. 25 promises vouchers for compute, shared data and **Vietnamese LLMs** for startups and SMEs — [LuatVietnam EN](https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html).
  - FPT AI Factory has a "Startups Program" (terms not shown) — [FPT AI Factory](https://factory.fpt.ai/).
  - payOS's BIDV-1K offer gives 1,000 free transactions a year until 31 Dec 2026 — [payOS](https://payos.vn/).
  - VPBank gives 500 free SePay transactions a month for a year — [SePay](https://sepay.vn/bang-gia.html).

### Inferences

These worked examples are the researcher's own calculations. Assumptions are labelled, and all USD→VND conversions use 25,940.

**Example A: text agent on Zalo, per monthly active user (MAU)**
- **Assumptions (not sourced)**:
  - 60 agent tasks per month (about 2 per day).
  - 3 LLM calls per task (plan → tool → final answer), each with about 6,000 input tokens (system prompt, tool schemas, memory, recent history) and about 400 output tokens.
  - 70% of input tokens are prompt-cache hits where caching is priced; Gemini and gpt-5.4-mini are computed without cache credit.
- **Monthly volume**: 180 calls, 1.08M input tokens (756k cached plus 324k uncached) and 72k output tokens.

| Model | LLM cost per user per month |
|---|---|
| gpt-6-luna | 0.0324 + 0.0076 + 0.036 = **$0.076 ≈ 2,000 VND** |
| Gemini 3.5 Flash-Lite | 0.324 + 0.18 = **$0.50 ≈ 13,100 VND** |
| Claude Haiku 4.5 | 0.324 + 0.0756 + 0.36 = **$0.76 ≈ 19,700 VND**, plus a small cache-write premium |
| Gemini 3.8 Flash, 2026 price | **$1.08 ≈ 28,000 VND** |
| Gemini 3.8 Flash, from 1 Jan 2027 | **$2.16 ≈ 56,000 VND** |
| gpt-5.4-mini | 0.81 + 0.324 = **$1.13 ≈ 29,400 VND** |
| gpt-6.1-sol | 0.648 + 0.0756 + 0.72 = **$1.44 ≈ 37,500 VND** |
| Claude Sonnet 5.5 | 0.648 + 0.151 + 0.72 = **$1.52 ≈ 39,400 VND** |
| Claude Opus 5.5 | 1.296 + 0.151 + 1.44 = **$2.89 ≈ 74,900 VND** |

- **Messaging**: 8 ZBS "other" notices × 200 VND plus 2 OTP/payment-request templates × 300 VND = 2,200 VND, or **about 2,420 VND with 10% VAT**. Replies inside the 48-hour window are covered by the OA package.
- **Payment confirmation**: about 0 VND at MVP volume (payOS, or the SePay/Casso free tiers).
- **Pricing floor**: to keep variable AI and messaging cost at or below 30% of revenue, the monthly price per paying user would need to be about **14,600 VND** (gpt-6-luna), **51,600 VND** (Flash-Lite), **73,800 VND** (Haiku 4.5) or **139,400 VND** (Sonnet 5.5). A tiered router, with a cheap model by default and a large model only for planning or verification, keeps blended cost near the low end.

**Example B: voice add-on (6 call-minutes per MAU per month, agent speaking about 50% of the time)**

| Option | Cost for 6 minutes | Notes |
|---|---|---|
| Gemini 3.8 Live | 6 × $0.005 + 3 × $0.018 = **$0.084 ≈ 2,200 VND** | Excludes any per-turn context re-billing (unverified) |
| gpt-realtime-2.1-mini | **$0.108 ≈ 2,800 VND** | Assumes about 600 input-audio tokens per minute and 1,200 output-audio tokens per minute of agent speech (unverified for 2026 models) |
| gpt-realtime-2.1 | **$0.35 ≈ 9,000 VND** | Same token assumptions |
| Cascaded Vietnamese vendor (2022 list prices) | about **4,400 VND**, plus LLM (small) and Stringee 624–900 VND | Viettel STT 6 × 600 = 3,600 VND; TTS 3 min × about 800 chars per min (assumption) = 2,400 chars × 0.32 VND = about 770 VND; carrier fees unknown |

- **Callbot SME customer at 1,000 call-minutes per month**:
  - Gemini Live ≈ $5 + $9 = **$14 ≈ 363,000 VND**.
  - Viettel cascade ≈ 600,000 + 128,000 = **about 728,000 VND**.
  - Add Stringee software fees of about 104–150k VND plus carrier minutes.

  This suggests that voice SaaS pricing below about 1M VND/month per 1,000 minutes is hard to sustain.

**Example C: fixed monthly MVP running costs (excluding people)**
- Zalo OA Growth: 2.5M VND/yr ≈ **208k VND/month**.
- SePay Startup: 120k VND/month, optional because payOS is free.
- Template approvals: free.
- Search grounding: 5,000 free requests per month on Gemini.
- Hosting, domain and observability tooling: not priced in this research.

**Budget for the whole MVP pilot**: 50 pilot users on Sonnet 5.5 for 7 weeks (about 1.63 months) ≈ 50 × (39,400 + 2,420) × 1.63 ≈ **3.4M VND (about $131)**. That is well within free credits or the Gemini free tier. Cost is **not** a feasibility blocker; the binding constraints are integration lead times and legal design (sections 3 and 4).

**Eligibility caveat**: most credit programmes (Google, NVIDIA, AWS Portfolio) require an incorporated company, a website and a matching domain email. A student team without a company should rely on the Gemini free tier, Anthropic's trial credits, AWS Founders (self-funded) or university and competition partnerships. Incorporating early would unlock up to $2k (Google Start) and up to $5k (AWS Founders).

### Gaps
- Vietnamese tokenization overhead per word or syllable was not measured, and it may shift LLM costs by a meaningful factor.
- Gemini Live and OpenAI Realtime per-turn context billing for long sessions was not verified.
- Carrier per-minute fees for outbound and inbound calls in Vietnam were not found.
- Hosting/VPS prices in Vietnam and observability tool pricing (LangSmith, Langfuse) were not researched, as search budget ran out.
- Details of the Microsoft for Startups 2026 eligibility, Anthropic and OpenAI startup credit terms, FPT AI Factory startup programme terms, NIC (National Innovation Center) programmes, and implementation of the AI Law Art. 25 vouchers were not found.
- Whether Gemini free-tier data may be used by Google to improve products was not verified. This matters for PDPL when real user data is involved.

---

## 6. Vietnamese Agentic AI startups/products launched in 2025–2026 and AI-agent hackathons/competitions in Vietnam

### Takeaway
In Vietnam, "agentic AI" is now led by incumbents: VNPT AI's iSense Agentic CX, Viettel AI's agent ecosystem on a 120B model, FPT.AI's Agents and Voice Agent, and AI features in MISA. A new wave of startups is focusing on legal, compliance, DevOps, mental health and orchestration. The biggest 2026 competition signal is the **Âu Lạc Grand Prize** ($1M top prize; FPT, the Government Portal and VnExpress among organisers; finals in Nov 2026, awards in Dec 2026). It overlaps the TDTU MVP window and shows which themes judges reward. Business demand is high: 26% of Vietnamese businesses use AI and 46% of those surveyed plan to implement agentic AI.

### Cited Findings
- **Market data**: an AWS and Strand Partners study reports that 26% of Vietnamese businesses use AI (up from 18%), about 75,000 adopted AI in the past year ("8 businesses per hour"), and about 245,000 apply AI in total. 61% are still exploring or testing and 8% have integrated AI into core processes. **46% of surveyed businesses plan to implement agentic AI.** Vietnam has 42 commercial data centres (372 MW), 99.8% 4G coverage and 91.9% 5G coverage (29 Sep 2026) — [VnExpress](https://vnexpress.net/trung-binh-moi-gio-viet-nam-co-them-8-doanh-nghiep-ung-dung-ai-5126323.html)
- **Diaflow**, a Vietnamese AI-native orchestration platform built on Amazon Bedrock, has 40,000+ users, 75% of them in the US — [VnExpress](https://vnexpress.net/trung-binh-moi-gio-viet-nam-co-them-8-doanh-nghiep-ung-dung-ai-5126323.html)
- **VNPT AI's iSense Agentic CX Platform** (voice agents, VNPT LLM, RAG, emotion detection, SIP trunk) is deployed at VinaPhone with about 100k calls/day, 100% call QA (about 30M calls/yr) and about 5.8B VND saved in 2025. It can be deployed in the cloud, on-premise or hybrid (24 Sep 2026) — [CafeBiz](https://cafebiz.vn/vietnam-digital-finance-2026-agentic-ai-la-buoc-nhay-vot-tai-thiet-trai-nghiem-tai-chinh-so-176260924192827572.chn). The same article cites international benchmarks: 66% of customer-service organisations use AI agents, Klarna −25% repeat contacts, DoorDash −49% escalations.
- **Viettel AI** announced VT-Super-120B-A12B (June 2026) and an "AI Agent ecosystem for Vietnamese users", starting with a Legal AI Assistant — [CafeF](https://cafef.vn/cong-nghe-5-6-viettel-ai-tang-cuong-suc-manh-voi-mo-hinh-ngon-ngu-120b-tham-so-188260605074535525.chn)
- **FPT.AI**'s line-up includes FPT AI Agents, AI Chat, AI Engage, AI Mentor, AI Voice Agent, AI eKYC and AI Read. It claims 3,000+ enterprise clients, 16M+ end users and 200M+ automated interactions — [FPT.AI](https://fpt.ai/)
- **MISA meInvoice** markets AI invoice validation, error flagging, expense classification and anomaly alerts — [MISA meInvoice](https://www.meinvoice.vn/)
- **The Zalo Bot Platform** explicitly supports connecting AI agents to Zalo chats, with a free tier — [Zalo Bot Platform](https://bot.zaloplatforms.com/)
- **LEXcentra/LEXengine** (founder Dương Bảo Trung, a Harvard Law alumnus) is a legal AI assistant over 2M+ documents that emphasises evidence-cited answers ("AI phải dẫn được căn cứ để luật sư kiểm tra lại"). It is integrated into the National Legal Portal by the Ministry of Justice and is an Âu Lạc semifinalist (3 Oct 2026) — [VnExpress](https://vnexpress.net/cuu-sinh-vien-luat-harvard-xay-tro-ly-ai-cho-luat-su-viet-nam-5127539.html)
- **Âu Lạc Grand Prize 2026** — [VnExpress, 28 Sep 2026](https://vnexpress.net/15-giai-phap-ai-buoc-vao-cuoc-dua-gianh-giai-thuong-mot-trieu-usd-5125184.html):
  - **Organisers**: Âu Lạc AI Alliance, FPT, the Government Information Portal and VnExpress.
  - **Prize**: $1M for the top solution, with 400+ registrations.
  - **Timeline**: preliminary round Oct 2026, final Nov 2026, awards Dec 2026.
  - **15 finalists**: BioAI, Pathology AI Lab and Brain-Life (health/science); N2TP AI4Science Platform; 1Robot; CMC Video Miner; ViCore; CloudThinker VibeOps Platform; AesirX ComplianceOne and LEXcentra (legal/compliance); I Got AI and Murror (mental health); Volterra (energy); Egg Vision (agriculture); Onflow Vietnam (heritage).
- **Zalo AI Challenge**: a 2025 edition exists; tracks and dates were not extractable — [Zalo AI Challenge](https://challenge.zalo.ai/)
- **Other Vietnamese AI products in October 2026 news**: Creativehunts' "Nolan" content-optimisation tool (headline only) — [VnExpress](https://vnexpress.net/creativehunts-gioi-thieu-cong-cu-toi-uu-noi-dung-nolan-5127969.html)

### Inferences
- **Competitive white space for a student team**: incumbents (VNPT, Viettel, FPT) target enterprise call centres, government and banks with on-premise LLMs. A student MVP is more credible in **micro, small and household-business workflows on Zalo** (orders → VietQR payment → e-invoice → follow-up). It should combine cheap frontier models with Vietnamese payment and invoice rails, which incumbents serve with separate products rather than one autonomous agent.
- **Evidence-citing and human-verifiable outputs** (LEXcentra's "AI phải dẫn được căn cứ") are a recurring theme among Vietnamese winners. Building source-citation and verification steps into the agent aligns with what local judges are rewarding.
- **Âu Lạc finalist themes** (health, legal/compliance, DevOps/VibeOps, mental health, agriculture, energy) give a reading of what Vietnamese AI juries in 2026 consider high-impact. A TDTU pitch that connects to compliance (PDPL, AI Law, e-invoicing, VNeID deadline) or SME productivity is current.
- Incumbent-scale proof points can be used as "market validation" slides: VinaPhone's about 100k calls/day via iSense, the 46% agentic-AI intent figure, and FPT's 200M+ automated interactions.

### Gaps
- No systematic list of Vietnamese agentic-AI startups founded or launched in 2025–2026, nor their funding, could be compiled. The search budget was exhausted, and Tech in Asia and e27 were not reachable without search.
- No AI-agent-specific hackathons in Vietnam for 2025–2026 (e.g., by Google, AWS, NVIDIA, Viettel or universities) were verified beyond the Âu Lạc Grand Prize and the existence of Zalo AI Challenge 2025.
- The extent to which the listed incumbent products are truly "agentic" (autonomous multi-step tool use) rather than chatbots or voicebots is based on vendor descriptions, not technical review.
