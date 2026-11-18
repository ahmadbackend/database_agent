# Pharmacy Invoices — Multi-Branch Management with AI Data Assistant

A Django app for a multi-branch pharmacy group: branches, supervisors, sellers,
products and invoices — plus a **read-only AI assistant in the Django admin**
that answers natural-language questions ("Who is the best seller this month?")
using a local [Ollama](https://ollama.com) model. No data ever leaves the machine.

## Features

- **Multi-branch data model** — one supervisor manages many branches, one branch
  has many sellers, one invoice holds many sold products (through `InvoiceItem`
  with quantity and unit price).
- **Full Django admin** — invoice line items editable inline, list filters and
  search on every model.
- **Dummy data loader** — one management command seeds the database from a
  single CSV file.
- **AI data assistant** (`/admin/pharmacy/assistant/`) — text-to-SQL over
  reporting views, hardened at every level (see Security below).

## Tech stack

- Python 3.11+ / Django 5.2 / SQLite
- Ollama (local LLM server) with `qwen2.5-coder:7b`
- `sqlparse` for SQL validation, `requests` for the Ollama HTTP API

## Project structure

```
invoices/                 # Django project settings
pharmacy/                 # main app
├── models.py             # Supervisor, Branch, Seller, Product, Invoice, InvoiceItem
├── admin.py              # admin registrations + assistant view (/admin/pharmacy/assistant/)
├── data/dummy_data.csv   # seed data (one row per sold product line)
├── management/commands/load_dummy_data.py
├── migrations/0002_reporting_views.py   # creates the 3 reporting views
└── assistant/            # the AI assistant
    ├── prompt.py         # view schemas + few-shot examples sent to the LLM
    ├── ollama_client.py  # HTTP client for the local Ollama server
    ├── validate.py       # SQL validation gate (see Security)
    └── service.py        # question -> SQL -> validate -> execute -> summarize
```

## Setup

```bash
git clone https://github.com/ahmadbackend/database_agent
cd invoices
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py load_dummy_data     # optional: seed demo data
python manage.py createsuperuser
python manage.py runserver
```

Admin: http://127.0.0.1:8000/admin/

### Ollama (for the AI assistant)

```bash
# install from https://ollama.com, then:
ollama pull qwen2.5-coder:7b
```

Settings in `invoices/settings.py`:

| Setting | Default | Notes |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | any pulled model works |
| `OLLAMA_NUM_GPU` | `0` | GPU layers. **Keep `0` (CPU)** — GPU inference on this machine corrupts tokens. Set `-1` only after verifying output with updated GPU drivers. |

## Usage

- **Data entry**: standard Django admin (invoices with inline line items).
- **AI assistant**: open `/admin/` — a chat widget sits in the bottom-right
  corner of the admin home page. Ask, e.g.
  - "Who is the best seller this month?"
  - "Which branch made the most revenue today?"
  - "Top 5 best selling products this year?"
  - "Which products expire in the next 90 days?"
- **Reload seed data**: `python manage.py load_dummy_data [--csv path/to/file.csv]`
  (idempotent — safe to run repeatedly).

## Security: how the assistant stays read-only

The LLM never touches the database directly; it only outputs SQL text, which
must pass three independent layers:

1. **Prompt** — the model only knows about 3 reporting views
   (`v_sales_detail`, `v_product_stock`, `v_branch_sellers`), never raw tables.
2. **Validation gate** (`assistant/validate.py`) — rejects anything that is not
   exactly one `SELECT`; blocks write/introspection keywords (`INSERT`, `DROP`,
   `PRAGMA`, `ATTACH`, `sqlite_*`, …); every referenced table must be in the
   view allowlist; a `LIMIT 500` is enforced.
3. **Database** — queries run on a dedicated connection opened with SQLite
   `mode=ro`, so the driver itself refuses writes even if a query slipped through.

One request produces at most one executed statement; on validation or database
errors the model gets up to 2 self-correction attempts before failing cleanly.
