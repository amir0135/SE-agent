# Chief of Staff — Architecture & Decision Flow

Two views: the **system architecture** (what connects to what) and the **decision flow**
(how a single signal is routed). Both render in VS Code / GitHub. An Excalidraw source is
also provided at [architecture.excalidraw](./architecture.excalidraw) for export to PNG.

## 1. System architecture

```mermaid
flowchart TB
    subgraph SIGNALS["① SIGNALS (perceive)"]
        OUT["Outlook<br/>mail, flags, deadlines"]
        CAL["Calendar<br/>meetings, gaps, focus"]
        TEAMS["Teams<br/>pod chats, @-mentions"]
        MSX["MSX / Dynamics<br/>opps, milestones"]
    end

    subgraph BRAIN["CHIEF OF STAFF (Copilot Studio orchestrator)"]
        PERCEIVE["Normalize → Signal"]
        DECIDE["② DECIDE<br/>priority rubric<br/>P1 win ▸ P2 pod/mgr ▸ P3 compliance ▸ P4 hygiene ▸ noise"]
        DELEGATE["③ DELEGATE<br/>pick worker(s), run parallel, stitch"]
        REPORT["④ REPORT<br/>brief · pings · wrap-up"]
        PERCEIVE --> DECIDE --> DELEGATE --> REPORT
    end

    subgraph WORKERS["WORKERS (Azure AI Foundry agents, called as tools)"]
        AI["Account Intelligence"]
        DEMO["Demo Builder"]
        ENV["Envisioning Prep"]
        PIPE["Pipeline/MSX<br/>(MSX Helper app via MCP)"]
        COMP["Compete"]
    end

    subgraph GOV["GOVERNANCE"]
        ENTRA["Entra Agent ID"]
        PURVIEW["Purview / Defender"]
    end

    USER(["👤 User<br/>brief + approval taps only"])

    SIGNALS --> PERCEIVE
    DELEGATE --> AI & DEMO & ENV & PIPE & COMP
    PIPE -. "MCP (streamable-http)<br/>reads / draft writes" .-> MSX
    REPORT --> USER
    USER -. Approve / Edit / Skip .-> DELEGATE
    BRAIN --- GOV
```

## 2. Decision flow (one signal)

```mermaid
flowchart TD
    S["New signal<br/>(mail / meeting / Teams / MSX)"] --> Q1{"Q1: Customer /<br/>technical-win signal?"}

    Q1 -- "POC / arch / pricing" --> TW["P1 · TECHNICAL_WIN<br/>fire Demo Builder + Envisioning Prep<br/>draft reply → APPROVE-FIRST"]
    Q1 -- "new customer meeting" --> MP["P1 · MEETING_PREP<br/>Account Intelligence<br/>1-page brief 24h before (AUTO)"]
    Q1 -- "no" --> Q2{"Q2: Pod / v-team<br/>or manager ask?"}

    Q2 -- "specialist ping" --> PO["P2 · POD_ORCHESTRATION<br/>draft Teams reply + check MSX milestone"]
    Q2 -- "manager 1:1" --> MG["P2 · MANAGER_PREP<br/>Pipeline/MSX numbers + talking points<br/>APPROVE-FIRST if sent to mgr"]
    Q2 -- "no" --> Q3{"Q3: Compliance /<br/>admin deadline?"}

    Q3 -- "training / quota / attestation" --> CD["P3 · COMPLIANCE_DEADLINE<br/>block focus time + remind (AUTO)"]
    Q3 -- "no" --> Q4{"Q4: Pipeline risk?<br/>(UC 14+ days, stale)"}

    Q4 -- "yes" --> PR["P4 · PIPELINE_RISK<br/>flag + suggested next action<br/>MSX draft (AUTO), commit APPROVE-FIRST"]
    Q4 -- "no" --> NZ["NOISE<br/>summarize / file / archive<br/>never interrupt"]

    TW --> STAGE["Stage in brief / approval queue"]
    MP --> STAGE
    PO --> STAGE
    MG --> STAGE
    CD --> STAGE
    PR --> STAGE
    NZ --> BRIEF["Roll into brief (FYI) or silently archive"]
```

## 3. Autonomy gate (applied before any outbound action)

```mermaid
flowchart LR
    A["Prepared action"] --> G{"Crosses a<br/>guardrail?"}
    G -- "customer msg /<br/>committed MSX /<br/>manager+leadership" --> AF["APPROVE-FIRST<br/>stage → wait for tap"]
    G -- "research / brief /<br/>calendar block /<br/>draft / archive" --> AU["AUTO<br/>do it now"]
    AF --> TAP(["👤 Approve / Edit / Skip"])
    TAP --> DONE["Execute on Approve"]
    AU --> DONE
```
