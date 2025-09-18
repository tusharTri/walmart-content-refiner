# walmart-content-refiner

A minimal FastAPI-based service to refine Walmart product content in batch or via API.

## Structure
- `app/`: FastAPI app, services, models, and routes
- `tests/`: Unit tests
- `run_batch.py`: Batch runner for CSV input
- `sample_input.csv`: Example input file

## Quick start
1. Create and populate `.env` from `.env.example`.
2. Install dependencies: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
3. Run API: `uvicorn app.main:app --reload`
4. Run batch: `python run_batch.py --input sample_input.csv --output output.csv`

## Docker
Build: `docker build -t walmart-content-refiner .`
Run: `docker run --env-file .env -p 8000:8000 walmart-content-refiner`
