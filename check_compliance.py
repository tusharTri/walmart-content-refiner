#!/usr/bin/env python3
"""
Test script to verify Walmart compliance
"""

import pandas as pd
import re
from typing import List

BANNED_WORDS = ["cosplay", "weapon", "knife", "uv", "premium", "perfect"]

def check_compliance(csv_file: str):
    """Check if CSV output complies with Walmart rules"""
    df = pd.read_csv(csv_file)
    
    print(f"Checking compliance for {len(df)} products...")
    
    violations_count = 0
    total_products = len(df)
    
    for idx, row in df.iterrows():
        product_violations = []
        
        # Check title
        title = str(row.get('refined_title', ''))
        if len(title) > 150:
            product_violations.append("Title > 150 chars")
        if not title:
            product_violations.append("Empty title")
        
        # Check bullets
        bullets = str(row.get('refined_bullets', ''))
        if bullets:
            # Count <li> tags
            li_count = len(re.findall(r'<li[^>]*>', bullets))
            if li_count != 8:
                product_violations.append(f"Bullets count: {li_count} (should be 8)")
            
            # Check individual bullet lengths
            li_matches = re.findall(r'<li[^>]*>(.*?)</li>', bullets)
            for i, bullet_content in enumerate(li_matches):
                if len(bullet_content.strip()) > 85:
                    product_violations.append(f"Bullet {i+1} > 85 chars")
        
        # Check description word count
        description = str(row.get('refined_description', ''))
        word_count = len(description.split())
        if word_count < 120 or word_count > 160:
            product_violations.append(f"Description: {word_count} words (should be 120-160)")
        
        # Check meta title
        meta_title = str(row.get('meta_title', ''))
        if len(meta_title) > 70:
            product_violations.append(f"Meta title: {len(meta_title)} chars (should be ≤70)")
        
        # Check meta description
        meta_desc = str(row.get('meta_description', ''))
        if len(meta_desc) > 160:
            product_violations.append(f"Meta description: {len(meta_desc)} chars (should be ≤160)")
        
        # Check banned words
        all_text = f"{title} {description} {meta_title} {meta_desc} {bullets}".lower()
        for word in BANNED_WORDS:
            if word in all_text:
                product_violations.append(f"Banned word: {word}")
        
        if product_violations:
            violations_count += 1
            print(f"Product {idx+1} ({row.get('brand', 'Unknown')}): {product_violations}")
    
    compliance_rate = ((total_products - violations_count) / total_products) * 100
    print(f"\nCompliance Summary:")
    print(f"Total products: {total_products}")
    print(f"Products with violations: {violations_count}")
    print(f"Compliance rate: {compliance_rate:.1f}%")
    
    return compliance_rate

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python check_compliance.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    check_compliance(csv_file)
