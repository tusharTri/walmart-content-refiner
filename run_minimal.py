#!/usr/bin/env python3
"""
Minimal Walmart Content Refiner - Batch Processor
Processes CSV files with strict compliance to Walmart rules
"""

import argparse
import pandas as pd
import json
from tqdm import tqdm
from app.services.refiner_service import refine_product
from app.models import ProductInput
from app.services.data_loader import load_csv, save_csv

def process_batch(input_file: str, output_file: str):
    """Process CSV file with Walmart content refinement"""
    print(f"Loading input file: {input_file}")
    df = load_csv(input_file)
    
    print(f"Processing {len(df)} products...")
    outputs = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        # Create input
        inp = ProductInput(
            brand=row.get("brand", ""),
            product_type=row.get("product_type", ""),
            attributes=row.get("attributes", {}),
            current_description=row.get("current_description", ""),
            current_bullets=row.get("current_bullets", [])
        )
        
        # Refine product
        out = refine_product(inp)
        
        # Collect output
        outputs.append({
            "refined_title": out.title,
            "refined_bullets": out.bullets,  # HTML string
            "refined_description": out.description,
            "meta_title": out.meta_title,
            "meta_description": out.meta_description,
            "violations": "; ".join(out.violations),
        })
    
    # Combine with original data
    out_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(outputs)], axis=1)
    
    print(f"Saving output to: {output_file}")
    save_csv(out_df, output_file)
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walmart Content Refiner - Batch Processor")
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument("output", help="Output CSV file")
    
    args = parser.parse_args()
    process_batch(args.input, args.output)