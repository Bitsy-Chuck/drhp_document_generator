# DRHP Drafting Agent - Document Knowledge

## PAS-3 Document Set

Location: `supporting_docs/PAS-3/`

These are ROC (Registrar of Companies) filings for share allotment events. Use them as evidence to populate the Capital Structure section of a DRHP.

---

## Document Schemas

### 1. Board Resolution Allotment of Shares.md

**How to read**: Single continuous document. Header contains company info, body contains resolution text with embedded table.

```yaml
schema:
  header:
    company_name: string  # First line, all caps
    address: string       # Second line

  resolution_metadata:
    meeting_type: "BOARD OF DIRECTORS"
    date: date            # Parse from "HELD ON {weekday}, {date}"
    location: string      # After "AT THE REGISTERED OFFICE"
    time: time            # End of header line "AT {time}"

  resolution_title: string  # Line starting with "ALLOTMENT OF..."

  resolution_body:
    section_reference: string    # "Section 62(1) of the Companies Act, 2013"
    shares_allotted: integer     # Number in parentheses with words
    face_value: amount           # "face value INR {amount}"
    issue_price: amount          # "at INR {amount}...per share"
    premium: amount              # "share premium of INR {amount}"

  allottee_table:                # Markdown pipe table
    columns:
      - name_of_allottee: string
      - no_equity_share: integer
      - folio_no: string
      - share_certificate_number: string
      - distinctive_numbers: string  # Format: "{start}-{end}"

  further_resolutions: list[string]  # Each "RESOLVED FURTHER THAT..." block

  signatory:
    name: string
    designation: string
    din: string  # Director Identification Number
```

**Parsing notes**:
- Table uses `<br />` for line breaks in cells
- Numbers may include words in parentheses: "960 (Nine Hundred and Sixty)"
- Premium embedded in parenthetical: "(inclusive of a share premium of INR X)"

---

### 2. List of Allottees.md

**How to read**: Two tables (A and B). Table A is metadata, Table B is the actual allottee list.

```yaml
schema:
  header:
    company_name: string
    address: string
    document_title: "List of Allottees"

  table_a:  # Markdown pipe table - key-value pairs
    fields:
      - name_of_company: string
      - date_of_allotment: date
      - type_of_share: enum[Equity, Preference]
      - nominal_value_per_share: amount
      - premium_per_share: amount
      - total_allottees: integer_or_word  # "Three"
      - terms_and_conditions: string

  table_b:  # HTML <table> - allottee details
    columns:
      - sr_no: integer
      - name_and_occupation: string      # May have line breaks
      - address: string                   # Multi-line with <br /> or newlines
      - nationality: string
      - no_of_shares_allotted: integer
      - total_amount_paid: amount         # Indian format: "15,09,120"
      - amount_outstanding: amount|"Nil"

    has_total_row: true  # Last row contains "TOTAL" with sums

  signatory:
    name: string
    designation: string
    din: string
```

**Parsing notes**:
- Table A uses markdown pipe format
- Table B uses raw HTML `<table>` tags
- Addresses span multiple lines with inconsistent delimiters
- Amount format is Indian lakh system (XX,XX,XXX)

---

### 3. PAS-3 Form.md

**How to read**: Multi-page regulatory form. Sections numbered 1-9. Key data in sections 1, 3, 7.

