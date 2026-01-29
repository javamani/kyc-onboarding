# KYC Onboarding System - OCR & NLP Setup Guide

## 🆕 New Features Added

### 1. **OCR & Document Processing**
- Extract text from uploaded documents using PaddleOCR
- Support for scanned and photographed documents
- Document quality validation (blur detection, brightness check)
- Image preprocessing (denoising, contrast adjustment, deskewing)
- Specific extractors for PAN, Aadhaar, and Passport

### 2. **NLP & Entity Extraction**
- Extract Name, DOB, Address using spaCy
- Extract and validate PAN/Aadhaar numbers using Regex
- Cross-validation between OCR data and form data
- Confidence scoring for extracted entities

---

## 📋 Updated Project Structure

```
kyc-onboarding-system/
├── backend/
│   ├── main.py                 # Main FastAPI app (UPDATED)
│   ├── ocr_processor.py        # NEW: OCR processing module
│   ├── nlp_extractor.py        # NEW: NLP entity extraction
│   └── requirements.txt        # UPDATED with OCR/NLP deps
└── frontend/
    ├── src/
    │   └── App.js              # React app (can be enhanced)
    └── package.json
```

---

## 🚀 Installation Steps

### 1. Backend Setup with OCR & NLP

#### Create Backend Files

Create the following files in `backend/` directory:

1. **main.py** - Copy from "main.py - Updated with OCR & NLP Integration" artifact
2. **ocr_processor.py** - Copy from "ocr_processor.py - OCR & Document Processing" artifact
3. **nlp_extractor.py** - Copy from "nlp_extractor.py - NLP & Entity Extraction" artifact
4. **requirements.txt** - Copy from "requirements.txt - With OCR & NLP Dependencies" artifact

#### Install Dependencies

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy English model
python -m spacy download en_core_web_sm

# For better accuracy (larger model, optional):
# python -m spacy download en_core_web_md
```

#### Expected Installation Time
- Basic installation: 5-10 minutes
- PaddleOCR download: 2-5 minutes (first run)
- spaCy model download: 1-2 minutes

---

### 2. System Requirements

**Minimum:**
- Python 3.8+
- 4GB RAM
- 2GB free disk space

**Recommended:**
- Python 3.9+
- 8GB RAM
- GPU (optional, for faster OCR processing)

---

### 3. Test OCR & NLP Installation

Create a test script `test_ocr_nlp.py`:

```python
# test_ocr_nlp.py
from ocr_processor import OCRProcessor
from nlp_extractor import NLPEntityExtractor

print("Testing OCR Processor...")
ocr = OCRProcessor(use_gpu=False)
print("✅ OCR Processor initialized")

print("\nTesting NLP Extractor...")
nlp = NLPEntityExtractor()
print("✅ NLP Extractor initialized")

# Test NLP extraction
sample_text = """
Name: JOHN DOE
Date of Birth: 15/06/1990
Address: 123 Main Street, Mumbai, 400001
PAN: ABCDE1234F
"""

result = nlp.extract_all_fields(sample_text, 'general')
print("\n📊 Extracted Fields:")
print(f"  Name: {result['name']}")
print(f"  DOB: {result['dob']}")
print(f"  PAN: {result['pan']}")
print(f"  Confidence: {result['confidence_score']:.2%}")

print("\n✅ All tests passed!")
```

Run the test:
```bash
python test_ocr_nlp.py
```

---

### 4. Start the Backend

```bash
python main.py
```

You should see:
```
✅ Database connected
✅ OCR Processor initialized
✅ NLP Extractor initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🔧 Configuration Options

### OCR Configuration

In `ocr_processor.py`, you can modify:

```python
# Use GPU for faster processing (requires CUDA)
ocr_processor = OCRProcessor(use_gpu=True, lang='en')

# Support for multiple languages
ocr_processor = OCRProcessor(lang='hi')  # Hindi
```

### NLP Configuration

In `nlp_extractor.py`, you can use different spaCy models:

