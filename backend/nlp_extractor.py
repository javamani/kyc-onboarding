# nlp_extractor.py
import spacy
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import dateparser

class NLPEntityExtractor:
    """
    NLP-based Entity Extraction using spaCy and Regex
    Extracts: Name, Date of Birth, Address, PAN, Aadhaar numbers
    """
    
    def __init__(self, model_name: str = 'en_core_web_sm'):
        """
        Initialize spaCy model
        Args:
            model_name: spaCy model to use (default: en_core_web_sm)
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Downloading spaCy model {model_name}...")
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', model_name])
            self.nlp = spacy.load(model_name)
        
        # Add custom patterns for Indian entities
        self._add_custom_patterns()
    
    def _add_custom_patterns(self):
        """
        Add custom entity recognition patterns for Indian documents
        """
        from spacy.matcher import Matcher
        
        self.matcher = Matcher(self.nlp.vocab)
        
        # PAN pattern: ABCDE1234F
        pan_pattern = [
            {"TEXT": {"REGEX": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"}}
        ]
        self.matcher.add("PAN", [pan_pattern])
        
        # Aadhaar pattern: 1234 5678 9012 or 123456789012
        aadhaar_pattern_spaced = [
            {"TEXT": {"REGEX": r"^\d{4}$"}},
            {"TEXT": {"REGEX": r"^\d{4}$"}},
            {"TEXT": {"REGEX": r"^\d{4}$"}}
        ]
        aadhaar_pattern_continuous = [
            {"TEXT": {"REGEX": r"^\d{12}$"}}
        ]
        self.matcher.add("AADHAAR", [aadhaar_pattern_spaced, aadhaar_pattern_continuous])
    
    def extract_entities(self, text: str) -> Dict:
        """
        Extract all entities from text using spaCy NER
        """
        doc = self.nlp(text)
        
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'custom_entities': {
                'pan': [],
                'aadhaar': []
            }
        }
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                entities['persons'].append({
                    'text': ent.text,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
            elif ent.label_ == 'ORG':
                entities['organizations'].append(ent.text)
            elif ent.label_ in ['GPE', 'LOC']:
                entities['locations'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
        
        # Extract custom patterns
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            match_label = self.nlp.vocab.strings[match_id]
            
            if match_label == 'PAN':
                entities['custom_entities']['pan'].append(span.text)
            elif match_label == 'AADHAAR':
                entities['custom_entities']['aadhaar'].append(span.text)
        
        return entities
    
    def extract_name(self, text: str, context: str = None) -> Optional[str]:
        """
        Extract person name from text
        Args:
            text: Input text
            context: Optional context (e.g., 'pan', 'aadhaar') for better extraction
        """
        entities = self.extract_entities(text)
        
        if entities['persons']:
            # Return the first person name found
            return entities['persons'][0]['text']
        
        # Fallback: Use regex patterns
        # Pattern for Indian names (2-4 words, capitalized)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        names = re.findall(name_pattern, text)
        
        if names:
            # Filter out common non-name words
            common_words = {'Income', 'Tax', 'Department', 'Government', 'India', 'Permanent', 'Account', 'Number'}
            filtered_names = [name for name in names if not any(word in name for word in common_words)]
            
            if filtered_names:
                return filtered_names[0]
        
        return None
    
    def extract_date_of_birth(self, text: str) -> Optional[str]:
        """
        Extract date of birth from text
        Handles multiple date formats
        """
        # Common date patterns
        date_patterns = [
            r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b',  # DD-MM-YYYY or DD/MM/YYYY
            r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b',  # YYYY-MM-DD
            r'\b(\d{2}\s+[A-Za-z]+\s+\d{4})\b',  # DD Month YYYY
            r'\b([A-Za-z]+\s+\d{2},?\s+\d{4})\b'  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                
                # Parse and validate date
                try:
                    parsed_date = dateparser.parse(date_str)
                    if parsed_date:
                        # Check if it's a reasonable birth date (between 1920 and current year - 18)
                        current_year = datetime.now().year
                        if 1920 <= parsed_date.year <= current_year - 18:
                            return parsed_date.strftime('%Y-%m-%d')
                except:
                    continue
        
        # Use spaCy entities
        entities = self.extract_entities(text)
        if entities['dates']:
            for date_text in entities['dates']:
                try:
                    parsed_date = dateparser.parse(date_text)
                    if parsed_date and 1920 <= parsed_date.year <= datetime.now().year - 18:
                        return parsed_date.strftime('%Y-%m-%d')
                except:
                    continue
        
        return None
    
    def extract_address(self, text: str) -> Optional[str]:
        """
        Extract address from text
        """
        # Address usually contains locations and specific keywords
        address_keywords = [
            'address', 'residence', 'house', 'flat', 'street', 'road', 'avenue',
            'colony', 'nagar', 'society', 'apartment', 'building', 'pin', 'pincode'
        ]
        
        lines = text.split('\n')
        address_lines = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if line contains address keywords
            if any(keyword in line_lower for keyword in address_keywords):
                # Collect this line and next few lines
                start_idx = i
                end_idx = min(i + 4, len(lines))
                address_lines = lines[start_idx:end_idx]
                break
        
        if address_lines:
            # Clean and join address lines
            address = ' '.join([line.strip() for line in address_lines if line.strip()])
            
            # Remove address label if present
            address = re.sub(r'^(address|residence)[:\s]+', '', address, flags=re.IGNORECASE)
            
            return address
        
        # Fallback: Use spaCy to find locations
        entities = self.extract_entities(text)
        if entities['locations']:
            # Look for lines containing locations
            for location in entities['locations']:
                for line in lines:
                    if location in line:
                        # Find surrounding context
                        line_idx = lines.index(line)
                        context_lines = lines[max(0, line_idx-1):min(len(lines), line_idx+3)]
                        return ' '.join([l.strip() for l in context_lines if l.strip()])
        
        # Last resort: Look for PIN code pattern
        pin_pattern = r'\b\d{6}\b'
        for i, line in enumerate(lines):
            if re.search(pin_pattern, line):
                # Get 3 lines before PIN code
                start_idx = max(0, i - 2)
                address_lines = lines[start_idx:i+1]
                return ' '.join([l.strip() for l in address_lines if l.strip()])
        
        return None
    
    def extract_pan_number(self, text: str) -> Optional[str]:
        """
        Extract PAN number from text
        Format: ABCDE1234F
        """
        # Remove spaces and newlines for better matching
        clean_text = re.sub(r'\s+', '', text)
        
        # PAN pattern
        pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
        match = re.search(pan_pattern, text)
        
        if match:
            pan = match.group(0)
            
            # Validate PAN structure
            if self.validate_pan(pan):
                return pan
        
        # Also check in cleaned text
        match = re.search(pan_pattern, clean_text)
        if match:
            pan = match.group(0)
            if self.validate_pan(pan):
                return pan
        
        return None
    
    def extract_aadhaar_number(self, text: str) -> Optional[str]:
        """
        Extract Aadhaar number from text
        Format: 1234 5678 9012 or 123456789012
        """
        # Pattern with spaces
        aadhaar_pattern_spaced = r'\b\d{4}\s\d{4}\s\d{4}\b'
        match = re.search(aadhaar_pattern_spaced, text)
        
        if match:
            aadhaar = match.group(0)
            if self.validate_aadhaar(aadhaar.replace(' ', '')):
                return aadhaar
        
        # Pattern without spaces
        clean_text = re.sub(r'\s+', '', text)
        aadhaar_pattern_continuous = r'\b\d{12}\b'
        match = re.search(aadhaar_pattern_continuous, clean_text)
        
        if match:
            aadhaar = match.group(0)
            if self.validate_aadhaar(aadhaar):
                # Format with spaces
                return f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:]}"
        
        return None
    
    def validate_pan(self, pan: str) -> bool:
        """
        Validate PAN number structure
        """
        if len(pan) != 10:
            return False
        
        # Fourth character should be 'P' for individual
        # Fifth character is first letter of surname
        # Characters 1-5: Letters
        # Characters 6-9: Numbers
        # Character 10: Letter
        
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        return bool(re.match(pattern, pan))
    
    def validate_aadhaar(self, aadhaar: str) -> bool:
        """
        Validate Aadhaar number (basic validation)
        """
        # Remove spaces
        aadhaar = aadhaar.replace(' ', '')
        
        # Should be exactly 12 digits
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            return False
        
        # First digit should not be 0 or 1
        if aadhaar[0] in ['0', '1']:
            return False
        
        return True
    
    def extract_all_fields(self, text: str, doc_type: str = 'general') -> Dict:
        """
        Extract all relevant fields from text
        Args:
            text: Input text from OCR
            doc_type: Type of document (pan, aadhaar, passport, general)
        """
        result = {
            'name': self.extract_name(text, doc_type),
            'dob': self.extract_date_of_birth(text),
            'address': self.extract_address(text),
            'pan': self.extract_pan_number(text),
            'aadhaar': self.extract_aadhaar_number(text),
            'entities': self.extract_entities(text)
        }
        
        # Document-specific processing
        if doc_type == 'pan':
            result['document_type'] = 'PAN Card'
            result['primary_id'] = result['pan']
        elif doc_type == 'aadhaar':
            result['document_type'] = 'Aadhaar Card'
            result['primary_id'] = result['aadhaar']
        elif doc_type == 'passport':
            result['document_type'] = 'Passport'
            # Extract passport number
            passport_pattern = r'\b[A-Z]{1}\d{7}\b'
            match = re.search(passport_pattern, text)
            result['passport_number'] = match.group(0) if match else None
            result['primary_id'] = result['passport_number']
        
        # Calculate confidence score
        result['confidence_score'] = self._calculate_confidence(result)
        
        return result
    
    def _calculate_confidence(self, extracted_data: Dict) -> float:
        """
        Calculate confidence score based on extracted fields
        """
        score = 0.0
        total_fields = 0
        
        # Check essential fields
        fields_weights = {
            'name': 0.25,
            'dob': 0.20,
            'address': 0.15,
            'pan': 0.20,
            'aadhaar': 0.20
        }
        
        for field, weight in fields_weights.items():
            total_fields += weight
            if extracted_data.get(field):
                score += weight
        
        return score / total_fields if total_fields > 0 else 0.0
    
    def cross_validate_fields(self, ocr_data: Dict, form_data: Dict) -> Dict:
        """
        Cross-validate extracted data with user-provided form data
        """
        validation_results = {
            'matches': {},
            'mismatches': {},
            'missing_in_ocr': {},
            'overall_match_score': 0.0
        }
        
        fields_to_check = ['name', 'dob', 'address']
        matches = 0
        total_checks = 0
        
        for field in fields_to_check:
            if field in form_data and form_data[field]:
                total_checks += 1
                
                if field in ocr_data and ocr_data[field]:
                    # Simple similarity check
                    similarity = self._calculate_similarity(
                        str(form_data[field]).lower(),
                        str(ocr_data[field]).lower()
                    )
                    
                    if similarity > 0.8:
                        validation_results['matches'][field] = {
                            'form': form_data[field],
                            'ocr': ocr_data[field],
                            'similarity': similarity
                        }
                        matches += 1
                    else:
                        validation_results['mismatches'][field] = {
                            'form': form_data[field],
                            'ocr': ocr_data[field],
                            'similarity': similarity
                        }
                else:
                    validation_results['missing_in_ocr'][field] = form_data[field]
        
        validation_results['overall_match_score'] = matches / total_checks if total_checks > 0 else 0.0
        
        return validation_results
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using Levenshtein distance
        """
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()


