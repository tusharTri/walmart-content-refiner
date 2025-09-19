#!/usr/bin/env python3
"""
Minimal test script for Walmart Content Refiner
Processes only the first row to minimize API token usage
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_single_row():
    """Test with just one row to minimize token usage"""
    print("🧪 Testing Walmart Content Refiner (Single Row)")
    print("=" * 50)
    
    # Check if API key is set
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ No GEMINI_API_KEY found!")
        print("💡 Get free API key: https://makersuite.google.com/app/apikey")
        print("💡 Set it: export GEMINI_API_KEY='your_key'")
        return False
    
    try:
        from app.models import ProductInput
        from app.services.refiner_service import refine_product
        
        # Test with just one product to save tokens
        test_input = ProductInput(
            brand="TechBrand",
            product_type="Wireless Headphones",
            attributes={
                "Color": "Black",
                "Features": "Noise Cancelling, Bluetooth"
            },
            current_description="Perfect headphones with premium sound quality. Great for cosplay events.",
            current_bullets=[
                "- Perfect sound quality",
                "- Premium materials",
                "- UV resistant design",
                "- Cosplay friendly",
                "- Sharp audio",
                "- Weapon-grade durability",
                "- Premium comfort",
                "- Perfect for all occasions"
            ]
        )
        
        print(f"📱 Processing: {test_input.brand} {test_input.product_type}")
        print("⏳ Calling Gemini API (this may take a few seconds)...")
        
        result = refine_product(test_input)
        
        print("\n✅ Results:")
        print(f"Title: {result.title}")
        print(f"Title length: {len(result.title)} chars")
        print(f"Description: {result.description[:100]}...")
        print(f"Description word count: {len(result.description.split())} words")
        print(f"Bullets count: {len(result.bullets)}")
        print(f"Meta title: {result.meta_title}")
        print(f"Meta description: {result.meta_description}")
        print(f"Violations: {result.violations}")
        
        if not result.violations:
            print("\n🎉 Perfect! No violations found.")
        else:
            print(f"\n⚠️  Violations found: {result.violations}")
        
        print("\n📊 Compliance Check:")
        print(f"✅ Title ≤150 chars: {len(result.title) <= 150}")
        print(f"✅ Exactly 8 bullets: {len(result.bullets) == 8}")
        print(f"✅ Brand in title: {'TechBrand' in result.title}")
        print(f"✅ Brand in description: {'TechBrand' in result.description}")
        print(f"✅ Meta title ≤70 chars: {len(result.meta_title) <= 70}")
        print(f"✅ Meta description ≤160 chars: {len(result.meta_description) <= 160}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_csv_processing():
    """Test CSV processing without API calls"""
    print("\n📊 Testing CSV Processing...")
    
    try:
        from app.services.data_loader import load_csv
        
        sample_path = project_root / "sample_input.csv"
        if sample_path.exists():
            df = load_csv(str(sample_path))
            print(f"✅ Successfully loaded CSV with {len(df)} rows")
            print(f"✅ Columns: {list(df.columns)}")
            print(f"✅ First row brand: {df.iloc[0]['brand']}")
            return True
        else:
            print("❌ sample_input.csv not found")
            return False
            
    except Exception as e:
        print(f"❌ CSV processing failed: {e}")
        return False

def main():
    """Run minimal tests"""
    print("🚀 Walmart Content Refiner - Minimal Test")
    
    # Test CSV processing first (no API calls)
    csv_ok = test_csv_processing()
    
    # Test single row with API
    api_ok = test_single_row()
    
    print("\n📋 Test Summary:")
    print(f"CSV Processing: {'✅ PASS' if csv_ok else '❌ FAIL'}")
    print(f"API Integration: {'✅ PASS' if api_ok else '❌ FAIL'}")
    
    if csv_ok and api_ok:
        print("\n🎉 System ready! You can now run:")
        print("   python run_batch.py sample_input.csv output.csv")
    else:
        print("\n❌ Some tests failed. Check errors above.")

if __name__ == "__main__":
    main()