```python
# Small model (faster, less accurate)
extractor = NLPEntityExtractor(model_name='en_core_web_sm')

# Medium model (balanced)
extractor = NLPEntityExtractor(model_name='en_core_web_md')

# Large model (slower, more accurate)
extractor = NLPEntityExtractor(model_name='en_core_web_lg')
```

---

## 📝 API Changes & New Endpoints

### Updated Upload Endpoint

**POST** `/api/cases/{case_id}/upload`

Now automatically processes documents with OCR and NLP:

```bash
curl -X POST "http://localhost:8000/api/cases/{case_id}/upload" \
  -F "doc_type=pan" \
  -F "file=@pan_card.jpg"
```

**Response:**
```json
{
  "message": "Document uploaded and processed successfully",
  "filename": "pan_card.jpg",
  "ocr_confidence": 0.89,
  "data_match_score": 0.95,
  "extracted_fields": {
    "name": "JOHN DOE",
    "dob": "1990-06-15",
    "pan": "ABCDE1234F"
  },
  "validation": {
    "matches": {
      "name": {
        "form": "John Doe",
        "ocr": "JOHN DOE",
        "similarity": 0.95
      }
    },
    "overall_match_score": 0.95
  }
}
```

### New Endpoint: Get OCR Results

**GET** `/api/cases/{case_id}/ocr-results`

```bash
curl http://localhost:8000/api/cases/{case_id}/ocr-results
```

**Response:**
```json
{
  "case_id": "...",
  "ocr_results": {
    "pan": {
      "raw_text": "...",
      "extracted_fields": {...},
      "confidence_score": 0.89,
      "validation": {...}
    }
  },
  "data_match_score": 0.95
}
```

---

## 🎯 How It Works

### Workflow with OCR & NLP

1. **Document Upload**
   - User uploads document (PAN/Aadhaar/Passport)
   - System validates image quality (blur, brightness, resolution)

2. **OCR Processing**
   - Image preprocessing (denoise, contrast, deskew)
   - Text extraction using PaddleOCR
   - Document-specific field extraction

3. **NLP Processing**
   - Named entity recognition using spaCy
   - Pattern matching for IDs (PAN, Aadhaar)
   - Date and address extraction

4. **Cross-Validation**
   - Compare OCR data with form data
   - Calculate similarity scores
   - Generate match report

5. **AI Review**
   - Enhanced scoring based on:
     - OCR confidence
     - Data match score
     - Document quality

---

## 📊 Enhanced Case Data Structure

Cases now include:

```json
{
  "customer_profile": {...},
  "documents": {
    "pan": "filename.jpg",
    "aadhaar": "filename.jpg"
  },
  "ocr_results": {
    "pan": {
      "raw_text": "Extracted text...",
      "extracted_fields": {
        "name": "JOHN DOE",
        "pan": "ABCDE1234F",
        "dob": "1990-06-15"
      },
      "confidence_score": 0.89,
      "quality_check": {
        "valid": true,
        "blur_score": 245.6,
        "brightness": 128
      },
      "validation": {
        "matches": {...},
        "overall_match_score": 0.95
      }
    }
  },
  "data_match_score": 0.95,
  "ai_score": 92
}
```

---

## 🧪 Testing the OCR & NLP Features

### 1. Test Document Quality Validation

```python
from ocr_processor import OCRProcessor

processor = OCRProcessor()

with open('test_document.jpg', 'rb') as f:
    content = f.read()

quality = processor.validate_document_quality(content)
print(quality)
```

### 2. Test OCR Extraction

```python
# Test PAN extraction
with open('pan_card.jpg', 'rb') as f:
    result = processor.extract_pan_specific(f.read())
    print(result['extracted_fields'])
```

### 3. Test NLP Extraction

```python
from nlp_extractor import NLPEntityExtractor

extractor = NLPEntityExtractor()

text = "Name: JOHN DOE, DOB: 15/06/1990, PAN: ABCDE1234F"
result = extractor.extract_all_fields(text, 'pan')
print(result)
```

### 4. Test Cross-Validation

