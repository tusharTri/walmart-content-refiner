import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from app.models import ProductInput, ProductOutput
from app.services import validator
from app.config import get_settings, get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configure Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    logger.warning("No Gemini API key found. Using fallback mode.")
    model = None

# Advanced system prompt for high-quality content generation
SYSTEM_PROMPT = """You are an expert Walmart Content Refiner AI specializing in e-commerce product descriptions. Your task is to create compelling, compliant, and conversion-optimized content.

CRITICAL COMPLIANCE RULES (MUST FOLLOW):
1. TITLE: ≤150 characters, MUST contain the brand name naturally
2. BULLETS: Exactly 8 bullets, each ≤85 characters, format as HTML <li>...</li>
3. DESCRIPTION: 120-160 words, natural and engaging, MUST contain brand name
4. META TITLE: ≤70 characters, include brand name
5. META DESCRIPTION: ≤160 characters, compelling and informative
6. BANNED WORDS: NEVER use these words (case-insensitive): cosplay, weapon, knife, UV, premium, perfect
7. ATTRIBUTES: Use ALL provided attributes naturally in description (only once each)
8. NO MEDICAL CLAIMS: Avoid words like cure, treat, diagnose, prevent, heal, remedy
9. NATURAL LANGUAGE: Content must sound human-written and engaging

CONTENT QUALITY STANDARDS:
- Write in active voice with compelling, benefit-focused language
- Use power words that drive conversions (durable, reliable, efficient, innovative)
- Create urgency and desire without being pushy
- Ensure descriptions flow naturally and read well
- Make bullets scannable and benefit-focused
- Include specific details and measurements when available

OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:
{
  "title": "BrandName Product Type - Key Benefit",
  "bullets": ["<li>Benefit-focused feature 1</li>", "<li>Benefit-focused feature 2</li>", ...],
  "description": "Compelling 120-160 word description that naturally includes brand name and all attributes...",
  "meta_title": "BrandName Product Type",
  "meta_description": "Compelling meta description under 160 characters"
}

Remember: Quality over speed. Create content that converts and complies with all rules."""

