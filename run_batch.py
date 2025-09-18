import argparse
import json
from tqdm import tqdm
from app.services.data_loader import load_csv, save_csv
from app.services.refiner_service import refine_product
from app.models import ProductInput
from app.config import get_logger


def main():
    logger = get_logger()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    df = load_csv(args.input)
    outputs = []

    for _, row in tqdm(df.iterrows(), total=len(df)):
        inp = ProductInput(
            brand=row.get("brand", ""),
            product_type=row.get("product_type", ""),
            attributes=row.get("attributes", {}),
            current_description=row.get("current_description", ""),
            current_bullets=row.get("current_bullets", []),
        )
        out = refine_product(inp)
        outputs.append({
            "refined_title": out.title,
            "refined_bullets": json.dumps(out.bullets, ensure_ascii=False),
            "refined_description": out.description,
            "meta_title": out.meta_title,
            "meta_description": out.meta_description,
            "violations": "; ".join(out.violations),
        })

    # Append new columns to original DataFrame
    import pandas as pd
    out_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(outputs)], axis=1)
    save_csv(out_df, args.output)
    logger.info("Wrote %d rows to %s", len(out_df), args.output)


if __name__ == "__main__":
    main()
