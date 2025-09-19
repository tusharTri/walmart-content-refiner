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
SYSTEM_PROMPT = """You are an expert Walmart Content Refiner AI specializing in e-commerce product descriptions. Your task is to create compelling, compliant, and conversion-optimized content that achieves 100% rule adherence.

CRITICAL COMPLIANCE RULES (MUST FOLLOW EXACTLY):

1. TITLE REQUIREMENTS:
   - Maximum 150 characters (count every character including spaces)
   - MUST contain the brand name naturally integrated
   - Should be compelling and benefit-focused
   - Example: "BrandCo Professional Blender - Powerful 1200W Motor for Smoothies"

2. BULLETS REQUIREMENTS (CRITICAL):
   - EXACTLY 8 bullets (no more, no less)
   - Each bullet ≤85 characters (count every character)
   - Format as HTML: <li>Your bullet text here</li>
   - Must be benefit-focused and scannable
   - Example: <li>Powerful 1200W motor blends toughest ingredients</li>

3. DESCRIPTION REQUIREMENTS:
   - EXACTLY 120-160 words (count every word)
   - MUST contain brand name naturally
   - Must use ALL provided attributes naturally (once each)
   - Should be engaging and conversion-focused
   - Write in active voice with compelling language

4. META TITLE REQUIREMENTS:
   - Maximum 70 characters (count every character)
   - Must include brand name
   - Should be SEO-optimized and compelling

5. META DESCRIPTION REQUIREMENTS:
   - Maximum 160 characters (count every character)
   - Must be compelling and informative
   - Should encourage clicks and conversions

6. BANNED WORDS (NEVER USE - CASE INSENSITIVE):
   - cosplay, weapon, knife, UV, premium, perfect
   - Synonyms to avoid: outstanding, remarkable, superior, excellent, exceptional, amazing, fantastic, incredible, wonderful, brilliant, magnificent, spectacular, extraordinary, phenomenal
   - Use alternatives: great, reliable, durable, efficient, innovative, quality, effective

7. ATTRIBUTE INTEGRATION:
   - Use ALL provided attributes naturally in the description
   - Each attribute should appear exactly once
   - Integrate seamlessly into the narrative flow
   - Include specific measurements and details

8. NO MEDICAL CLAIMS:
   - Avoid: cure, treat, diagnose, prevent, heal, remedy, therapeutic, medicinal, clinical, medical, health benefits
   - Use: support, promote, enhance, improve, maintain, boost

9. KEYWORD PRESERVATION:
   - Preserve and naturally insert ALL given keywords
   - Keywords should flow naturally in the content
   - Don't force keywords unnaturally

CONTENT QUALITY STANDARDS:
- Write in active voice with compelling, benefit-focused language
- Use power words that drive conversions (durable, reliable, efficient, innovative)
- Create urgency and desire without being pushy
- Ensure descriptions flow naturally and read well
- Make bullets scannable and benefit-focused
- Include specific details and measurements when available

VALIDATION CHECKLIST (VERIFY BEFORE OUTPUT):
✓ Title ≤150 chars with brand name
✓ Exactly 8 bullets, each ≤85 chars, HTML format
✓ Description 120-160 words with brand name
✓ Meta title ≤70 chars
✓ Meta description ≤160 chars
✓ No banned words or synonyms
✓ All attributes used naturally (once each)
✓ No medical claims
✓ All keywords preserved and integrated
✓ Natural, engaging language

OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:
{
  "title": "BrandName Product Type - Key Benefit",
  "bullets": ["<li>Benefit-focused feature 1</li>", "<li>Benefit-focused feature 2</li>", "<li>Benefit-focused feature 3</li>", "<li>Benefit-focused feature 4</li>", "<li>Benefit-focused feature 5</li>", "<li>Benefit-focused feature 6</li>", "<li>Benefit-focused feature 7</li>", "<li>Benefit-focused feature 8</li>"],
  "description": "Compelling 120-160 word description that naturally includes brand name and all attributes...",
  "meta_title": "BrandName Product Type",
  "meta_description": "Compelling meta description under 160 characters"
}

EXAMPLE OF PERFECT OUTPUT:
{
  "title": "BrandCo Professional Blender - Powerful 1200W Motor for Smoothies",
  "bullets": ["<li>Powerful 1200W motor blends toughest ingredients</li>", "<li>6-blade design ensures smooth consistency every time</li>", "<li>Stainless steel construction for durability and style</li>", "<li>5-speed control for precise blending control</li>", "<li>Dishwasher safe parts for easy cleanup</li>", "<li>Large capacity jar perfect for family meals</li>", "<li>Quiet operation won't disturb your household</li>", "<li>5-year warranty for peace of mind</li>"],
  "description": "The BrandCo Professional Blender delivers exceptional performance with its powerful 1200W motor that effortlessly blends even the toughest ingredients. Featuring a sophisticated 6-blade design, this blender ensures smooth consistency every time you use it. The stainless steel construction provides both durability and elegant style that complements any kitchen. With 5-speed control, you have precise blending control for everything from smoothies to sauces. The large capacity jar is perfect for family meals, while the dishwasher safe parts make cleanup effortless. The quiet operation won't disturb your household, and the 5-year warranty provides peace of mind. This reliable appliance combines innovative technology with quality construction to deliver consistent results.",
  "meta_title": "BrandCo Professional Blender - 1200W Motor",
  "meta_description": "Powerful BrandCo Professional Blender with 1200W motor, 6-blade design, and stainless steel construction. 5-year warranty."
}

Remember: Quality over speed. Create content that converts and complies with ALL rules. Double-check character counts and word counts before outputting."""

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

