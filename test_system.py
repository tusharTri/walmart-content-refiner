#!/usr/bin/env python3
"""
Test script for Walmart Content Refiner with Gemini AI
This script tests the complete pipeline with sample data
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.models import ProductInput
from app.services.refiner_service import refine_product
from app.config import get_logger

def test_gemini_integration():
    """Test the Gemini integration with a sample product"""
    logger = get_logger(__name__)
    
    # Set a test API key if not already set
    if not os.getenv('GEMINI_API_KEY'):
        logger.warning("No GEMINI_API_KEY found. Please set it in your environment.")
        logger.info("You can get a free API key from: https://makersuite.google.com/app/apikey")
        return False
    
    # Create a test product input
    test_input = ProductInput(
        brand="TechBrand",
        product_type="Wireless Headphones",
        attributes={
            "Color": "Black",
            "Material": "Plastic",
            "Features": "Noise Cancelling, Bluetooth 5.0",
            "Battery Life": "30 hours"
        },
        current_description="These are perfect wireless headphones with premium sound quality. They have UV protection and are great for cosplay events. The knife-sharp audio quality will cut through any noise.",
        current_bullets=[
            "- Perfect sound quality",
            "- Premium materials",
            "- UV resistant design", 
            "- Cosplay friendly",
            "- Sharp audio like a knife",
            "- Weapon-grade durability",
            "- Premium comfort",
            "- Perfect for all occasions"
        ]
    )
    
    logger.info("Testing Gemini integration with sample product...")
    logger.info(f"Brand: {test_input.brand}")
    logger.info(f"Product Type: {test_input.product_type}")
    
    try:
        # Test the refinement
        result = refine_product(test_input)
        
        logger.info("✅ Refinement completed successfully!")
        logger.info(f"Title: {result.title}")
        logger.info(f"Description length: {len(result.description.split())} words")
        logger.info(f"Bullets count: {len(result.bullets)}")
        logger.info(f"Violations: {result.violations}")
        
        # Check if violations were fixed
        if not result.violations:
            logger.info("🎉 Perfect! No violations found.")
        else:
            logger.warning(f"⚠️  Some violations remain: {result.violations}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_csv_processing():
    """Test CSV processing with sample data"""
    logger = get_logger(__name__)
    
    try:
        from app.services.data_loader import load_csv
        
        # Test loading sample input
        sample_path = project_root / "sample_input.csv"
        if sample_path.exists():
            df = load_csv(str(sample_path))
            logger.info(f"✅ Successfully loaded CSV with {len(df)} rows")
            logger.info(f"Columns: {list(df.columns)}")
            return True
        else:
            logger.error("❌ sample_input.csv not found")
            return False
            
    except Exception as e:
        logger.error(f"❌ CSV processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger = get_logger(__name__)
    logger.info("🚀 Starting Walmart Content Refiner Tests")
    
    # Test 1: CSV Processing
    logger.info("\n📊 Testing CSV Processing...")
    csv_ok = test_csv_processing()
    
    # Test 2: Gemini Integration
    logger.info("\n🤖 Testing Gemini Integration...")
    gemini_ok = test_gemini_integration()
    
    # Summary
    logger.info("\n📋 Test Summary:")
    logger.info(f"CSV Processing: {'✅ PASS' if csv_ok else '❌ FAIL'}")
    logger.info(f"Gemini Integration: {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    
    if csv_ok and gemini_ok:
        logger.info("\n🎉 All tests passed! The system is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Set your GEMINI_API_KEY in .env file")
        logger.info("2. Run: python run_batch.py sample_input.csv sample_output.csv")
        logger.info("3. Check the results in sample_output.csv")
    else:
        logger.error("\n❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