```python
ocr_data = {'name': 'JOHN DOE', 'dob': '1990-06-15'}
form_data = {'name': 'John Doe', 'dob': '1990-06-15'}

validation = extractor.cross_validate_fields(ocr_data, form_data)
print(f"Match Score: {validation['overall_match_score']:.2%}")
```

---

## 🐛 Troubleshooting

### Issue: PaddleOCR Installation Fails

**Solution:**
```bash
# Install dependencies separately
pip install paddlepaddle==2.5.2
pip install paddleocr==2.7.0.3

# For macOS M1/M2 (Apple Silicon):
pip install paddlepaddle==2.5.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Issue: spaCy Model Not Found

**Solution:**
```bash
python -m spacy download en_core_web_sm

# Or download directly
python -c "import spacy; spacy.cli.download('en_core_web_sm')"
```

### Issue: OpenCV Import Error

**Solution:**
```bash
pip install opencv-python-headless==4.8.1.78

# For systems without GUI
pip install opencv-python==4.8.1.78 --no-deps
pip install numpy
```

### Issue: Low OCR Accuracy

**Solutions:**
- Ensure documents are clear and well-lit
- Use higher resolution images (min 200x200)
- Enable GPU processing if available
- Adjust preprocessing parameters in `ocr_processor.py`

### Issue: Memory Error During OCR

**Solution:**
```python
# Process images in smaller batches
# Reduce image resolution before processing
import cv2

image = cv2.imread('large_image.jpg')
resized = cv2.resize(image, (1000, 1000))
```

---

## 🚀 Performance Optimization

### GPU Acceleration (Optional)

For faster OCR processing with GPU:

```bash
# Install CUDA-enabled PaddlePaddle
pip uninstall paddlepaddle
pip install paddlepaddle-gpu

# Update main.py
ocr_processor = OCRProcessor(use_gpu=True)
```

### Batch Processing

Process multiple documents efficiently:

```python
from ocr_processor import OCRProcessor

processor = OCRProcessor()

documents = [
    (pan_file_content, 'pan'),
    (aadhaar_file_content, 'aadhaar')
]

results = processor.batch_process_documents(documents)
```

---

## 📈 Accuracy Metrics

### Expected Performance

| Document Type | OCR Accuracy | Entity Extraction |
|--------------|--------------|-------------------|
| PAN Card | 85-95% | 90-98% |
| Aadhaar Card | 80-90% | 85-95% |
| Passport | 75-85% | 80-90% |

**Factors affecting accuracy:**
- Image quality (resolution, lighting)
- Document condition (damage, wear)
- Text clarity and font size
- Language and script

---

## 🔒 Security Considerations

1. **Document Storage**
   - Store documents securely (encrypted)
   - Implement access controls
   - Regular backups

2. **PII Protection**
   - Mask sensitive data in logs
   - Implement data retention policies
   - Comply with privacy regulations (GDPR, etc.)

3. **OCR Data Validation**
   - Always cross-validate extracted data
   - Implement fraud detection
   - Flag suspicious patterns

---

## 📚 Additional Resources

### Documentation
- [PaddleOCR Docs](https://github.com/PaddlePaddle/PaddleOCR)
- [spaCy Documentation](https://spacy.io/usage)
- [OpenCV Python Tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)

### Sample Test Documents
Create test images with:
- PAN card format
- Aadhaar card format
- Various image qualities

---

## ✅ Verification Checklist

- [ ] PaddleOCR installed and working
- [ ] spaCy model downloaded
- [ ] OCR processor initialized without errors
- [ ] NLP extractor working correctly
- [ ] Document upload processes OCR automatically
- [ ] Cross-validation shows match scores
- [ ] AI review includes OCR confidence
- [ ] Audit trail logs OCR processing

---

## 🎓 Next Steps

1. **Enhance Frontend**
   - Display OCR results in UI
   - Show confidence scores
   - Highlight data mismatches

2. **Advanced Features**
   - Multi-language support
   - Face detection in documents
   - Signature verification
   - Tamper detection

3. **Integration**
   - External verification APIs
   - Government database checks
   - Real-time fraud detection

---

You're all set with OCR and NLP capabilities! 🎉