```yaml
schema:
  form_header:
    form_number: "PAS-3"
    form_title: "Return of Allotment"
    legal_reference: string  # Section and rule citations
    language: enum[English, Hindi]

  section_1_company_info:
    cin: string              # Corporate Identity Number, field 1(a)
    gln: string|null         # Global Location Number, field 1(b)
    company_name: string     # Field 2(a)
    registered_address: string  # Field 2(b)
    email: string            # Field 2(c)

  section_3_securities_cash:  # HTML <table>
    number_of_allotments: integer
    per_allotment:
      date_of_allotment: date
      shareholders_resolution_date: date|null
      mgт_14_srn: string|null

    securities_table:        # Multi-column, one row per security type
      columns:
        - particulars: string
        - preference_shares: amount|null
        - equity_shares_without_differential: amount|null
        - equity_shares_with_differential: amount|null
        - debentures: amount|null
      rows:
        - brief_particulars_terms
        - number_of_securities_allotted
        - nominal_amount_per_security
        - total_nominal_amount
        - amount_paid_per_security_on_application
        - total_amount_paid_on_application
        - amount_due_on_allotment
        - total_amount_paid_on_allotment
        - premium_per_security
        - total_premium_due
        - premium_paid_per_security
        - total_premium_paid
        - discount_per_security
        - total_discount
        - amount_on_calls_per_security
        - total_amount_on_calls

  section_4_securities_non_cash:  # Similar structure, usually empty
    # Same table structure as section_3

  section_5_bonus_shares:
    date_of_allotment: date|null
    number_of_bonus_shares: integer|null
    nominal_amount_per_share: amount|null
    # Usually empty for cash allotments

  section_6_private_placement:
    category: list[enum]  # Checkboxes
    declarations: list[checkbox]  # Compliance declarations

  section_7_capital_structure:  # HTML <table> - CRITICAL FOR DRHP
    columns:
      - particulars: string
      - authorized_capital: amount
      - issued_capital: amount
      - subscribed_capital: amount
      - paid_up_capital: amount
    rows:
      - number_of_equity_shares
      - nominal_amount_per_equity_share
      - total_amount_equity_shares
      - number_of_preference_shares
      - nominal_value_per_preference_share
      - total_amount_preference_shares
      - unclassified_shares
      - total_amount_unclassified
      - total

  section_8_debt_structure:  # HTML <table>
    columns:
      - particulars: string
      - total_securities: integer
      - nominal_value_per_unit: amount
      - total_amount: amount
    rows:
      - debentures
      - secured_loans
      - others

  section_9_attachments:
    list_of_allottees_attached: boolean
    board_resolution_attached: boolean
    optional_attachments: list[string]

  declaration:
    resolution_number: string
    resolution_date: date
    signatory:
      name: string
      designation: string
      din_or_pan: string
    digital_signature_date: datetime

  professional_certificate:  # Optional
    professional_type: enum[CA, Cost Accountant, CS]
    membership_number: string
    cop_number: string
```

**Parsing notes**:
- Page breaks marked with `---` and "Page X of Y"
- Tables are HTML `<table>` format
- Checkboxes: `☑` (checked), `[ ]` or `○` (unchecked)
- Many fields are empty/null - this is normal
- Section 7 contains the capital structure summary needed for DRHP

---

## Cross-Document Validation Rules

```yaml
validation:
  shares_allotted_consistency:
    - board_resolution.shares_allotted == list_of_allottees.table_b.sum(no_of_shares)
    - board_resolution.shares_allotted == pas3_form.section_3.number_of_securities_allotted

  amount_consistency:
    - list_of_allottees.table_b.sum(total_amount_paid) == pas3_form.section_3.total_amount_paid + total_premium_paid

  date_consistency:
    - board_resolution.date == list_of_allottees.table_a.date_of_allotment
    - board_resolution.date == pas3_form.section_3.date_of_allotment

  allottee_count:
    - list_of_allottees.table_a.total_allottees == count(list_of_allottees.table_b.rows) - 1  # minus total row
```

---

## Extraction Priority for Capital Structure DRHP Section

| Data Point | Primary Source | Fallback Source |
|------------|----------------|-----------------|
| Authorized capital | PAS-3 Form §7 | - |
| Issued/Paid-up capital | PAS-3 Form §7 | - |
| Face value per share | PAS-3 Form §7 | Board Resolution |
| Share allotment history | Board Resolution | List of Allottees Table A |
| Allottee details | List of Allottees Table B | Board Resolution table |
| Premium per share | Board Resolution | List of Allottees Table A |
| Total consideration | List of Allottees Table B (total row) | Calculate from unit price × shares |
