# Walmart Content Refiner - Technical Documentation

## System Architecture & Design Decisions

### Core Design Principles

1. **100% Compliance First**: Every component is designed to ensure Walmart's strict business rules are met
2. **Reliability Over Speed**: Rule-based fallback ensures the system never fails
3. **Comprehensive Validation**: Multiple layers of validation prevent violations
4. **Production Ready**: Robust error handling, logging, and monitoring

### Content Generation Strategy

The system uses a **dual-approach** for content generation:

#### Primary: Hugging Face API
- **Model**: `gpt2` (free tier, no special permissions required)
- **Fallback**: Automatic retry with different models
- **Error Handling**: Graceful degradation to rule-based generation

#### Fallback: Rule-Based Generation
- **100% Reliable**: No external dependencies
- **Perfect Compliance**: Guaranteed adherence to all rules
- **Fast Processing**: Instant results without API calls

## Prompt Engineering

### System Prompt Design

The system uses a comprehensive prompt that includes:

```python
WALMART_PROMPT = """
You are a Walmart Content Refiner. You MUST generate 100% compliant content on the FIRST attempt with ZERO violations.

Strict Walmart rules:
- Title ≤ 150 chars, must include brand + product type, no banned words.
- Bullets: exactly 8 <li> items, each ≤ 85 chars, HTML <li> tags required, no banned words.
- Description: 120–160 words, must mention brand, no banned words.
- Meta Title: ≤ 70 chars, includes brand/product, no banned words.
- Meta Description: ≤ 160 chars, must summarize, no banned words.
- ABSOLUTELY NO medical claims: cure, treat, diagnose, prevent.
- DO NOT include "cosplay, weapon, knife, uv, premium, perfect".

Output Format: Return ONLY this JSON (no explanation, no markdown):
{
  "title": "...",
  "bullets": "<li>...</li><li>...</li> ... 8 items total ...",
  "description": "...",
  "meta_title": "...",
  "meta_description": "..."
}
"""
```

### Key Prompt Features

1. **Explicit Instructions**: Clear, unambiguous requirements
2. **JSON Format**: Structured output for easy parsing
3. **Banned Word List**: Explicit prohibition of problematic terms
4. **Character Limits**: Precise length requirements
5. **HTML Formatting**: Specific bullet point requirements

## Validation System

### Multi-Layer Validation

The validator checks multiple aspects of compliance:

```python
def validate_product_output(output_dict: Dict[str, Any], input_keywords: List[str], brand: str) -> List[str]:
    """
    Comprehensive validation of generated content against Walmart rules
    
    Validation checks:
    1. Title length and brand presence
    2. Bullet count, length, and HTML formatting
    3. Description word count (120-160 words)
    4. Meta title/description character limits
    5. Banned word detection
    6. Keyword integration
    7. Medical claims detection
    """
```

### Banned Words Management

```python
BANNED_WORDS = ["cosplay", "weapon", "knife", "uv", "premium", "perfect"]

# Automatic synonym replacement
SYNONYMS = {
    "perfect": ["excellent", "outstanding", "superior", "exceptional"],
    "premium": ["high-quality", "top-tier", "superior", "deluxe"],
    "uv": ["sun protection", "weather-resistant", "outdoor-safe"],
    "weapon": ["tool", "implement", "device", "equipment"],
    "knife": ["blade", "cutter", "slicer", "cutting tool"],
    "cosplay": ["costume", "dress-up", "roleplay", "themed outfit"]
}
```

## Data Flow Architecture

### Input Processing
```
CSV File → Data Loader → ProductInput → Refiner Service → ProductOutput → CSV Export
```

### Content Generation Flow
```
1. Parse product attributes (JSON/string)
2. Extract keywords for integration
3. Attempt Hugging Face API call
4. If API fails → Use rule-based generation
5. Validate generated content
6. If violations found → Retry (up to 3 attempts)
7. Return best result or perfect compliance
```

### Validation Pipeline
```
Generated Content → Validator → Compliance Check → Violation Report → Final Output
```

## Error Handling Strategy