{f"🚨 CRITICAL: ALL PREVIOUS ATTEMPTS FAILED WITH THESE VIOLATIONS:" if violations else ""}
{chr(10).join([f"❌ {violation}" for violation in violations]) if violations else ""}

{f"🔥 URGENT: You have {len(violations)} violations to fix! This is attempt {attempt}. You MUST avoid ALL these violations!" if violations else ""}

TASK: Rewrite this content to be Walmart-compliant, conversion-optimized, and engaging. Follow ALL rules strictly.

CRITICAL REQUIREMENTS CHECKLIST:
✓ Title ≤150 chars with brand name naturally integrated
✓ Exactly 8 bullets, each ≤85 chars, HTML <li> format
✓ Description 120-160 words with brand name and ALL attributes
✓ Meta title ≤70 chars with brand name
✓ Meta description ≤160 chars
✓ No banned words (cosplay/weapon/knife/UV/premium/perfect) or synonyms
✓ Use all attributes naturally (once each) in description
✓ No medical claims (cure/treat/diagnose/prevent/heal/remedy)
✓ Preserve and integrate ALL keywords naturally
✓ Natural, engaging, conversion-focused language

{f"🎯 FOCUS: Fix these specific issues: {', '.join(violations)}" if violations else "🎯 FOCUS: Create perfect, compliant content"}

SPECIFIC VIOLATION FIXING INSTRUCTIONS:
{f"❌ NEVER use these banned words: perfect, premium, cosplay, weapon, knife, UV" if violations else ""}
{f"❌ ALWAYS ensure description is 120-160 words exactly" if violations else ""}
{f"❌ ALWAYS include ALL attributes: {attributes_text}" if violations else ""}
{f"❌ ALWAYS count characters and words before outputting" if violations else ""}

{f"🔧 SPECIFIC FIXES NEEDED:" if violations else ""}
{f"• For 'keyword not present' violations: You MUST include these exact keywords in your description: {attributes_text}" if violations else ""}
{f"• For 'description word count' violations: Count words carefully - must be 120-160 words exactly" if violations else ""}
{f"• For 'banned word' violations: Replace banned words with alternatives like 'great', 'reliable', 'durable', 'efficient'" if violations else ""}

{f"📝 EXAMPLE OF PROPER KEYWORD INTEGRATION:" if violations else ""}
{f"• If attributes are 'Color: Pink, Material: Plastic, Features: Waterproof, Long-lasting'" if violations else ""}
{f"• Your description MUST mention: 'pink color', 'plastic material', 'waterproof feature', 'long-lasting performance'" if violations else ""}
{f"• Each attribute must appear naturally in the description exactly once" if violations else ""}

VALIDATION STEPS (DO THIS BEFORE OUTPUTTING):
1. Count characters in title (must be ≤150)
2. Count bullets (must be exactly 8, each ≤85 chars)
3. Count words in description (must be 120-160)
4. Count characters in meta title (must be ≤70)
5. Count characters in meta description (must be ≤160)
6. Check for banned words and synonyms
7. Verify all attributes are used naturally
8. Verify no medical claims
9. Verify all keywords are preserved

{f"⚠️  WARNING: Previous attempts had {len(violations)} violations. Be extra careful!" if violations else ""}
{f"🚫 DO NOT repeat these mistakes: {', '.join(violations)}" if violations else ""}

{f"✅ SUCCESS CRITERIA: Your output will be validated. If you repeat any violation, you will fail!" if violations else ""}