def call_gemini_advanced(input_data: ProductInput, violations: List[str] = None, attempt: int = 1) -> Dict[str, Any]:
    """Call Gemini API with advanced prompting for high-quality content generation"""
    if not model:
        logger.error("Gemini model not available")
        return {}
    
    try:
        # Build concise user prompt to save tokens
        attributes_text = ""
        if isinstance(input_data.attributes, dict):
            attributes_text = ", ".join([f"{k}: {v}" for k, v in input_data.attributes.items()])
        elif isinstance(input_data.attributes, str):
            attributes_text = input_data.attributes
        
        user_prompt = f"""
PRODUCT INFORMATION TO REFINE:
- Brand: {input_data.brand}
- Product Type: {input_data.product_type}
- Attributes: {attributes_text}
- Current Description: {input_data.current_description}
- Current Bullets: {json.dumps(input_data.current_bullets)}

{f"PREVIOUS VIOLATIONS TO FIX (Attempt {attempt}): {', '.join(violations)}" if violations else ""}

TASK: Rewrite this content to be Walmart-compliant, conversion-optimized, and engaging. Follow ALL rules strictly.

REQUIREMENTS CHECKLIST:
✓ Title ≤150 chars with brand name
✓ Exactly 8 bullets, each ≤85 chars, HTML format
✓ Description 120-160 words with brand name
✓ Meta title ≤70 chars
✓ Meta description ≤160 chars
✓ No banned words (cosplay/weapon/knife/UV/premium/perfect)
✓ Use all attributes naturally (once each)
✓ No medical claims
✓ Natural, engaging language

{f"FOCUS: Fix these specific issues: {', '.join(violations)}" if violations else "FOCUS: Create perfect, compliant content"}

Return only valid JSON as specified above.
"""
        
        logger.info(f"Calling Gemini for {input_data.brand} (attempt {attempt})")
        
        response = model.generate_content(
            SYSTEM_PROMPT + "\n\n" + user_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3 if attempt == 1 else 0.2,  # Lower temperature for retries
                max_output_tokens=1200,
                top_p=0.8,
                top_k=40
            )
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to find JSON in the response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        
        # Parse JSON
        try:
            result = json.loads(response_text)
            logger.info(f"Successfully generated content for {input_data.brand} (attempt {attempt})")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed (attempt {attempt}): {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return {}
            
    except Exception as e:
        logger.error(f"Gemini API call failed (attempt {attempt}): {e}")
        return {}

def refine_product(input_data: ProductInput) -> ProductOutput:
    """Refine product content using advanced Gemini AI with single validation"""
    logger.info(f"Starting advanced refinement for {input_data.brand} {input_data.product_type}")
    
    # Single generation attempt to conserve API tokens
    draft = call_gemini_advanced(input_data)
    
    if not draft:
        logger.error("Failed to generate initial content")
        return ProductOutput(
            title=f"{input_data.brand} {input_data.product_type}",
            bullets=["<li>Product feature</li>"] * 8,
            description=f"{input_data.brand} {input_data.product_type} - Product description.",
            meta_title=f"{input_data.brand} {input_data.product_type}",
            meta_description=f"{input_data.brand} {input_data.product_type} - Product description.",
            violations=["Failed to generate content"]
        )
    
    # Single validation attempt to conserve API tokens
    logger.info(f"Single validation attempt for {input_data.brand}")
    
    violations = validator.validate_product_output(
        draft, 
        input_keywords=list((input_data.attributes or {}).values()), 
        brand=input_data.brand
    )
    
    if violations:
        logger.warning(f"Violations found for {input_data.brand}: {violations}")
        logger.info("Skipping retries to conserve API tokens")
    else:
        logger.info(f"Content validated successfully for {input_data.brand}")
    
    # Ensure we have valid structure and fallback content
    return ProductOutput(
        title=draft.get("title", f"{input_data.brand} {input_data.product_type}"),
        bullets=draft.get("bullets", ["<li>Product feature</li>"] * 8),
        description=draft.get("description", f"{input_data.brand} {input_data.product_type} - Product description."),
        meta_title=draft.get("meta_title", f"{input_data.brand} {input_data.product_type}"),
        meta_description=draft.get("meta_description", f"{input_data.brand} {input_data.product_type} - Product description."),
        violations=violations
    )

def fix_output_violations(output_dict: Dict[str, Any], violations: List[str], brand: str) -> Dict[str, Any]:
    """Fix specific violations in existing output using advanced Gemini prompting"""
    if not model:
        logger.error("Gemini model not available for fixing violations")
        return output_dict
    
    try:
        fix_prompt = f"""
You have an existing product output with specific violations. Please fix ONLY the specified violations while keeping everything else exactly the same.

CURRENT OUTPUT:
{json.dumps(output_dict, indent=2)}

VIOLATIONS TO FIX: {', '.join(violations)}

Brand: {brand}

INSTRUCTIONS:
1. Fix ONLY the specified violations
2. Keep all other content unchanged
3. Maintain the same structure and format
4. Ensure the fix sounds natural and engaging
5. Follow all compliance rules

Return the corrected JSON with the same structure, fixing only the specified violations.
"""
        
        logger.info(f"Fixing violations for {brand}: {violations}")
        
        response = model.generate_content(
            fix_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=800,
                top_p=0.7,
                top_k=30
            )
        )
        
        response_text = response.text.strip()
        
        # Extract JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        
        try:
            fixed_output = json.loads(response_text)
            logger.info(f"Successfully fixed violations for {brand}")
            return fixed_output
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for fix: {e}")
            return output_dict
            
    except Exception as e:
        logger.error(f"Failed to fix violations for {brand}: {e}")
        return output_dict