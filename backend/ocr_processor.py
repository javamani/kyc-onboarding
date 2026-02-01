import io
from PIL import Image
import pytesseract
from typing import Dict, Optional, Union
import cv2
import numpy as np

class OCRProcessor:
    """
    OCR processor with proper BytesIO handling for the RAG Compliance Engine
    Fixes the "cannot identify image file" error
    """
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize OCR processor
        
        Args:
            tesseract_cmd: Path to tesseract executable (if not in PATH)
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def process_image_for_ocr(self, image_source: Union[bytes, str, Image.Image]) -> Dict:
        """
        Process image for OCR with proper error handling
        
        Args:
            image_source: Can be bytes, file path, or PIL Image
            
        Returns:
            Dictionary with OCR results and processing info
        """
        try:
            # Convert to PIL Image based on input type
            img = self._load_image(image_source)
            
            if img is None:
                return {
                    'success': False,
                    'error': 'Failed to load image',
                    'text': None
                }
            
            # Preprocess image for better OCR
            processed_img = self._preprocess_image(img)
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_img)
            
            # Get additional OCR data (confidence, bounding boxes, etc.)
            ocr_data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'success': True,
                'text': text.strip(),
                'confidence': avg_confidence,
                'word_count': len(text.split()),
                'ocr_data': ocr_data,
                'image_size': img.size
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'OCR processing failed: {str(e)}',
                'text': None
            }
    
    def _load_image(self, image_source: Union[bytes, str, Image.Image]) -> Optional[Image.Image]:
        """
        Load image from various sources with proper BytesIO handling
        
        Args:
            image_source: bytes, file path, or PIL Image
            
        Returns:
            PIL Image object or None
        """
        try:
            if isinstance(image_source, Image.Image):
                # Already a PIL Image
                return image_source.copy()
            
            elif isinstance(image_source, bytes):
                # CRITICAL FIX: Proper BytesIO handling
                img_io = io.BytesIO(image_source)
                img_io.seek(0)  # Ensure we're at the start
                
                # Open and load the image
                img = Image.open(img_io)
                img.load()  # Force loading of image data
                
                # Create a copy to avoid BytesIO closure issues
                img_copy = img.copy()
                
                # Close the BytesIO object
                img_io.close()
                
                return img_copy
            
            elif isinstance(image_source, str):
                # File path
                img = Image.open(image_source)
                img.load()
                return img
            
            else:
                print(f"Unsupported image source type: {type(image_source)}")
                return None
                
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            return None
    
    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy
        
        Args:
            img: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # Convert to numpy array for OpenCV processing
            img_array = np.array(img)
            
            # Convert to grayscale if not already
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL Image
            processed_img = Image.fromarray(thresh)
            
            return processed_img
            
        except Exception as e:
            print(f"Preprocessing failed, using original image: {str(e)}")
            return img
    
    def quality_check_before_ocr(self, image_source: Union[bytes, str, Image.Image]) -> Dict:
        """
        Perform quality check before OCR processing
        
        Args:
            image_source: Image to check
            
        Returns:
            Quality check results
        """
        try:
            img = self._load_image(image_source)
            
            if img is None:
                return {
                    'passed': False,
                    'reason': 'Failed to load image',
                    'details': {}
                }
            
            width, height = img.size
            
            # Check minimum dimensions
            if width < 100 or height < 100:
                return {
                    'passed': False,
                    'reason': f'Image too small: {width}x{height}',
                    'details': {'size': (width, height)}
                }
            
            # Check if image is blank/empty
            img_array = np.array(img.convert('L'))
            std_dev = np.std(img_array)
            
            if std_dev < 10:
                return {
                    'passed': False,
                    'reason': 'Image appears to be blank or has very low contrast',
                    'details': {'std_dev': float(std_dev)}
                }
            
            # Check brightness
            mean_brightness = np.mean(img_array)
            
            if mean_brightness < 20 or mean_brightness > 250:
                return {
                    'passed': False,
                    'reason': f'Image brightness out of range: {mean_brightness:.2f}',
                    'details': {'brightness': float(mean_brightness)}
                }
            
            return {
                'passed': True,
                'reason': 'Image quality acceptable',
                'details': {
                    'size': (width, height),
                    'brightness': float(mean_brightness),
                    'contrast': float(std_dev)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'reason': f'Quality check failed: {str(e)}',
                'details': {}
            }


class DocumentQualityValidator:
    """
    Validates document quality before processing
    This is the component that was causing your original error
    """
    
    @staticmethod
    def validate_image_document(file_data: bytes, filename: str) -> Dict:
        """
        FIXED VERSION: Validate image document with proper BytesIO handling
        
        Args:
            file_data: Raw image bytes
            filename: Original filename
            
        Returns:
            Validation result dictionary
        """
        try:
            # CRITICAL FIX: Create BytesIO and seek to start
            img_io = io.BytesIO(file_data)
            img_io.seek(0)  # This is the key fix!
            
            # Try to open the image
            img = Image.open(img_io)
            
            # Verify it's a valid image
            img.verify()
            
            # Close and reopen for actual processing (verify() closes the file)
            img_io.close()
            
            # Reopen for processing
            img_io = io.BytesIO(file_data)
            img_io.seek(0)
            img = Image.open(img_io)
            img.load()  # Load image data into memory
            
            # Perform quality checks
            width, height = img.size
            
            quality_result = {
                'success': True,
                'format': img.format,
                'mode': img.mode,
                'size': (width, height),
                'filename': filename
            }
            
            # Check dimensions
            if width < 100 or height < 100:
                quality_result['success'] = False
                quality_result['error'] = f'Image too small: {width}x{height}'
            
            # Check file size (in bytes)
            file_size = len(file_data)
            if file_size > 50 * 1024 * 1024:  # 50MB
                quality_result['success'] = False
                quality_result['error'] = f'File too large: {file_size / (1024*1024):.2f}MB'
            
            img_io.close()
            
            return quality_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Document quality check failed: {str(e)}',
                'filename': filename
            }


