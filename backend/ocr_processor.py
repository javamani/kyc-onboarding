# ocr_processor_fixed.py - Fixed version with PaddleOCR integration
import io
import os
from PIL import Image
import cv2
import numpy as np
from typing import Dict, Optional, Union, List
import re
from pdf2image import convert_from_bytes

class PaddleOCRProcessor:
    """
    Wrapper around PaddleOCR with proper image handling and quality validation
    Fixes both the 'validate_document_quality' error and PDF processing issues
    """
    
    def __init__(self, use_gpu: bool = False, lang: str = 'en'):
        """
        Initialize PaddleOCR processor
        
        Args:
            use_gpu: Whether to use GPU
            lang: Language for OCR
        """
        from paddleocr import PaddleOCR
        
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)
        self.lang = lang
    
    def validate_document_quality(self, file_content: bytes) -> Dict:
        """
        FIXED: Validate document quality before OCR processing
        This method was missing in PaddleOCR, causing the AttributeError
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            Validation result dictionary
        """
        try:
            # Try to load as image first
            img = self._load_image_from_bytes(file_content)
            
            if img is None:
                return {
                    'valid': False,
                    'reason': 'Cannot read image: Invalid image format or corrupted file',
                    'details': {}
                }
            
            # Check image dimensions
            height, width = img.shape[:2]
            
            if width < 100 or height < 100:
                return {
                    'valid': False,
                    'reason': f'Image too small: {width}x{height} pixels (minimum 100x100)',
                    'details': {'size': (width, height)}
                }
            
            # Check if image is too large
            if width > 10000 or height > 10000:
                return {
                    'valid': False,
                    'reason': f'Image too large: {width}x{height} pixels (maximum 10000x10000)',
                    'details': {'size': (width, height)}
                }
            
            # Check image content (not blank)
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            std_dev = np.std(gray)
            mean_brightness = np.mean(gray)
            
            if std_dev < 5:
                return {
                    'valid': False,
                    'reason': 'Image appears to be blank or has very low contrast',
                    'details': {'std_dev': float(std_dev), 'brightness': float(mean_brightness)}
                }
            
            if mean_brightness < 10 or mean_brightness > 250:
                return {
                    'valid': False,
                    'reason': f'Image brightness out of acceptable range: {mean_brightness:.2f}',
                    'details': {'brightness': float(mean_brightness)}
                }
            
            return {
                'valid': True,
                'reason': 'Document quality acceptable',
                'details': {
                    'size': (width, height),
                    'brightness': float(mean_brightness),
                    'contrast': float(std_dev),
                    'channels': len(img.shape)
                }
            }
            
        except Exception as e:
            return {
                'valid': False,
                'reason': f'Document quality check failed: {str(e)}',
                'details': {}
            }
    
    def _load_image_from_bytes(self, file_content: bytes) -> Optional[np.ndarray]:
        """
        FIXED: Load image from bytes with proper BytesIO handling
        Supports both regular images (JPG, PNG) and PDFs
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            OpenCV image (numpy array) or None
        """
        try:
            # First, try to detect if it's a PDF
            if file_content[:4] == b'%PDF':
                # It's a PDF - convert to images
                images = convert_from_bytes(file_content, dpi=300, first_page=1, last_page=1)
                if images:
                    # Convert PIL Image to OpenCV format
                    pil_img = images[0]
                    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                else:
                    return None
            
            # Not a PDF, try as regular image
            # CRITICAL FIX: Proper BytesIO handling
            img_io = io.BytesIO(file_content)
            img_io.seek(0)  # Ensure we're at the start
            
            # Try opening with PIL first
            try:
                pil_img = Image.open(img_io)
                pil_img.load()  # Force loading of image data
                
                # Convert PIL Image to OpenCV format
                img_array = np.array(pil_img)
                
                # Convert RGB to BGR if needed (OpenCV uses BGR)
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                else:
                    img_cv = img_array
                
                img_io.close()
                return img_cv
                
            except Exception as pil_error:
                # PIL failed, try direct OpenCV decode
                img_io.close()
                
                # Use OpenCV to decode from bytes
                nparr = np.frombuffer(file_content, np.uint8)
                img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img_cv is not None:
                    return img_cv
                else:
                    print(f"Failed to decode image: {str(pil_error)}")
                    return None
                    
        except Exception as e:
            print(f"Error loading image from bytes: {str(e)}")
            return None
    
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            img: OpenCV image (numpy array)
            
        Returns:
            Preprocessed image
        """
        try:
            # Convert to grayscale if needed
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            return thresh
            
        except Exception as e:
            print(f"Preprocessing failed, using original: {str(e)}")
            return img
    
    def extract_text_generic(self, file_content: bytes) -> Dict:
        """
        Extract text from document using PaddleOCR
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            OCR result dictionary
        """
        try:
            # Load image
            img = self._load_image_from_bytes(file_content)
            
            if img is None:
                return {
                    'status': 'error',
                    'error': 'Failed to load image',
                    'raw_text': '',
                    'confidence_score': 0.0
                }
            
            # Run PaddleOCR
            result = self.ocr.ocr(img, cls=True)
            
            if not result or not result[0]:
                return {
                    'status': 'error',
                    'error': 'No text detected in image',
                    'raw_text': '',
                    'confidence_score': 0.0
                }
            
            # Extract text and confidence
            text_lines = []
            confidences = []
            
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0]  # Text content
                    confidence = line[1][1]  # Confidence score
                    
                    text_lines.append(text)
                    confidences.append(confidence)
            
            raw_text = '\n'.join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'status': 'success',
                'raw_text': raw_text,
                'confidence_score': avg_confidence,
                'text_lines': text_lines,
                'line_confidences': confidences
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'OCR processing failed: {str(e)}',
                'raw_text': '',
                'confidence_score': 0.0
            }
    
    def extract_pan_specific(self, file_content: bytes) -> Dict:
        """
        Extract PAN-specific information
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            Extracted PAN data
        """
        result = self.extract_text_generic(file_content)
        
        if result['status'] == 'error':
            return result
        
        text = result['raw_text']
        
        # Extract PAN number
        pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
        pan_match = re.search(pan_pattern, text)
        
        # Extract name
        name = self._extract_name_from_text(text)
        
        # Extract date of birth
        dob = self._extract_dob_from_text(text)
        
        result['document_type'] = 'pan'
        result['extracted_fields'] = {
            'pan_number': pan_match.group(0) if pan_match else None,
            'name': name,
            'dob': dob
        }
        
        return result
    
    def extract_aadhaar_specific(self, file_content: bytes) -> Dict:
        """
        Extract Aadhaar-specific information
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            Extracted Aadhaar data
        """
        result = self.extract_text_generic(file_content)
        
        if result['status'] == 'error':
            return result
        
        text = result['raw_text']
        
        # Extract Aadhaar number (with or without spaces)
        aadhaar_pattern = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
        aadhaar_match = re.search(aadhaar_pattern, text)
        
        # Extract name
        name = self._extract_name_from_text(text)
        
        # Extract date of birth
        dob = self._extract_dob_from_text(text)
        
        # Extract address
        address = self._extract_address_from_text(text)
        
        result['document_type'] = 'aadhaar'
        result['extracted_fields'] = {
            'aadhaar_number': aadhaar_match.group(0) if aadhaar_match else None,
            'name': name,
            'dob': dob,
            'address': address
        }
        
        return result
    
    def extract_passport_specific(self, file_content: bytes) -> Dict:
        """
        Extract Passport-specific information
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            Extracted Passport data
        """
        result = self.extract_text_generic(file_content)
        
        if result['status'] == 'error':
            return result
        
        text = result['raw_text']
        
        # Extract passport number
        passport_pattern = r'\b[A-Z]{1}\d{7}\b'
        passport_match = re.search(passport_pattern, text)
        
        # Extract name
        name = self._extract_name_from_text(text)
        
        # Extract date of birth
        dob = self._extract_dob_from_text(text)
        
        # Extract address
        address = self._extract_address_from_text(text)
        
        result['document_type'] = 'passport'
        result['extracted_fields'] = {
            'passport_number': passport_match.group(0) if passport_match else None,
            'name': name,
            'dob': dob,
            'address': address
        }
        
        return result
    
    def _extract_name_from_text(self, text: str) -> Optional[str]:
        """Extract name from OCR text"""
        # Look for name patterns
        name_patterns = [
            r'(?i)name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                # Filter out common non-name words
                if not any(word in name for word in ['Income', 'Tax', 'Government', 'India', 'Permanent']):
                    return name
        
        return None
    
    def _extract_dob_from_text(self, text: str) -> Optional[str]:
        """Extract date of birth from text"""
        date_patterns = [
            r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b',
            r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b',
            r'\b(\d{2}\s+[A-Za-z]+\s+\d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_address_from_text(self, text: str) -> Optional[str]:
        """Extract address from text"""
        # Look for address keywords and extract surrounding context
        lines = text.split('\n')
        address_keywords = ['address', 'residence', 'house', 'flat', 'street', 'pin']
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in address_keywords):
                # Get this line and next 2-3 lines
                end_idx = min(i + 3, len(lines))
                address_lines = lines[i:end_idx]
                return ' '.join([l.strip() for l in address_lines if l.strip()])
        
        return None


# For backward compatibility with existing code
OCRProcessor = PaddleOCRProcessor


if __name__ == "__main__":
    print("Testing Fixed PaddleOCR Processor")
    print("=" * 60)
    
    # Initialize processor
    processor = PaddleOCRProcessor(use_gpu=False, lang='en')
    
    # Create a test image
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw sample PAN card text
    text_content = [
        "INCOME TAX DEPARTMENT",
        "GOVT. OF INDIA",
        "",
        "Permanent Account Number",
        "ABCDE1234F",
        "",
        "Name: JOHN DOE",
        "Father's Name: ROBERT DOE",
        "Date of Birth: 15/06/1990"
    ]
    
    y = 20
    for line in text_content:
        draw.text((20, y), line, fill='black')
        y += 30
    
    # Convert to bytes
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    img_bytes = img_io.getvalue()
    img_io.close()
    
    # Test quality validation
    print("\n1. Testing quality validation...")
    quality = processor.validate_document_quality(img_bytes)
    print(f"   Valid: {quality['valid']}")
    print(f"   Reason: {quality['reason']}")
    print(f"   Details: {quality.get('details', {})}")
    
    # Test OCR extraction
    if quality['valid']:
        print("\n2. Testing PAN extraction...")
        result = processor.extract_pan_specific(img_bytes)
        print(f"   Status: {result['status']}")
        if result['status'] == 'success':
            print(f"   Confidence: {result['confidence_score']:.2%}")
            print(f"   Extracted Fields: {result.get('extracted_fields', {})}")
            print(f"   Raw Text Preview: {result['raw_text'][:100]}...")
    
    print("\n" + "=" * 60)
    print("Testing complete!")