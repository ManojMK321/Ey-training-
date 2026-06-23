# Orchestration pattern selection

Three scenarios, each matched against five orchestration patterns (Round-robin, Selector, Swarm/Handoff, GraphFlow, Magentic), with the selected pattern, justification, and a block diagram.

---

## 1. RFP response builder (Manufacturing)

> A bid response has four sections (technical, pricing, compliance, timeline), each owned by a specialist and assembled in order. A reviewer then checks the assembled draft and may send specific sections back for rework before final sign-off.

**Selected pattern: GraphFlow**

- Four named roles (technical, pricing, compliance, timeline) — a fixed, known set, not ad-hoc
- Sections must be **assembled in order** — needs an explicit sequence, not free-form handoff
- Reviewer can send **specific sections back** — needs a graph with conditional edges, not a one-way pipeline
- Close call: Swarm/Handoff — but handoff implies peers deciding who goes next; here the routing logic (which section, when, why) is pre-defined, which is a graph, not a negotiation

```
                              +---------------+
                              |  RFP request  |
                              +---------------+
                                      |
        +---------------+------------+------------+---------------+
        |               |                         |               |
        v               v                         v               v
  +-----------+   +-----------+            +-------------+   +-----------+
  | Technical |   |  Pricing  |            | Compliance  |   | Timeline  |
  |   agent   |   |   agent   |            |    agent    |   |   agent   |
  +-----------+   +-----------+            +-------------+   +-----------+
        |               |                         |               |
        +---------------+------------+------------+---------------+
                                      |
                                      v
                            +-------------------+
                            |     Assembler     |
                            | orders sections   |
                            |    into draft     |
                            +-------------------+
                                      |
                                      v
                            +-------------------+
                            |      Reviewer     |
                            | checks assembled  |
                            |       draft       |
                            +-------------------+
                                |          |
                     rework section      approved
                                |          |
                                v          v
                        (back to agent) +----------------+
                                         | Final sign-off |
                                         +----------------+
```

---

## 2. Claims adjudication (Insurance)

> A claim needs three independent checks — fraud screening, policy-coverage check, and medical-coding review — that can run at the same time. A final decision agent then combines all three results into an approve or deny.

**Selected pattern: GraphFlow (fork/join)**

- Three checks are explicitly **independent and run concurrently** — a known, fixed fan-out, not sequential handoff
- A single **final decision agent** merges all three — a defined join point, not an open-ended discussion
- Close call: Swarm/Handoff — sounds multi-agent, but Swarm passes control sequentially between peers with no built-in guarantee of parallelism or a structured merge; GraphFlow is purpose-built for fork/join graphs

```
                            +-----------------+
                            | Incoming claim  |
                            +-----------------+
                                     |
              +----------------------+----------------------+
              |                      |                       |
              v                      v                       v
      +---------------+      +---------------+       +---------------+
      |     Fraud     |      |    Coverage   |       |     Coding    |
      |   screening   |      |     check     |       |     review    |
      +---------------+      +---------------+       +---------------+
              |                      |                       |
              +----------------------+----------------------+
                                     |
                                     v
                          +----------------------+
                          |    Decision agent    |
                          | combines all results |
                          +----------------------+
                                     |
                                     v
                          +----------------------+
                          |   Approve or deny    |
                          +----------------------+
```

---

## 3. Buyer's research assistant (Retail)

> A merchandising team asks: 'Find three trending materials for outdoor furniture this season and summarise supplier options.' The number and type of sub-tasks isn't known in advance and may need web search and data lookups.

**Selected pattern: Magentic**

- Number and type of sub-tasks **isn't known in advance** — no graph can be pre-wired because the shape of the work isn't fixed
- Needs **web search and data lookups** decided on the fly — the planner figures out what's needed as it goes, not from a template
- Close call: GraphFlow — excellent when the steps are known ahead of time, but here the planner must *invent* the decomposition at runtime, which a static graph can't express

```
                      +--------------------------+
                      |     Open-ended task       |
                      | find trending materials   |
                      +--------------------------+
                                  |
                                  v
                      +--------------------------+
                      |         Planner          |
                      | decomposes task at        |
                      |        runtime            |
                      +--------------------------+
                        |          |           |
                  (dispatched dynamically, as needed)
                        |          |           |
                        v          v           v
                 +----------+ +----------+ +-----------+
                 |   Web    | | Supplier | |  Worker   |
                 |  search  | |  lookup  | |    n...   |
                 |  worker  | |  worker  | |           |
                 +----------+ +----------+ +-----------+
                        |          |           |
                        +----------+-----------+
                                  |
                                  v
                      +--------------------------+
                      |      Planner (synth)      |
                      +--------------------------+
                                  |
                                  v
                      +--------------------------+
                      |    Synthesized summary    |
                      +--------------------------+
```

---

## Summary table

| Scenario | Pattern | Why not the close call |
|---|---|---|
| RFP response builder | GraphFlow | Fixed roles + ordered assembly + targeted rework loop need explicit graph edges, not peer-decided handoff |
| Claims adjudication | GraphFlow (fork/join) | Concurrency and a defined merge step need a structured join, not sequential peer handoff |
| Buyer's research assistant | Magentic | Sub-task shape is unknown ahead of time, so it can't be pre-wired into any graph |
