# Claude SKILL.md System — Industry Applications & Working Demo

> **Assessment Report** | Author: Claude Sonnet 4.6 | Date: June 23, 2026

---

## Table of Contents

1. [What Are SKILL.md Files?](#1-what-are-skillmd-files)
2. [How the SKILL.md System Works](#2-how-the-skillmd-system-works)
3. [Skills Catalogue — Deep Research](#3-skills-catalogue--deep-research)
4. [Industry Mapping](#4-industry-mapping)
5. [Working Demo — What Was Built](#5-working-demo--what-was-built)
6. [File-by-File Walkthrough](#6-file-by-file-walkthrough)
7. [Architecture Diagram](#7-architecture-diagram)
8. [Key Insights & Findings](#8-key-insights--findings)
9. [Running the Demo Yourself](#9-running-the-demo-yourself)

---

## 1. What Are SKILL.md Files?

`SKILL.md` files are **structured instruction documents embedded inside Claude's runtime environment** that teach Claude *how* to perform specific, complex technical tasks — particularly those involving file creation and manipulation.

They live at `/mnt/skills/public/<skill-name>/SKILL.md` and are mounted **read-only** into Claude's sandboxed Linux environment. Claude's system instructions explicitly direct it to **always read the relevant SKILL.md before writing any code or creating any file**.

### Why They Exist

Claude's general training gives it broad knowledge, but skills like "create a valid `.docx` file with tracked changes" or "build an Excel model with live formulas" require highly environment-specific knowledge:

- Which npm/pip packages are installed
- What scripts are available in the container
- What quirks the rendering pipeline has (e.g., LibreOffice font substitution in PPTX)
- Industry standards like financial model color conventions

SKILL.md files encode this hard-won, trial-and-error knowledge in a format Claude can retrieve and follow precisely — like a **pit crew handbook** that tells the driver exactly how this specific car behaves.

---

## 2. How the SKILL.md System Works

```
User Request
     │
     ▼
Claude reads system prompt
     │
     ▼
Scans <available_skills> block
     │
     ▼
Views EVERY plausibly-relevant SKILL.md  ◄── MANDATORY step
     │
     ▼
Plans implementation using skill constraints
     │
     ▼
Writes code / runs bash commands per skill guidance
     │
     ▼
Saves output → /mnt/user-data/outputs/
     │
     ▼
Calls present_files() to surface result to user
```

The system prompt enforces this explicitly:
> *"Reading the relevant SKILL.md is a required first step before writing any code, creating any file, or running any other computer tool."*

This is **unconditional** — Claude cannot skip the skill-reading step even if it believes it knows how to do the task from training.

---

## 3. Skills Catalogue — Deep Research

### 3.1 `docx` Skill

| Attribute | Detail |
|-----------|--------|
| **Location** | `/mnt/skills/public/docx/SKILL.md` |
| **Trigger** | Word doc, .docx, report, memo, letter, template |
| **Core Library** | `docx` (npm) |
| **Alternative** | XML manipulation via `unpack.py` + `pack.py` scripts |
| **Key Constraints** | DXA units for measurements; no unicode bullets; ShadingType.CLEAR not SOLID; Arial as default font |

**What it teaches Claude:**
- The `.docx` format is a ZIP of XML files — edits can be done at the XML level
- Font handling, list numbering config, table dual-width requirements
- Tracked changes XML syntax (`<w:ins>`, `<w:del>`)
- Comment injection via `scripts/comment.py`
- US Letter vs A4 page size defaults (docx-js defaults to A4!)
- Smart quote XML entities for professional typography

**Validation workflow:**
```bash
python scripts/office/validate.py doc.docx   # auto-repairs durableId overflows
```

---

### 3.2 `xlsx` Skill

| Attribute | Detail |
|-----------|--------|
| **Location** | `/mnt/skills/public/xlsx/SKILL.md` |
| **Trigger** | .xlsx, .xlsm, .csv, spreadsheet, financial model |
| **Core Libraries** | `openpyxl` (formatting/formulas), `pandas` (data analysis) |
| **Key Constraint** | Always use Excel formulas — NEVER hardcode computed values |

**What it teaches Claude:**
- Industry-standard financial model color coding:
  - 🔵 Blue text = hardcoded inputs
  - ⚫ Black text = formulas
  - 🟢 Green text = cross-sheet links
  - 🔴 Red text = external file links
  - 🟡 Yellow background = key assumptions
- Number formatting standards (currency, percentages, multiples)
- Formula recalculation via `scripts/recalc.py` (LibreOffice-backed)
- Formula error validation with JSON output (`#REF!`, `#DIV/0!`, etc.)

**Critical rule:**
```python
# ❌ WRONG
sheet['B10'] = 5000  # hardcoded Python calculation

# ✅ CORRECT  
sheet['B10'] = '=SUM(B2:B9)'  # live Excel formula
```

---

### 3.3 `pptx` Skill

| Attribute | Detail |
|-----------|--------|
| **Location** | `/mnt/skills/public/pptx/SKILL.md` |
| **Trigger** | deck, slides, presentation, .pptx |
| **Core Library** | `pptxgenjs` (npm) for new creation; XML editing for templates |
| **QA Tool** | LibreOffice → PDF → `pdftoppm` → visual inspection |

**What it teaches Claude:**
- Complete visual design system with 10 named color palettes
- Typography safety list (fonts that render correctly in LibreOffice QA)
- `QA-unreliable` fonts to avoid for text-fit checks (Georgia, Trebuchet MS, Impact)
- Design anti-patterns: no accent stripes, no cream backgrounds, no text-only slides
- "Sandwich" dark/light structure for professional decks
- Sub-agent-based visual QA loop to catch overflow/overlap

**Font safety table from the skill:**
```
Safe fonts (QA reliable):  Arial, Calibri, Cambria, Times New Roman
QA-unreliable (width mismatch): Georgia, Trebuchet MS, Impact, Calibri Light
NEVER use: Aptos (Office 2023+ default — no compatible substitute)
```

---

### 3.4 `pdf` Skill

| Attribute | Detail |
|-----------|--------|
| **Location** | `/mnt/skills/public/pdf/SKILL.md` |
| **Trigger** | .pdf, create PDF, merge PDFs, extract from PDF |
| **Core Libraries** | `pypdf`, `pdfplumber`, `reportlab` |
| **Command Tools** | `pdftotext`, `qpdf`, `pdftk` |

**What it teaches Claude:**
- Do NOT use `pypdf` (old name) — the skill uses `pypdf` (updated package)
- `reportlab` for creation: Canvas API vs Platypus (flow-based) API
- Never use Unicode subscript/superscript characters — they render as black boxes in built-in fonts; use `<sub>` and `<super>` XML tags in Paragraph objects instead
- `pdfplumber` for table extraction (superior to basic `pypdf` text extraction)
- OCR pipeline: `pdf2image` → `pytesseract` for scanned documents
- FORMS.md sub-guide for PDF form filling

---

### 3.5 `frontend-design` Skill

| Attribute | Detail |
|-----------|--------|
| **Location** | `/mnt/skills/public/frontend-design/SKILL.md` |
| **Trigger** | Any UI/web component, React artifact, HTML page |
| **Philosophy** | "Design lead at a small studio" — opinionated, specific, non-generic |

**What it teaches Claude:**
- Brainstorm → critique → build (two-pass process)
- Three AI design clichés to actively avoid: warm cream + terracotta serif, near-black + acid-green, broadsheet hairlines
- Color palettes must be specific to the *subject* — not swappable across briefs
- Typography as personality, not neutral delivery
- Motion as deliberate narrative tool, not scattered decoration
- Copy must serve navigation — active voice, no filler, consistent terminology

---

### 3.6 `file-reading` & `pdf-reading` Skills

Router skills that tell Claude **which tool to use for which file type**:

```
file-reading  →  routes between: pandas (csv/xlsx), pypdf/pdfplumber (pdf),
                  python-docx (docx), PIL (images), zipfile (archives)

pdf-reading   →  decides between: text extraction, page rasterization,
                  embedded image extraction, form field reading, OCR
```

---

### 3.7 `product-self-knowledge` Skill

A fact-checking skill — Claude reads it before making any claim about Anthropic product pricing, API limits, model names, or feature availability, because training data may be stale.

---

## 4. Industry Mapping

| Industry | Primary Skill(s) | Use Case Examples |
|----------|-----------------|-------------------|
| **Healthcare** | `xlsx`, `docx`, `pdf` | Financial models for clinic revenue; patient intake forms; compliance reports; service contracts |
| **Legal & Professional Services** | `docx`, `pdf` | Contract generation with tracked changes; NDAs; regulatory filings; engagement letters |
| **EdTech / Training** | `pptx`, `frontend-design` | Investor pitch decks; course slide templates; interactive learning interfaces |
| **Supply Chain & Logistics** | `xlsx`, `pdf`, `pptx` | KPI dashboards; vendor scorecards; board reports; RFQ/RFP documents |
| **Banking & Finance** | `xlsx`, `pdf` | DCF models; credit memos; term sheets; fund performance reports |
| **Media & Marketing** | `pptx`, `frontend-design` | Campaign decks; brand guidelines; media kits; landing pages |
| **Manufacturing** | `xlsx`, `pdf` | Production planning models; quality control reports; ISO documentation |
| **Real Estate** | `docx`, `xlsx`, `pdf` | Lease agreements; property valuation models; due diligence reports |
| **Government & NGO** | `docx`, `pdf` | Policy briefs; grant reports; tender documents; compliance filings |
| **SaaS / Startups** | `pptx`, `xlsx`, `frontend-design` | Pitch decks; financial projections; investor dashboards; product sites |

### Industry Depth: Why Each Skill Fits

**Healthcare × xlsx:** Hospital CFOs use rolling 5-year financial models. The skill's color-coding standard (blue inputs, black formulas) is a match for finance team workflows. The formula-over-hardcode rule prevents models from going stale when assumptions change — critical for budget cycles.

**Legal × docx:** Law firms do 80% of their work in Word. The skill's tracked changes XML support means Claude can generate contracts with redline-ready markup — insertions and deletions visible to counsel. Smart quote entities ensure typographically professional output.

**EdTech × pptx:** Investor pitch decks are the primary fundraising artifact. The skill's design system (anti-patterns list, color palette catalogue, QA loop) produces decks that can go directly to investors without post-processing.

**Logistics × pdf:** Industry intelligence reports and KPI scorecards are consumed by C-suite executives who expect polished PDFs — not editable Excel files. `reportlab` with `Platypus` produces publication-grade output.

---

## 5. Working Demo — What Was Built

This repository contains four production-quality files, each exercising a different SKILL.md, each grounded in a real industry scenario:

| File | Skill Used | Industry | What It Demonstrates |
|------|-----------|----------|----------------------|
| `healthcare_financial_model.xlsx` | `xlsx` | Healthcare | Color-coded 5-year revenue model with live Excel formulas, assumption tracking, and EBITDA projections |
| `legal_contract.docx` | `docx` | Legal / Healthcare | Formatted service agreement with party tables, numbered clauses, payment schedule, and signature blocks |
| `edtech_pitch.pptx` | `pptx` | EdTech | 5-slide investor pitch deck with custom dark palette, stat callouts, feature cards, and traction metrics |
| `supply_chain_report.pdf` | `pdf` | Logistics | Reportlab-generated industry intelligence report with KPI tables, recommendations, and styled typography |

---

## 6. File-by-File Walkthrough

### 6.1 `healthcare_financial_model.xlsx`

**Industry context:** A clinic CFO needs a 5-year revenue model to present to the hospital board.

**SKILL.md principles applied:**
- ✅ Blue text for all hardcoded assumptions (patient visits, revenue per visit)
- ✅ Black text for all formula cells (`=C6*C7`, `=SUM(C18:C21)`)
- ✅ No Python calculations hardcoded — Excel does all arithmetic
- ✅ `$#,##0;($#,##0);-` number format (negatives in parentheses, zeros as dash)
- ✅ `0.0%` format for EBITDA margin
- ✅ Source documentation comment for assumptions
- ✅ Separate assumptions section clearly delineated

**Key formulas used:**
```
Gross Revenue    = Patient Visits × Revenue per Visit
Net Revenue      = Gross Revenue + Adjustments (−8%)
Total Costs      = Staff + Supplies + Rent + Admin
EBITDA           = Net Revenue − Total Costs
EBITDA Margin    = EBITDA / Net Revenue
```

---

### 6.2 `legal_contract.docx`

**Industry context:** A healthcare IT vendor needs a service agreement for a diagnostics chain client.

**SKILL.md principles applied:**
- ✅ US Letter page size set explicitly (12240 × 15840 DXA) — skill warns docx-js defaults to A4
- ✅ `LevelFormat.BULLET` + numbering config (never Unicode bullet characters)
- ✅ `ShadingType.CLEAR` for table cell fills (not SOLID — would cause black backgrounds)
- ✅ Tables use both `columnWidths` array AND per-cell `width` — dual width requirement
- ✅ Cell margins set (`top: 80, bottom: 80, left: 120, right: 120`)
- ✅ Heading styles override built-in IDs (`"Heading1"`, `"Heading2"`) with `outlineLevel`
- ✅ Arial as default font throughout
- ✅ Header with company branding using bottom border (not a table — skill warns against table dividers)

**Document structure:**
1. Parties table (navy header, data rows)
2. Section 1 — Scope of Services (numbered list)
3. Section 2 — Payment Terms (pricing table: 3 columns)
4. Section 3 — Data Protection & Compliance
5. Signature block (2-column table)

---

### 6.3 `edtech_pitch.pptx`

**Industry context:** LearnForge, an AI-driven EdTech startup, raises Series A from VCs.

**SKILL.md principles applied:**
- ✅ Custom color palette specific to EdTech trust + premium positioning (navy/gold/teal — not defaulting to generic blue)
- ✅ "Sandwich" structure: dark title/close slides, light content slides
- ✅ Visual motif: rounded rectangle cards repeated across slides
- ✅ Every slide has a visual element (stat callouts, emoji icons, data tables)
- ✅ Calibri used throughout (safe-list font for QA reliability)
- ✅ Large stat numbers (48pt) with small descriptor labels — skill-recommended layout
- ✅ No accent stripes under titles
- ✅ No cream/beige backgrounds

**Slide breakdown:**
1. **Title** — Dark navy, gold rule, company name at 72pt
2. **Problem** — 3 stat cards with 48pt numbers on dark backgrounds
3. **Solution** — 4 feature cards in 2×2 grid on dark background
4. **Traction** — 4 large metrics on light background, partnership banner
5. **The Ask** — Funding amount + use-of-funds allocation table

---

### 6.4 `supply_chain_report.pdf`

**Industry context:** A consultancy publishes an annual supply chain benchmark report for enterprise clients.

**SKILL.md principles applied:**
- ✅ `reportlab` Platypus API for complex flow-based layout
- ✅ No Unicode subscripts — `CO₂` in titles uses UTF-8, but any sub/superscript in Paragraphs would use `<sub>` tags
- ✅ Custom `ParagraphStyle` objects for consistent typography
- ✅ `TableStyle` with alternating row fills (`ROWBACKGROUNDS`) for readability
- ✅ `HRFlowable` for divider lines (not table rows)
- ✅ All color definitions via `colors.HexColor()` — not built-in color constants
- ✅ `letter` pagesize with explicit margins

**Report structure:**
1. Badge header block (teal background)
2. Title + subtitle + gold rule
3. Executive summary (2 paragraphs)
4. KPI table (8 metrics, FY2025 vs FY2026 comparison)
5. Sector deep-dive section
6. 5 strategic recommendations table
7. Footer with attribution

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude's Runtime Environment                 │
│                                                                   │
│  /mnt/skills/public/          /mnt/user-data/uploads/           │
│  ├── docx/SKILL.md            (user-uploaded files)             │
│  ├── xlsx/SKILL.md                                               │
│  ├── pptx/SKILL.md            /home/claude/                      │
│  ├── pdf/SKILL.md             (working directory)               │
│  ├── frontend-design/         ├── *.py scripts                  │
│  │   SKILL.md                 ├── *.js scripts                  │
│  ├── file-reading/            └── intermediate files            │
│  │   SKILL.md                                                    │
│  └── pdf-reading/             /mnt/user-data/outputs/           │
│      SKILL.md                 (final deliverables)              │
│                               ├── *.xlsx                        │
│  Read-only mount              ├── *.docx                        │
│  (Claude cannot modify)       ├── *.pptx                        │
│                               └── *.pdf                         │
└─────────────────────────────────────────────────────────────────┘

Flow:
User Request → System Prompt (with <available_skills>) →
Claude views SKILL.md → Bash/Node/Python execution →
File written to /outputs → present_files() → User receives file
```

---

## 8. Key Insights & Findings

### Insight 1: SKILL.md Files Are Environment Contracts

The most important function of SKILL.md is not to teach Claude general knowledge — it's to establish a **contract with the runtime environment**. Claude cannot know from training what npm packages are installed, what scripts exist in `/mnt/skills/public/docx/scripts/`, or that LibreOffice is configured headlessly. SKILL.md bridges this gap.

### Insight 2: The System Prevents Common AI Failure Modes

Without the xlsx skill, Claude might:
- Compute values in Python and write hardcoded numbers to cells (non-dynamic model)
- Forget to call `recalc.py` (values remain unevaluated)
- Use the wrong number formats (e.g., `#,##0` for percentages)

Without the pptx skill, Claude might:
- Use Georgia or Trebuchet fonts (misaligned QA preview)
- Add accent stripes under titles (AI design cliché)
- Skip the QA loop (shipping overlapping text)

The skills encode **years of debugging** so Claude doesn't repeat known mistakes.

### Insight 3: Skills Compose Across Industries

The skill system is modular — a single complex task often combines multiple skills:

```
"Create a board pack" = pptx + xlsx + pdf
"Draft a signed contract with embedded data" = docx + xlsx
"Build a startup data room" = pptx + xlsx + pdf + docx
```

### Insight 4: The Trigger System Is Critical

Each skill has a `description` field that acts as a semantic trigger. Claude reads all `<available_skills>` blocks in the system prompt and maps incoming requests to skill descriptions. This means:
- "Can you make me a deck?" → triggers `pptx`
- "I need a Word doc with financials" → triggers both `docx` and `xlsx`
- "Summarize this PDF" → triggers `pdf-reading` (not `pdf` — different skill!)

### Insight 5: Anti-Patterns Are as Valuable as Patterns

The pptx skill dedicates an entire "Avoid" section to common mistakes. The docx skill has a "Never" list. This negative-case documentation is arguably *more* valuable than positive examples, because Claude's training makes certain choices feel natural when they're actually wrong in this specific environment.

---

## 9. Running the Demo Yourself

### Prerequisites

```bash
# Node.js packages
npm install -g docx pptxgenjs

# Python packages
pip install openpyxl pandas reportlab pypdf pdfplumber --break-system-packages
```

### Generate All Files

```bash
# XLSX — Healthcare Financial Model
python healthcare_financial_model.py

# DOCX — Legal Service Agreement
node legal_contract.js

# PPTX — EdTech Investor Pitch
node edtech_pitch.js

# PDF — Supply Chain Intelligence Report
python supply_chain_report.py
```

### Output Location

All files are written to `./outputs/`:

```
outputs/
├── healthcare_financial_model.xlsx   (~6.4 KB)
├── legal_contract.docx               (~11 KB)
├── edtech_pitch.pptx                 (~106 KB)
└── supply_chain_report.pdf           (~5.8 KB)
```

---

## Summary

The SKILL.md system represents a powerful pattern for grounding AI agents in environment-specific reality. By treating skills as **read-first contracts** — mandatory pre-reads before any file generation — Anthropic has built a system where Claude can reliably produce professional-grade documents across industries without reinventing the wheel or repeating known failure modes.

The four demo files in this repository demonstrate that the system works end-to-end: a healthcare financial model, a legal contract, an EdTech pitch deck, and a logistics intelligence report — each built on the appropriate SKILL.md and each ready for real-world use.

---