# Integration example with your existing modules
class RAGDocumentProcessor:
    """
    Complete document processor for RAG-based compliance engine
    Integrates upload, OCR, and quality checks
    """
    
    def __init__(self, upload_dir: str = "./compliance_docs"):
        from document_upload_handler import DocumentUploadHandler
        
        self.upload_handler = DocumentUploadHandler(upload_dir=upload_dir)
        self.ocr_processor = OCRDocumentProcessor()
        self.validator = DocumentQualityValidator()
    
    def process_document(self, file_data: bytes, filename: str, 
                        user_id: str = None, doc_type: str = None) -> Dict:
        """
        Complete document processing pipeline
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            user_id: User who uploaded
            doc_type: Document type (regulation, policy, etc.)
            
        Returns:
            Complete processing result
        """
        result = {
            'success': False,
            'stages': {}
        }
        
        try:
            # Stage 1: Upload and save
            upload_result = self.upload_handler.process_upload(
                file_data, filename, user_id, doc_type
            )
            result['stages']['upload'] = upload_result
            
            if not upload_result['success']:
                result['error'] = upload_result['error']
                return result
            
            file_type = upload_result['file_info']['file_type']
            
            # Stage 2: Quality check (for images)
            if file_type == 'image':
                quality_result = self.validator.validate_image_document(file_data, filename)
                result['stages']['quality_check'] = quality_result
                
                if not quality_result['success']:
                    result['error'] = quality_result['error']
                    return result
                
                # Stage 3: OCR processing
                ocr_result = self.ocr_processor.process_image_for_ocr(file_data)
                result['stages']['ocr'] = ocr_result
                
                if not ocr_result['success']:
                    result['error'] = ocr_result['error']
                    return result
                
                result['extracted_text'] = ocr_result['text']
                result['ocr_confidence'] = ocr_result['confidence']
            
            # Add more processing stages for other file types (PDF, DOCX, etc.)
            
            result['success'] = True
            result['file_path'] = upload_result['file_info']['file_path']
            
            return result
            
        except Exception as e:
            result['error'] = f'Document processing failed: {str(e)}'
            return result


# Test the fixed implementation
if __name__ == "__main__":
    print("Testing Fixed OCR Document Processor")
    print("=" * 50)
    
    # Create a simple test image
    from PIL import Image, ImageDraw, ImageFont
    
    # Create test image with text
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 80), "Sample Compliance Document", fill='black')
    
    # Convert to bytes
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    img_bytes = img_io.getvalue()
    img_io.close()
    
    # Test quality validation
    validator = DocumentQualityValidator()
    validation_result = validator.validate_image_document(img_bytes, "test.png")
    
    print(f"\nValidation Result: {validation_result}")
    
    # Test OCR
    ocr_processor = OCRDocumentProcessor()
    quality_check = ocr_processor.quality_check_before_ocr(img_bytes)
    
    print(f"\nQuality Check: {quality_check}")
    
    if quality_check['passed']:
        ocr_result = ocr_processor.process_image_for_ocr(img_bytes)
        print(f"\nOCR Result:")
        print(f"Success: {ocr_result['success']}")
        if ocr_result['success']:
            print(f"Extracted Text: {ocr_result['text']}")
            print(f"Confidence: {ocr_result['confidence']:.2f}%")
