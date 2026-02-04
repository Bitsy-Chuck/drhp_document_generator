Got it — if you’re passing the **original DRHP as Markdown**, the system can treat that Markdown as the **authoritative structure + tone scaffold**, then **slot-fill** it using grounded facts from supporting docs.

Below is a concrete design for “extract structure from MD → build a template → populate it with evidence-backed facts → output drafted section”.

---

## Goal

Input:

* `drhp.md` (original DRHP in Markdown)
* `supporting_docs/` (PDF/XLSX/DOCX/TXT)

Output (single run):

* `out/Objects_of_the_Issue.md` (or whichever one section you choose)
* `out/intermediate/section_template.json` (structure extracted from MD)
* `out/intermediate/filled_slots.json` (slot→value→evidence)
* `out/annotations.jsonl` (sentence/number → evidence spans)
* `out/review_flags.md` (missing/uncertain/conflicting)

Key rule:

* **MD provides structure + boilerplate phrasing only.**
* **Facts must be grounded in supporting docs (and optionally DRHP MD only if you explicitly allow it).**
* Anything not grounded becomes `[[REQUIRES REVIEW]]`.

---

## End-to-end flow

### 0) CLI

```bash
python -m drhp_agent.run \
  --section objects \
  --drhp_md ./inputs/drhp.md \
  --supporting ./inputs/supporting_docs/ \
  --out ./out/
```

---

## 1) Parse the DRHP Markdown into a “structure tree”

### What we extract from MD

* Heading hierarchy (H1/H2/H3…)
* Paragraph blocks
* Tables (Markdown tables)
* Lists (numbered/bullets)
* Inline formatting is irrelevant, but we preserve it in rendering

### Implementation

Use a Markdown parser that yields an AST (e.g., `markdown-it-py` or `mistune`) and convert it to a normalized node tree:

**Intermediate artifact #1 (required): `section_template.json`**

```json
{
  "section_key": "objects",
  "nodes": [
    {
      "type": "heading",
      "level": 1,
      "text": "OBJECTS OF THE ISSUE",
      "children": [
        {
          "type": "paragraph",
          "text": "The objects of the Issue are ...",
          "slots": [
            {"slot_id": "S_intro_net_proceeds", "kind": "amount", "hint": "Net Proceeds"}
          ]
        },
        {
          "type": "table",
          "table_id": "T_utilization",
          "headers": ["Particulars", "Amount (₹ in Lakhs)", "% of Net Proceeds"],
          "rows": [
            [
              {"text": "Funding working capital requirements", "slots": []},
              {"text": "", "slots": [{"slot_id": "S_wc_amt", "kind": "amount"}]},
              {"text": "", "slots": [{"slot_id": "S_wc_pct", "kind": "percent"}]}
            ]
          ]
        }
      ]
    }
  ]
}
```

---

## 2) Convert the MD structure into a “slot template”

The MD likely contains:

* fixed boilerplate prose (“Pending utilization…”)
* factual items (amounts, dates, lenders, schedule)
* tables with numeric cells

You want the LLM to “extract structure and populate it”, but the safe way is:

1. extract structure **deterministically** (AST)
2. identify fillable **slots** using a hybrid approach (rules + LLM)

### Slot detection strategy

**A. Rule-based first (fast + reliable)**

* Detect currency strings: `₹`, `INR`, “lakhs”, “crores”
* Detect dates (DD/MM/YYYY etc.)
* Detect table numeric columns
* Detect patterns like “as of [date]”, “amounting to”, “shall be used for”

**B. LLM-based slot labeling (for messy prose)**
Run an “annotate-to-template” prompt on blocks:

* classify spans as:

  * `boilerplate` (keep as-is)
  * `fact_needed` (slot)
  * `company_specific_term` (slot or defined term)
* produce slot hints:

  * `type`: amount/date/text/entity
  * `expected_source`: “financial statements”, “capex quotation”, “WC certificate”, etc.

This produces the same `section_template.json` but now with slots.

---

## 3) Build an evidence-backed “Fact Store” from supporting documents

### Ingestion

Convert each supporting doc into:

* `doc_id`, `page`, `text`
* extracted tables (XLSX tables are native; PDFs via Camelot/Tabula; DOCX tables via python-docx)
* store “evidence spans” with stable locators:

  * `(doc_id, page, char_start, char_end)` or `(doc_id, sheet, row, col)`

