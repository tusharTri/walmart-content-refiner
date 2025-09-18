# walmart-content-refiner

A minimal FastAPI-based service to refine Walmart product content in batch or via API.

## Structure
- `app/`: FastAPI app, services, models, and routes
- `tests/`: Unit tests
- `run_batch.py`: Batch runner for CSV input
- `sample_input.csv`: Example input file

## Tech stack
- **Python**: 3.10+
- **Backend**: FastAPI + Uvicorn
- **Data**: pandas for CSV/DataFrame operations
- **LLM**: OpenAI-compatible Chat Completions or Chat API (via `OPENAI_API_KEY`)
- **Validation & models**: pydantic
- **Tests**: pytest
- **Local config**: python-dotenv (`.env`)
- **Containerization**: Docker (`python:3.10-slim` base)
- **Optional UI**: Streamlit for quick demo; React + Tailwind or Next.js for production UI

## Project overview
- **Input**: CSV with columns `{brand, product_type, attributes (JSON string), current_description, current_bullets}` (see `sample_input.csv`).
- **Goal**: For each row, generate:
  - Walmart-safe title
  - HTML key features (as `<ul><li> ... </li></ul>`) or as a list of 8 bullets
  - Description of 120–160 words
  - Meta title (≤ 70 chars)
  - Meta description (≤ 160 chars)
- **Hard rules**:
  - Banned words: `cosplay`, `weapon`, `knife`, `UV`, `premium`, `perfect` (case-insensitive)
  - Bullets: exactly 8 bullets, each ≤ 85 characters
  - Keep brand name present in title and description
  - Preserve and naturally insert given attributes/keywords
  - No medical claims
- **Output**: CSV with new columns: `refined_title`, `refined_bullets` (pipe-joined or JSON), `refined_description`, `meta_title`, `meta_description`, `violations`.
- **Violations**: list any rule the generated content did not satisfy.

### Grading criteria
- **Rule adherence (40)**
- **Rewriting quality (30)**
- **Keyword handling & length limits (20)**
- **Code/docs (10)**

## Quick start
1. Create and populate `.env` from `.env.example`.
2. Install dependencies: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
3. Run API: `uvicorn app.main:app --reload`
4. Run batch: `python run_batch.py --input sample_input.csv --output output.csv`

## Docker
Build: `docker build -t walmart-content-refiner .`
Run: `docker run --env-file .env -p 8000:8000 walmart-content-refiner`
