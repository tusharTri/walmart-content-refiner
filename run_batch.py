import argparse
from app.services.data_loader import load_csv, write_csv
from app.services.refiner_service import refine_product
from app.services.validator import validate_required_fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_csv(args.input)
    issues = validate_required_fields(rows, ["product_id", "title", "description"])
    if issues:
        for issue in issues:
            print(f"Row {issue.row_index} - {issue.field}: {issue.message}")
        print("Validation issues found; continuing to refine anyway.")

    refined = [refine_product(r) for r in rows]
    write_csv(args.output, refined)
    print(f"Wrote {len(refined)} rows to {args.output}")


if __name__ == "__main__":
    main()
