# Testing Guide - OCR & NLP Features

## 🧪 Complete Testing Workflow

### 1. Setup Test Environment

```bash
# Terminal 1: Start MongoDB
mongosh

# Terminal 2: Start Backend
cd backend
source venv/bin/activate
python main.py

# Terminal 3: Start Frontend
cd frontend
npm start
```

---

## 📸 Create Test Documents

### Option A: Use Sample Images

Create test documents with the following content:

#### PAN Card Sample
```
INCOME TAX DEPARTMENT
GOVT. OF INDIA
Permanent Account Number Card

ABCDE1234F

Name: JOHN DOE
Father's Name: ROBERT DOE
Date of Birth: 15/06/1990
```

#### Aadhaar Card Sample
```
GOVERNMENT OF INDIA

1234 5678 9012

Name: JOHN DOE
Date of Birth: 15/06/1990
Gender: Male
Address: 123 Main Street
        Mumbai Maharashtra
        400001
```

### Option B: Download Sample Documents

You can create these as images using any text editor and screenshot tool, or use actual scanned copies (ensure they're test data, not real documents).

---

## 🎯 Testing Scenarios

### Scenario 1: Happy Path - Perfect Match

**Steps:**
1. Open http://localhost:3000
2. Fill form with:
   - Name: `JOHN DOE`
   - DOB: `1990-06-15`
   - Address: `123 Main Street Mumbai 400001`
   - Email: `john@example.com`
   - Phone: `+919876543210`

3. Upload PAN card image with same details
4. Click "Create Case with OCR"

**Expected Results:**
- ✅ Document uploaded successfully
- ✅ OCR Confidence: 85-95%
- ✅ Data Match Score: 90-100%
- ✅ Extracted fields match form data
- ✅ AI Score: 90-100

---

### Scenario 2: Partial Match

**Steps:**
1. Fill form with:
   - Name: `John Doe` (different case)
   - DOB: `1990-06-15`
   - Address: `123 Main St Mumbai` (shorter)

2. Upload document with:
   - Name: `JOHN DOE`
   - DOB: `15/06/1990`
   - Address: `123 Main Street Mumbai 400001`

**Expected Results:**
- ✅ OCR processes successfully
- ⚠️ Data Match Score: 70-85%
- ⚠️ Name shows as partial match
- ⚠️ Address shows as partial match
- ✅ AI Score: 75-85

---

### Scenario 3: Poor Quality Document

**Steps:**
1. Take a blurry photo of text
2. Try to upload it

**Expected Results:**
- ❌ Document quality check fails
- ❌ Error message: "Image too blurry"
- ℹ️ Suggestion to upload better quality image

---

### Scenario 4: Multiple Documents

**Steps:**
1. Create case with basic info
2. Upload PAN card
3. Wait for OCR processing
4. Upload Aadhaar card
5. Wait for OCR processing
6. Check case details

**Expected Results:**
- ✅ Each document processed separately
- ✅ OCR results shown for each document
- ✅ Combined data match score
- ✅ All fields extracted and validated

---

### Scenario 5: Complete Workflow

**As MAKER:**
1. Create case with customer details
2. Upload PAN card → See OCR confidence
3. Upload Aadhaar card → See OCR confidence
4. Review extracted data
5. Submit case

**As CHECKER:**
1. Switch to CHECKER role
2. View submitted case
3. Click "Details" to see:
   - OCR results for each document
   - Confidence scores
   - Data validation results
   - Audit trail with OCR events
4. Approve or reject based on OCR confidence

---

## 🔍 What to Check

### OCR Quality Indicators

**Good Quality (Proceed):**
- ✅ OCR Confidence > 80%
- ✅ Data Match > 80%
- ✅ All required fields extracted
- ✅ No quality warnings

**Medium Quality (Review):**
- ⚠️ OCR Confidence 60-80%
- ⚠️ Data Match 60-80%
- ⚠️ Some fields missing
- ⚠️ Minor quality issues

**Poor Quality (Reject):**
- ❌ OCR Confidence < 60%
- ❌ Data Match < 60%
- ❌ Multiple fields missing
- ❌ Quality check failed

---

## 🧾 Sample API Tests

### Test OCR Endpoint

```bash
# Create a case first
CASE_ID=$(curl -X POST http://localhost:8000/api/cases \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "dob": "1990-06-15",
    "address": "123 Main Street Mumbai",
    "user_id": "user1",
    "user_name": "John Maker",
    "user_role": "MAKER"
  }' | jq -r '.id')

echo "Case ID: $CASE_ID"

# Upload document with OCR
curl -X POST "http://localhost:8000/api/cases/$CASE_ID/upload" \
  -F "doc_type=pan" \
  -F "file=@pan_card.jpg"

# Get OCR results
curl "http://localhost:8000/api/cases/$CASE_ID/ocr-results" | jq '.'

# Get case with all details
curl "http://localhost:8000/api/cases/$CASE_ID" | jq '.'
```

---

## 📊 Understanding OCR Results

### Confidence Score Breakdown

```json
{
  "ocr_results": {
    "pan": {
      "confidence_score": 0.89,  // 89% confidence
      "extracted_fields": {
        "name": "JOHN DOE",
        "pan": "ABCDE1234F",
        "dob": "1990-06-15"
      },
      "validation": {
        "overall_match_score": 0.95,  // 95% match with form
        "matches": {
          "name": {
            "form": "John Doe",
            "ocr": "JOHN DOE",
            "similarity": 0.95
          }
        }
      }
    }
  }
}
```

**Interpretation:**
- **confidence_score**: How confident OCR is about text extraction
- **overall_match_score**: How well OCR data matches form data
- **similarity**: String similarity for each field (0.0 to 1.0)

---

## 🐛 Common Issues & Solutions

### Issue 1: OCR Returns Empty Text

**Cause:** Image quality too poor or wrong format

**Solution:**
```bash
# Check image format
file document.jpg

# Test with sample
python -c "
from ocr_processor import OCRProcessor
processor = OCRProcessor()
with open('document.jpg', 'rb') as f:
    quality = processor.validate_document_quality(f.read())
    print(quality)
"
```

### Issue 2: Wrong Fields Extracted

**Cause:** Document layout not recognized

**Solution:**
- Ensure document follows standard format
- Check if document type is correct (pan/aadhaar/passport)
- Try with different image (better quality)

### Issue 3: Low Confidence Scores

**Cause:** Poor image quality

**Solution:**
1. Retake photo with good lighting
2. Ensure text is clearly visible
3. Remove shadows and glare
4. Use higher resolution

### Issue 4: Data Mismatch

**Cause:** Form data doesn't match document

**Solution:**
1. Verify form data is correct
2. Check for typos
3. Ensure date formats match
4. Review case in details view

---

## 📈 Performance Benchmarks

### Expected Processing Times

| Operation | Time |
|-----------|------|
| Document Upload | < 1s |
| OCR Processing | 2-5s |
| NLP Extraction | < 1s |
| Validation | < 1s |
| **Total** | **3-7s** |

### Accuracy Expectations

| Document Type | OCR Accuracy | Entity Extraction |
|---------------|--------------|-------------------|
| PAN Card | 85-95% | 90-98% |
| Aadhaar Card | 80-90% | 85-95% |
| Passport | 75-85% | 80-90% |

---

## ✅ Test Checklist

### Frontend Tests
- [ ] Can create case with customer details
- [ ] Can upload documents
- [ ] Shows upload progress
- [ ] Displays OCR confidence scores
- [ ] Shows data match scores
- [ ] Displays extracted fields
- [ ] Shows validation results
- [ ] Audit trail includes OCR events

### Backend Tests
- [ ] OCR processor initializes correctly
- [ ] NLP extractor initializes correctly
- [ ] Document quality validation works
- [ ] OCR extraction returns results
- [ ] NLP extraction finds entities
- [ ] Cross-validation calculates scores
- [ ] AI review uses OCR data
- [ ] Audit trail logs OCR events

### Integration Tests
- [ ] Upload triggers OCR automatically
- [ ] OCR results stored in database
- [ ] Frontend displays OCR results
- [ ] Data match affects AI score
- [ ] CHECKER can see OCR data
- [ ] Audit trail is complete

---

## 🎓 Advanced Testing

### Test Different Image Qualities

```python
# test_image_quality.py
from ocr_processor import OCRProcessor
import cv2

processor = OCRProcessor()

# Test with different blur levels
image = cv2.imread('original.jpg')

for blur in [3, 7, 15]:
    blurred = cv2.GaussianBlur(image, (blur, blur), 0)
    cv2.imwrite(f'blurred_{blur}.jpg', blurred)
    
    with open(f'blurred_{blur}.jpg', 'rb') as f:
        quality = processor.validate_document_quality(f.read())
        print(f"Blur {blur}: {quality}")
```

### Test Extraction Accuracy

```python
# test_extraction.py
from nlp_extractor import NLPEntityExtractor

extractor = NLPEntityExtractor()

test_cases = [
    ("Name: JOHN DOE, PAN: ABCDE1234F", "ABCDE1234F"),
    ("DOB: 15/06/1990", "1990-06-15"),
    ("Aadhaar: 1234 5678 9012", "1234 5678 9012"),
]

for text, expected in test_cases:
    result = extractor.extract_all_fields(text, 'general')
    print(f"Text: {text}")
    print(f"Expected: {expected}")
    print(f"Got: {result}")
    print()
```

---

## 📝 Test Report Template

```
Test Date: YYYY-MM-DD
Tester: [Your Name]

Case Details:
- Case ID: _______
- Customer Name: _______
- Documents Uploaded: [ ] PAN [ ] Aadhaar [ ] Passport

OCR Results:
- PAN Confidence: _____%
- Aadhaar Confidence: _____%
- Data Match Score: _____%

Validation:
- [ ] All required fields extracted
- [ ] Data matches form
- [ ] No quality issues
- [ ] AI score > 80

Issues Found:
1. _______
2. _______

Status: [ ] PASS [ ] FAIL

Notes:
_______
```

---

Happy Testing! 🚀