Return only valid JSON as specified above. Double-check all counts before outputting.
"""
        
        print(f"🤖 Calling Gemini for {input_data.brand} (attempt {attempt})")
        
        response = model.generate_content(
            SYSTEM_PROMPT + "\n\n" + user_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7 if attempt > 1 else 0.3,  # Higher temperature for retries to encourage creativity
                max_output_tokens=1200,
                top_p=0.9 if attempt > 1 else 0.8,  # Higher top_p for retries
                top_k=50 if attempt > 1 else 40  # Higher top_k for retries
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
            
            # Convert bullets from list to string if needed
            if isinstance(result.get("bullets"), list):
                result["bullets"] = "".join(result["bullets"])
            
            print(f"✅ Successfully generated content for {input_data.brand} (attempt {attempt})")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed (attempt {attempt}): {e}")
            print(f"📝 Response text: {response_text[:500]}...")
            return {}
            
    except Exception as e:
        print(f"💥 Gemini API call failed (attempt {attempt}): {e}")
        return {}

def refine_product(input_data: ProductInput) -> ProductOutput:
    """Refine product content using iterative Gemini AI with comprehensive violation feedback"""
    print(f"🚀 Starting iterative refinement for {input_data.brand} {input_data.product_type}")
    
    best_result = None
    best_violations = []
    all_attempt_violations = []  # Track violations from ALL attempts
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        print(f"🔄 Attempt {attempt}/{max_attempts} for {input_data.brand}")
        
        # Generate content with ALL previous violations as feedback
        all_previous_violations = []
        for i, violations in enumerate(all_attempt_violations):
            all_previous_violations.extend([f"Attempt {i+1}: {v}" for v in violations])
        
        draft = call_gemini_advanced(input_data, all_previous_violations, attempt)
        
        if not draft:
            print(f"❌ Failed to generate content on attempt {attempt}")
            continue
        
        # Validate the generated content
        current_violations = validator.validate_product_output(
            draft, 
            input_keywords=list((input_data.attributes or {}).values()), 
            brand=input_data.brand
        )
        
        # Store violations from this attempt
        all_attempt_violations.append(current_violations)
        
        print(f"📊 Attempt {attempt} violations: {current_violations}")
        
        # If this is the first attempt or has fewer violations, save as best
        if attempt == 1 or len(current_violations) < len(best_violations):
            best_result = draft
            best_violations = current_violations
            print(f"🏆 New best result with {len(best_violations)} violations")
        
        # If no violations, we're done
        if not current_violations:
            print(f"🎉 Perfect content generated on attempt {attempt}")
            break
        
        # If we have violations and more attempts left, continue
        if attempt < max_attempts:
            print(f"⏭️  Continuing to attempt {attempt + 1} to fix violations")
            print(f"📋 All previous violations: {all_previous_violations}")
    
    # Return the best result we found
    if best_result:
        print(f"✅ Returning best result with {len(best_violations)} violations")
        print(f"🔍 Debug: Best violations content: {repr(best_violations)}")
        result = ProductOutput(
            title=best_result.get("title", f"{input_data.brand} {input_data.product_type}"),
            bullets=best_result.get("bullets", "<li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li>"),
            description=best_result.get("description", f"{input_data.brand} {input_data.product_type} - Product description."),
            meta_title=best_result.get("meta_title", f"{input_data.brand} {input_data.product_type}"),
            meta_description=best_result.get("meta_description", f"{input_data.brand} {input_data.product_type} - Product description."),
            violations=best_violations
        )
        print(f"🔍 Debug: ProductOutput violations: {repr(result.violations)}")
        return result
    else:
        print(f"💥 Failed to generate any content after all attempts")
        return ProductOutput(
            title=f"{input_data.brand} {input_data.product_type}",
            bullets="<li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li>",
            description=f"{input_data.brand} {input_data.product_type} - Product description.",
            meta_title=f"{input_data.brand} {input_data.product_type}",
            meta_description=f"{input_data.brand} {input_data.product_type} - Product description.",
            violations=["Failed to generate content after all attempts"]
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
            
            # Convert bullets from list to string if needed
            if isinstance(fixed_output.get("bullets"), list):
                fixed_output["bullets"] = "".join(fixed_output["bullets"])
            
            logger.info(f"Successfully fixed violations for {brand}")
            return fixed_output
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for fix: {e}")
            return output_dict
            
    except Exception as e:
        logger.error(f"Failed to fix violations for {brand}: {e}")
        return output_dict