### Indexing

* BM25 over chunks (fast keyword)
* embeddings over chunks (semantic)
* optional: table index by header names + column semantics

---

## 4) Slot Filling: map each slot → grounded value(s)

### Slot filling algorithm (per slot)

For each slot `S_xxx`:

1. **Retrieve candidates**

* query uses slot hint + surrounding MD text context
* e.g. “Net Proceeds”, “utilization”, “working capital”, “means of finance”

2. **Extract value(s)**

* If candidate is from a table: parse cell(s) deterministically
* Else: LLM extract-to-JSON from the chunk *with evidence span ids*

3. **Validate**

* type checks (amount/percent/date)
* reconcile totals:

  * sum(objects allocations) ≈ net proceeds (tolerance)
  * gross − expenses = net
  * percent columns consistent

4. **Decide**

* if exactly one strong candidate → fill
* if multiple conflicting candidates → fill with best + flag conflict
* if none → `[[REQUIRES REVIEW]]`

**Intermediate artifact #2 (required): `filled_slots.json`**

```json
{
  "S_wc_amt": {
    "value": 850.0,
    "unit": "lakhs",
    "evidence": [
      {"doc_id":"wc_certificate.pdf","page":2,"span":[1021,1104]}
    ],
    "confidence": 0.91
  },
  "S_intro_net_proceeds": {
    "value": null,
    "reason": "Not found in supporting docs",
    "confidence": 0.0
  }
}
```

---

## 5) Populate the MD structure and render the drafted section

### Rendering rules

* Keep headings exactly as in the source MD section (structure fidelity)
* Keep boilerplate paragraphs mostly unchanged (tone fidelity)
* Replace slot spans with formatted values:

  * `₹ 850.00 lakhs`
  * dates normalized to DRHP style

### Transparency in the output (mandatory)

Every filled fact should carry a marker:

* inline footnote / tag:

  * `₹ 850.00 lakhs [SRC:wc_certificate.pdf p2]`
* anything missing:

  * `[[REQUIRES REVIEW: Net Proceeds amount not found in supporting docs]]`

Also output `annotations.jsonl` mapping output spans to evidence spans.

---

## 6) “Extract the structure” from MD for only ONE chosen section

Even if the MD contains the whole DRHP, you should:

* detect section boundaries:

  * start at heading matching section title
  * end at next peer heading of same/higher level
* use that slice as the template for drafting

So the system can support:

```bash
--section objects
--section business_overview
--section risk_factors
```

---

## 7) Guardrails to prevent hallucinations

1. **No free-form “write a section” step**

* LLM is only used for:

  * slot identification
  * extraction-to-JSON from retrieved evidence chunks
  * optional: rewriting a paragraph *only using already-filled slots* (constrained)

2. **Fact registry**

* a paragraph renderer can only emit:

  * boilerplate text from template
  * filled slot values
  * explicitly flagged review placeholders

3. **Reconciliation checks**

* fail the run (or mark section as “needs review”) if:

  * critical totals inconsistent beyond threshold
  * a slot filled without evidence pointers

---

## Suggested repo layout (minimal but runnable)

```
drhp_agent/
  run.py
  md_template/
    parse_md.py          # md -> AST
    extract_section.py   # pick one section by heading
    slot_annotate.py     # rules + LLM to mark slots
  ingest/
    load_docs.py         # PDFs/DOCX/XLSX -> chunks + tables + evidence
  retrieve/
    index.py             # bm25 + embeddings
    search.py
  fill/
    slot_fill.py         # slot -> value -> evidence
    validate.py          # totals, types, consistency
  render/
    populate.py          # apply filled_slots to template tree
    to_markdown.py
    annotations.py
```

---

## What this buys you

* **Structure and tone match**: you literally reuse the DRHP MD skeleton.
* **Grounding is enforceable**: no slot value exists without evidence.
* **Reviewability is first-class**: missing/conflicts bubble up explicitly.
* **Intermediate artifacts exist**: template JSON + filled slots JSON + extracted tables.

---

If you want the design tightened further to “LLM extracts the structure” (instead of deterministic AST), you *can* do that—but I strongly recommend keeping **structure extraction deterministic** and using the LLM only to **label slots**, because headings/tables in Markdown are already machine-parseable and you’ll avoid a whole class of errors.