# Utility function for combined OCR + NLP processing
def process_document_with_nlp(ocr_result: Dict, extractor: NLPEntityExtractor) -> Dict:
    """
    Process OCR result with NLP entity extraction
    """
    if ocr_result['status'] == 'error':
        return ocr_result
    
    # Extract entities from OCR text
    nlp_result = extractor.extract_all_fields(
        ocr_result['raw_text'],
        ocr_result.get('document_type', 'general')
    )
    
    # Merge OCR and NLP results
    combined_result = {
        **ocr_result,
        'nlp_extracted_fields': nlp_result,
        'final_extracted_data': {
            'name': nlp_result.get('name') or ocr_result.get('extracted_fields', {}).get('name'),
            'dob': nlp_result.get('dob') or ocr_result.get('extracted_fields', {}).get('dob'),
            'address': nlp_result.get('address') or ocr_result.get('extracted_fields', {}).get('address'),
            'pan': nlp_result.get('pan') or ocr_result.get('extracted_fields', {}).get('pan_number'),
            'aadhaar': nlp_result.get('aadhaar') or ocr_result.get('extracted_fields', {}).get('aadhaar_number'),
        },
        'confidence_score': nlp_result.get('confidence_score', 0.0)
    }
    
    return combined_result


if __name__ == "__main__":
    # Example usage
    extractor = NLPEntityExtractor()
    
    # Sample text from OCR
    sample_text = """
    INCOME TAX DEPARTMENT
    GOVT. OF INDIA
    Permanent Account Number Card
    
    ABCDE1234F
    
    Name: JOHN DOE
    Father's Name: ROBERT DOE
    Date of Birth: 15/06/1990
    """
    
    result = extractor.extract_all_fields(sample_text, 'pan')
    print("Extracted Fields:", result)