### API Error Handling
- **401 Unauthorized**: Fallback to rule-based generation
- **403 Forbidden**: Try different model or fallback
- **429 Rate Limited**: Wait and retry
- **500 Server Error**: Immediate fallback

### Content Generation Errors
- **JSON Parsing Errors**: Retry with clearer instructions
- **Validation Failures**: Retry with violation feedback
- **Timeout Errors**: Fallback to rule-based generation

### Graceful Degradation
- **API Unavailable**: Continue with rule-based generation
- **Partial Failures**: Return best available result
- **Complete Failure**: Return error with detailed logging

## Performance Optimizations

### Caching Strategy
- **Model Initialization**: Cache model instances
- **Configuration Loading**: Single instance per request
- **Validation Results**: Cache common patterns

### Batch Processing
- **Progress Tracking**: Real-time progress bars
- **Parallel Processing**: Multiple products simultaneously
- **Memory Management**: Efficient DataFrame operations

### API Optimization
- **Request Batching**: Group similar requests
- **Timeout Management**: Prevent hanging requests
- **Retry Logic**: Exponential backoff for failures

## Security Considerations

### API Key Management
- **Environment Variables**: No hardcoded keys
- **Secure Storage**: Production key management
- **Access Control**: Minimal required permissions

### Input Validation
- **Pydantic Models**: Type safety and validation
- **Sanitization**: Clean user inputs
- **Size Limits**: Prevent resource exhaustion

### Output Security
- **Content Filtering**: Remove sensitive information
- **Audit Logging**: Track all operations
- **Error Masking**: Don't expose internal details

## Monitoring & Logging

### Structured Logging
```python
logger.info(f"Refining {input_data.brand} {input_data.product_type}")
logger.warning(f"❌ Violations found: {violations}")
logger.info(f"✅ 100% compliance achieved after {attempt + 1} attempts")
```

### Key Metrics
- **Compliance Rate**: Percentage of products with zero violations
- **Processing Time**: Average time per product
- **API Success Rate**: Hugging Face API reliability
- **Fallback Usage**: Rule-based generation frequency

### Error Tracking
- **API Failures**: Detailed error codes and messages
- **Validation Failures**: Specific rule violations
- **Processing Errors**: System-level issues

## Testing Strategy

### Unit Tests
- **Validator Tests**: All validation rules
- **Model Tests**: Pydantic validation
- **Service Tests**: Core business logic

### Integration Tests
- **API Endpoints**: Full request/response cycle
- **Batch Processing**: End-to-end CSV processing
- **Error Handling**: Failure scenarios

### Compliance Tests
- **Rule Adherence**: 100% compliance verification
- **Edge Cases**: Boundary conditions
- **Regression Tests**: Prevent rule violations

## Deployment Architecture

### Container Strategy
```dockerfile
FROM python:3.10-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
```env
# Production Environment
HUGGINGFACE_API_KEY=production_key
LOG_LEVEL=INFO
GCP_PROJECT=walmart-content-refiner
CLOUD_BUCKET=content-refiner-data

# Development Environment
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Scaling Considerations
- **Horizontal Scaling**: Multiple container instances
- **Load Balancing**: Distribute API requests
- **Database**: Optional for audit trails
- **Caching**: Redis for performance

## Future Enhancements

### Planned Features
1. **Multi-Language Support**: International compliance
2. **Advanced AI Models**: GPT-4, Claude integration
3. **Real-Time Processing**: WebSocket support
4. **Analytics Dashboard**: Compliance metrics
5. **Custom Rules**: Configurable business rules

### Performance Improvements
1. **Async Processing**: Non-blocking operations
2. **Batch Optimization**: Parallel processing
3. **Caching Layer**: Redis integration
4. **CDN Integration**: Static asset delivery

### Monitoring Enhancements
1. **Real-Time Metrics**: Live compliance tracking
2. **Alert System**: Violation notifications
3. **Performance Monitoring**: APM integration
4. **Cost Tracking**: API usage analytics

---

This technical documentation provides a comprehensive overview of the Walmart Content Refiner system, including design decisions, implementation details, and operational considerations.
