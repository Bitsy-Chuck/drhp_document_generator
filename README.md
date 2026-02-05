# DRHP Section Drafting Agent

Generate Draft Red Herring Prospectus (DRHP) sections from supporting documents using LLM-powered fact extraction and slot filling.

## Quick Start

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=your-api-key-here

# Run the pipeline (module)
python -m drhp_agent.run \
  --template templates/capital_structure.md \
  --evidence supporting_docs/PAS-3/ \
  --out out/

# Or use the installed CLI entrypoint
drhp-agent \
  --template templates/capital_structure.md \
  --evidence supporting_docs/PAS-3/ \
  --out out/
```

## Requirements

- Python 3.11+
- Anthropic API key
- Anthropic SDK (`anthropic` Python package)

## Installation

```bash
# Install project dependencies
pip install -e .

# Install Anthropic SDK (required at runtime)
pip install anthropic

# Optional: dev/test tools
pip install ".[dev]"

# Run tests
python -m pytest tests/ -v
```

## Usage

### Single Command Execution

```bash
python -m drhp_agent.run \
  --template templates/capital_structure.md \
  --evidence supporting_docs/PAS-3/ \
  --out out/
```

### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--template` | Yes | Path to template markdown file |
| `--evidence` | Yes | Path to supporting documents directory |
| `--out` | Yes | Output directory for generated files |
| `--quiet` | No | Suppress progress output |
| `--log-level` | No | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all slots filled |
| 1 | Success with review flags - some slots need human attention |
| 2 | Error - pipeline failed |

## Output Files

```
out/
├── capital_structure.md       # Generated DRHP section
├── annotations.jsonl          # Fact-to-source mappings
├── review_flags.md            # Items needing human review
├── manifest.json              # Run metadata
├── pipeline.log               # Pipeline logs
└── intermediate/
    ├── fact_store.json        # All extracted facts
    ├── section_template.json  # Parsed template slots
    ├── filled_slots.json      # Slot fill results
    ├── elaborations.json      # Elaboration results (if present)
    └── validation.json        # Validation results
```

## How It Works

1. **Document Ingestion**: Recursively loads all `.md` files from the evidence directory
2. **Fact Extraction**: Sends each document to LLM to extract structured facts
3. **Template Parsing**: Detects `{{type:slot_name:hint}}` markers in template
4. **Slot Filling**: Uses LLM to match facts to template slots
5. **Elaboration**: Generates text for `{{elaborate:block_id:hint}}` blocks (if any)
6. **Validation**: Checks fact consistency across documents
7. **Rendering**: Replaces slots/blocks with values, adds citations, flags missing data

## Template Slot Syntax

Slots use the format `{{type:slot_name:hint}}`:

- `{{text:company_name:Full legal company name}}`
- `{{integer:authorized_shares:Number of authorized shares}}`
- `{{amount:face_value:Face value per share}}`
- `{{date:incorporation_date:Date of incorporation}}`
- `{{percentage:shareholding_percent:Percentage holding}}`

Simple slots without type default to text: `{{simple_slot}}`

Elaboration blocks use the format `{{elaborate:block_id:hint}}`:

- `{{elaborate:share_capital_summary:Summarize the share capital changes}}`

## Sample Data

The `supporting_docs/PAS-3/` directory contains sample PAS-3 (Return of Allotment) documents for **Nexus Brightlearn Solutions Private Limited**:

- `Board Resolution Allotment of Shares.md` - Board minutes approving share allotment
- `List of Allottees.md` - Details of share recipients
- `PAS-3 Form.md` - Regulatory filing with ROC

## Project Structure

```
drhp_agent/
├── core/           # Data types, enums, exceptions
├── ingest/         # Document loading and fact extraction
├── llm/            # LLM client (Anthropic Claude)
├── md_template/    # Template parsing
├── fill/           # Slot filling
├── validate/       # Fact validation
├── render/         # Section rendering
├── run/            # CLI and orchestrator
└── prompts.py      # LLM prompt templates
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_template_parser.py -v
```

## License

MIT
