# ocr_processor.py - Complete OCR & Document Processing Module
import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image
import io
import re
from typing import Dict, List, Tuple, Optional
import base64

class OCRProcessor:
    """
    OCR Document Processing using PaddleOCR
    Supports scanned documents, photographed documents, and various image formats
    """
    
    def __init__(self, use_gpu: bool = False, lang: str = 'en'):
        """
        Initialize PaddleOCR
        Args:
            use_gpu: Whether to use GPU for processing
            lang: Language for OCR (default: 'en', supports 'en', 'hi', etc.)
        """
        self.ocr = PaddleOCR(
            use_angle_cls=True,  # Enable angle classification
            lang=lang,
            use_gpu=use_gpu,
            show_log=False
        )
        
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        - Convert to grayscale
        - Denoise
        - Adjust contrast
        - Deskew if needed
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)
        
        # Adaptive threshold for better text extraction
        binary = cv2.adaptiveThreshold(
            contrast, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        Correct skewed/rotated documents
        """
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        if abs(angle) < 0.5:  # Skip if almost straight
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        return rotated
    
    def validate_document_quality(self, file_content: bytes) -> Dict:
        """
        Validate if document is of sufficient quality for OCR
        Checks: blur, brightness, contrast, resolution
        """
        try:
            # Try OpenCV decode
            nparr = np.frombuffer(file_content, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Fallback to PIL if OpenCV fails
            if image is None:
                try:
                    pil_image = Image.open(io.BytesIO(file_content))
                    if pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')
                    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    print(f"✅ PIL successfully converted image: {pil_image.format}, {pil_image.size}")
                except Exception as pil_error:
                    print(f"❌ PIL conversion failed: {pil_error}")
                    return {
                        'valid': False, 
                        'reason': f'Cannot read image: {str(pil_error)[:100]}'
                    }
            
            if image is None:
                return {
                    'valid': False, 
                    'reason': 'Unsupported image format. Use JPG or PNG.'
                }
            
            # Check resolution
            height, width = image.shape[:2]
            if height < 200 or width < 200:
                return {
                    'valid': False, 
                    'reason': f'Resolution too low: {width}x{height}. Min: 200x200'
                }
            
            # Check for extremely large images
            if height > 5000 or width > 5000:
                return {
                    'valid': False, 
                    'reason': f'Image too large: {width}x{height}. Max: 5000x5000'
                }
            
            # Check blur
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if laplacian_var < 50:
                return {
                    'valid': False, 
                    'reason': f'Image too blurry (score: {laplacian_var:.1f})',
                    'blur_score': laplacian_var
                }
            
            # Check brightness
            brightness = np.mean(gray)
            if brightness < 40 or brightness > 220:
                return {
                    'valid': False, 
                    'reason': f'Poor lighting (brightness: {brightness:.1f})',
                    'brightness': brightness
                }
            
            return {
                'valid': True,
                'resolution': f'{width}x{height}',
                'blur_score': float(laplacian_var),
                'brightness': float(brightness)
            }
            
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return {
                'valid': False, 
                'reason': f'Validation error: {str(e)[:100]}'
            }
    
    def extract_text_from_file(self, file_content: bytes, doc_type: str = 'general') -> Dict:
        """
        Extract text from uploaded file
        Args:
            file_content: Binary content of the file
            doc_type: Type of document (pan, aadhaar, passport, general)
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Convert bytes to image
            nparr = np.frombuffer(file_content, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                # Try with PIL for other formats
                pil_image = Image.open(io.BytesIO(file_content))
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Deskew if needed
            deskewed_image = self.deskew_image(processed_image)
            
            # Perform OCR
            result = self.ocr.ocr(deskewed_image, cls=True)
            
            # Extract text and confidence scores
            extracted_data = {
                'raw_text': '',
                'structured_text': [],
                'confidence_scores': [],
                'document_type': doc_type,
                'status': 'success'
            }
            
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    bbox = line[0]  # Bounding box coordinates
                    
                    extracted_data['structured_text'].append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': bbox
                    })
                    extracted_data['confidence_scores'].append(confidence)
                    extracted_data['raw_text'] += text + '\n'
            
            # Calculate average confidence
            if extracted_data['confidence_scores']:
                extracted_data['avg_confidence'] = sum(
                    extracted_data['confidence_scores']
                ) / len(extracted_data['confidence_scores'])
            else:
                extracted_data['avg_confidence'] = 0.0
            
            return extracted_data
            
        except Exception as e:
            return {
                'status': 'error',
                'error_message': str(e),
                'raw_text': '',
                'structured_text': [],
                'confidence_scores': [],
                'avg_confidence': 0.0
            }
    
    def extract_text_from_base64(self, base64_string: str, doc_type: str = 'general') -> Dict:
        """
        Extract text from base64 encoded image
        """
        try:
            # Decode base64
            img_data = base64.b64decode(base64_string)
            return self.extract_text_from_file(img_data, doc_type)
        except Exception as e:
            return {
                'status': 'error',
                'error_message': f'Base64 decode error: {str(e)}',
                'raw_text': '',
                'structured_text': []
            }
    
    def extract_pan_specific(self, file_content: bytes) -> Dict:
        """
        Extract PAN card specific information
        """
        ocr_result = self.extract_text_from_file(file_content, 'pan')
        
        if ocr_result['status'] == 'error':
            return ocr_result
        
        text = ocr_result['raw_text']
        
        # PAN number pattern: ABCDE1234F
        pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
        pan_match = re.search(pan_pattern, text)
        
        # Name extraction (usually in capital letters)
        name_pattern = r'[A-Z\s]{3,50}'
        names = re.findall(name_pattern, text)
        
        # Date of birth pattern
        dob_pattern = r'\d{2}[/-]\d{2}[/-]\d{4}'
        dob_match = re.search(dob_pattern, text)
        
        ocr_result['extracted_fields'] = {
            'pan_number': pan_match.group(0) if pan_match else None,
            'name': names[0].strip() if names else None,
            'dob': dob_match.group(0) if dob_match else None
        }
        
        return ocr_result
    
    def extract_aadhaar_specific(self, file_content: bytes) -> Dict:
        """
        Extract Aadhaar card specific information
        """
        ocr_result = self.extract_text_from_file(file_content, 'aadhaar')
        
        if ocr_result['status'] == 'error':
            return ocr_result
        
        text = ocr_result['raw_text']
        
        # Aadhaar number pattern: 1234 5678 9012
        aadhaar_pattern = r'\d{4}\s\d{4}\s\d{4}'
        aadhaar_match = re.search(aadhaar_pattern, text)
        
        # Alternative pattern without spaces
        if not aadhaar_match:
            aadhaar_pattern_alt = r'\d{12}'
            aadhaar_match = re.search(aadhaar_pattern_alt, text)
        
        # Name extraction
        name_lines = [line['text'] for line in ocr_result['structured_text'] 
                     if line['confidence'] > 0.7 and len(line['text']) > 3]
        
        # Date of birth
        dob_pattern = r'\d{2}[/-]\d{2}[/-]\d{4}'
        dob_match = re.search(dob_pattern, text)
        
        # Gender
        gender_pattern = r'\b(MALE|FEMALE|Male|Female)\b'
        gender_match = re.search(gender_pattern, text, re.IGNORECASE)
        
        # Address (usually longer text lines)
        address_lines = [line['text'] for line in ocr_result['structured_text'] 
                        if len(line['text']) > 20]
        
        ocr_result['extracted_fields'] = {
            'aadhaar_number': aadhaar_match.group(0) if aadhaar_match else None,
            'name': name_lines[0] if name_lines else None,
            'dob': dob_match.group(0) if dob_match else None,
            'gender': gender_match.group(0) if gender_match else None,
            'address': ' '.join(address_lines[:3]) if address_lines else None
        }
        
        return ocr_result
    
    def extract_passport_specific(self, file_content: bytes) -> Dict:
        """
        Extract Passport specific information
        """
        ocr_result = self.extract_text_from_file(file_content, 'passport')
        
        if ocr_result['status'] == 'error':
            return ocr_result
        
        text = ocr_result['raw_text']
        
        # Passport number pattern (India): A-Z followed by 7 digits
        passport_pattern = r'[A-Z]{1}\d{7}'
        passport_match = re.search(passport_pattern, text)
        
        # Name extraction
        name_pattern = r'(?:Given Name|Surname)[:\s]+([A-Z\s]+)'
        name_matches = re.findall(name_pattern, text, re.IGNORECASE)
        
        # Date of birth
        dob_pattern = r'\d{2}[/-]\d{2}[/-]\d{4}'
        dob_matches = re.findall(dob_pattern, text)
        
        # Place of birth
        pob_pattern = r'(?:Place of Birth)[:\s]+([A-Z\s]+)'
        pob_match = re.search(pob_pattern, text, re.IGNORECASE)
        
        ocr_result['extracted_fields'] = {
            'passport_number': passport_match.group(0) if passport_match else None,
            'name': ' '.join(name_matches) if name_matches else None,
            'dob': dob_matches[0] if dob_matches else None,
            'place_of_birth': pob_match.group(1).strip() if pob_match else None
        }
        
        return ocr_result
    
    def batch_process_documents(self, documents: List[Tuple[bytes, str]]) -> List[Dict]:
        """
        Process multiple documents in batch
        Args:
            documents: List of tuples (file_content, doc_type)
        Returns:
            List of OCR results
        """
        results = []
        
        for file_content, doc_type in documents:
            if doc_type == 'pan':
                result = self.extract_pan_specific(file_content)
            elif doc_type == 'aadhaar':
                result = self.extract_aadhaar_specific(file_content)
            elif doc_type == 'passport':
                result = self.extract_passport_specific(file_content)
            else:
                result = self.extract_text_from_file(file_content, doc_type)
            
            results.append(result)
        
        return results


# Utility functions
def format_extracted_data(ocr_result: Dict) -> str:
    """
    Format OCR result for display
    """
    if ocr_result['status'] == 'error':
        return f"Error: {ocr_result.get('error_message', 'Unknown error')}"
    
    output = f"Document Type: {ocr_result['document_type']}\n"
    output += f"Average Confidence: {ocr_result['avg_confidence']:.2%}\n\n"
    
    if 'extracted_fields' in ocr_result:
        output += "Extracted Fields:\n"
        for key, value in ocr_result['extracted_fields'].items():
            output += f"  {key}: {value}\n"
    
    output += f"\nRaw Text:\n{ocr_result['raw_text']}"
    
    return output


if __name__ == "__main__":
    # Example usage
    processor = OCRProcessor(use_gpu=False, lang='en')
    
    print("OCRProcessor initialized successfully!")
    print(f"Available methods: {[m for m in dir(processor) if not m.startswith('_')]}")
    
    # Test if validate_document_quality exists
    if hasattr(processor, 'validate_document_quality'):
        print("✅ validate_document_quality method found")
    else:
        print("❌ validate_document_quality method NOT found")