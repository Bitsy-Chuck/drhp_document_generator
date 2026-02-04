"""LLM prompts for DRHP extraction and slot filling.

All prompts return structured JSON conforming to defined schemas.
"""

# =============================================================================
# FACT SCHEMA
# =============================================================================

FACT_SCHEMA = """
{
  "facts": [
    {
      "fact_id": "string - unique identifier, e.g., F001",
      "category": "string - one of: company_info, capital_structure, allotment, allottee, financial, date, signatory",
      "key": "string - normalized field name, e.g., authorized_share_capital",
      "value": "any - the extracted value (string, number, or structured object)",
      "value_type": "string - one of: amount, integer, percentage, date, text, entity, table_row",
      "unit": "string or null - e.g., INR, shares, lakhs",
      "raw_text": "string - exact text from document this was extracted from",
      "location": {
        "section": "string or null - section name/number if applicable",
        "table": "string or null - table name/id if from a table",
        "row": "string or null - row header/index if from table",
        "column": "string or null - column header if from table"
      },
      "confidence": "number 0-1 - how confident the extraction is"
    }
  ],
  "document_type": "string - detected type: board_resolution, list_of_allottees, pas3_form, other",
  "document_date": "string or null - primary date of the document if found"
}
"""

# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are a document extraction assistant specializing in Indian corporate filings.

Your task is to extract ALL factual information from the given document and return it as structured JSON.

## What to Extract

Extract every fact you can find, including but not limited to:
- Company information (name, CIN, address, email)
- Share capital details (authorized, issued, subscribed, paid-up)
- Allotment details (date, number of shares, face value, premium, issue price)
- Allottee information (names, addresses, shares allocated, amounts)
- Financial figures (amounts in INR, percentages)
- Dates (allotment dates, resolution dates, meeting dates)
- Signatories (names, designations, DIN numbers)
- Any tables with their complete data

## Output Format

Return ONLY valid JSON matching this schema:
{schema}

## Rules

1. Extract facts as they appear - do not calculate or derive new values
2. For amounts, preserve the original format (e.g., "15,09,120" not "1509120")
3. For tables, extract each row as a separate fact with table/row/column location
4. Set confidence to 1.0 for clearly stated facts, lower for ambiguous ones
5. If a value appears multiple times, extract each occurrence (they may differ)
6. Include the exact raw_text that the fact was extracted from
"""

EXTRACTION_USER_PROMPT = """Extract all facts from this document:

---
DOCUMENT: {filename}
---
{content}
---

Return the extracted facts as JSON matching the schema."""


# =============================================================================
# SLOT FILLING PROMPT
# =============================================================================

SLOT_FILL_SYSTEM_PROMPT = """You are a DRHP drafting assistant. Your task is to fill template slots using extracted facts.

## Input
- A template slot that needs to be filled
- A collection of extracted facts from supporting documents

## Output
Return JSON with the filled value and its source:

{{
  "slot_id": "string - the slot being filled",
  "status": "string - one of: filled, missing, conflict, low_confidence",
  "value": "any - the value to fill, formatted appropriately",
  "formatted_value": "string - display-ready formatted value",
  "source_facts": ["list of fact_ids used"],
  "source_files": ["list of source filenames"],
  "confidence": "number 0-1",
  "reason": "string - explanation, especially if missing or conflict"
}}

## Rules

1. Only use facts from the provided fact store - do not make up values
2. If multiple facts could fill the slot, check if they agree
   - If they agree: use the value, note all sources
   - If they conflict: status = "conflict", include all conflicting values in reason
3. If no relevant fact exists: status = "missing"
4. Format values appropriately for DRHP:
   - Amounts: Use Indian format with ₹ symbol (e.g., "₹ 3,00,000")
   - Dates: Use "DD Month YYYY" format (e.g., "15 May 2019")
   - Shares: Include "equity shares" suffix
5. For calculated fields (e.g., total = shares × face value), verify the calculation matches
"""

SLOT_FILL_USER_PROMPT = """Fill this template slot using the extracted facts.

## Slot to Fill
- Slot ID: {slot_id}
- Slot Type: {slot_type}
- Slot Hint: {slot_hint}
- Context: {slot_context}

## Available Facts
{facts_json}

Return JSON with the filled value and source."""


# =============================================================================
# SECTION GENERATION PROMPT
# =============================================================================

SECTION_GENERATE_SYSTEM_PROMPT = """You are a DRHP drafting assistant. Generate a Capital Structure section for a Draft Red Herring Prospectus.

## Style Requirements
- Use formal legal disclosure language
- Do NOT use marketing or promotional tone
- Do NOT summarize - state facts directly
- Follow standard DRHP section structure
- Every fact must have a source citation

## Citation Format
After each fact, add: [Source: filename]

## Missing Data
For any required information not available in the facts:
[[REQUIRES REVIEW: description of what's missing]]

## Output
Generate the complete section in Markdown format.
"""

SECTION_GENERATE_USER_PROMPT = """Generate the Capital Structure section using these filled slots:

## Company
{company_name}

## Filled Slots
{filled_slots_json}

## Source Documents
{source_files}

Generate the DRHP Capital Structure section in Markdown."""


# =============================================================================
# VALIDATION PROMPT
# =============================================================================

VALIDATION_SYSTEM_PROMPT = """You are a document validation assistant. Check extracted facts for consistency.

## Checks to Perform
1. Cross-document consistency (same fact should match across documents)
2. Mathematical consistency (totals should equal sum of parts)
3. Date consistency (dates should be logical)
4. Completeness (flag if critical facts are missing)

## Output
Return JSON:
{{
  "is_valid": boolean,
  "issues": [
    {{
      "severity": "info|warn|error|critical",
      "type": "inconsistency|math_error|missing|date_error",
      "message": "description of the issue",
      "facts_involved": ["fact_ids"],
      "suggestion": "how to resolve"
    }}
  ]
}}
"""

VALIDATION_USER_PROMPT = """Validate these extracted facts for consistency:

{facts_json}

Check for inconsistencies and return validation results as JSON."""
