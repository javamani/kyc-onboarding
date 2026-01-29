# validation_scorer.py - Validation & Risk Scoring Module
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re
from difflib import SequenceMatcher

class RiskLevel(str, Enum):
    """Risk levels for KYC assessment"""
    VERY_LOW = "VERY_LOW"      # 0-20
    LOW = "LOW"                 # 21-40
    MEDIUM = "MEDIUM"           # 41-60
    HIGH = "HIGH"               # 61-80
    VERY_HIGH = "VERY_HIGH"     # 81-100

class AnomalyType(str, Enum):
    """Types of anomalies detected"""
    MISSING_FIELD = "MISSING_FIELD"
    MISMATCH = "MISMATCH"
    INVALID_FORMAT = "INVALID_FORMAT"
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"
    AGE_INCONSISTENCY = "AGE_INCONSISTENCY"
    DOCUMENT_QUALITY = "DOCUMENT_QUALITY"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"

class ValidationRiskScorer:
    """
    Comprehensive validation and risk scoring for KYC onboarding
    """
    
    def __init__(self):
        # Risk scoring weights
        self.weights = {
            'data_match': 0.25,           # How well OCR matches form
            'document_quality': 0.15,      # Quality of uploaded documents
            'completeness': 0.20,          # All required fields present
            'consistency': 0.20,           # Internal consistency
            'format_validation': 0.10,     # Format correctness
            'anomaly_count': 0.10          # Number of anomalies
        }
        
        # Thresholds for risk assessment
        self.thresholds = {
            'min_data_match': 0.75,
            'min_ocr_confidence': 0.70,
            'max_age': 100,
            'min_age': 18,
            'max_anomalies': 3
        }
    
    def validate_and_score(
        self, 
        form_data: Dict, 
        ocr_results: Dict,
        case_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Main validation and scoring function
        
        Args:
            form_data: Data from onboarding form
            ocr_results: Results from OCR processing
            case_metadata: Additional case information
            
        Returns:
            Complete validation and risk assessment
        """
        # Initialize results
        validation_result = {
            'is_valid': True,
            'risk_score': 0,
            'risk_level': RiskLevel.LOW,
            'anomalies': [],
            'validations': {},
            'recommendations': [],
            'scores_breakdown': {}
        }
        
        # 1. Compare extracted fields with form data
        data_match_result = self._compare_extracted_fields(form_data, ocr_results)
        validation_result['validations']['data_match'] = data_match_result
        validation_result['scores_breakdown']['data_match'] = data_match_result['score']
        
        # 2. Check document quality
        quality_result = self._check_document_quality(ocr_results)
        validation_result['validations']['document_quality'] = quality_result
        validation_result['scores_breakdown']['document_quality'] = quality_result['score']
        
        # 3. Validate completeness
        completeness_result = self._validate_completeness(form_data, ocr_results)
        validation_result['validations']['completeness'] = completeness_result
        validation_result['scores_breakdown']['completeness'] = completeness_result['score']
        
        # 4. Check internal consistency
        consistency_result = self._check_consistency(form_data, ocr_results)
        validation_result['validations']['consistency'] = consistency_result
        validation_result['scores_breakdown']['consistency'] = consistency_result['score']
        
        # 5. Validate data formats
        format_result = self._validate_formats(form_data, ocr_results)
        validation_result['validations']['format_validation'] = format_result
        validation_result['scores_breakdown']['format_validation'] = format_result['score']
        
        # 6. Detect anomalies
        anomalies = self._detect_anomalies(form_data, ocr_results, validation_result)
        validation_result['anomalies'] = anomalies
        validation_result['scores_breakdown']['anomaly_count'] = self._score_anomalies(anomalies)
        
        # 7. Calculate overall risk score
        risk_score = self._calculate_risk_score(validation_result['scores_breakdown'])
        validation_result['risk_score'] = risk_score
        validation_result['risk_level'] = self._determine_risk_level(risk_score)
        
        # 8. Generate recommendations
        validation_result['recommendations'] = self._generate_recommendations(validation_result)
        
        # 9. Determine if validation passed
        validation_result['is_valid'] = self._is_validation_passed(validation_result)
        
        return validation_result
    
    def _compare_extracted_fields(self, form_data: Dict, ocr_results: Dict) -> Dict:
        """
        Compare OCR extracted fields with form data
        """
        result = {
            'score': 100,
            'matches': [],
            'mismatches': [],
            'missing_in_ocr': []
        }
        
        if not ocr_results:
            result['score'] = 0
            result['missing_in_ocr'] = ['All fields']
            return result
        
        # Fields to compare
        comparison_fields = {
            'name': 'customer_name',
            'dob': 'dob',
            'address': 'address'
        }
        
        total_fields = len(comparison_fields)
        matched_fields = 0
        
        for ocr_field, form_field in comparison_fields.items():
            form_value = form_data.get(form_field, '')
            
            # Get OCR value from any document
            ocr_value = None
            for doc_type, doc_data in ocr_results.items():
                if 'extracted_fields' in doc_data:
                    ocr_value = doc_data['extracted_fields'].get(ocr_field)
                    if ocr_value:
                        break
            
            if not ocr_value:
                result['missing_in_ocr'].append(ocr_field)
                continue
            
            # Calculate similarity
            similarity = self._calculate_similarity(str(form_value), str(ocr_value))
            
            if similarity >= 0.8:
                result['matches'].append({
                    'field': ocr_field,
                    'form_value': form_value,
                    'ocr_value': ocr_value,
                    'similarity': similarity
                })
                matched_fields += 1
            else:
                result['mismatches'].append({
                    'field': ocr_field,
                    'form_value': form_value,
                    'ocr_value': ocr_value,
                    'similarity': similarity
                })
        
        # Calculate score
        if total_fields > 0:
            result['score'] = int((matched_fields / total_fields) * 100)
        
        return result
    
    def _check_document_quality(self, ocr_results: Dict) -> Dict:
        """
        Check quality of uploaded documents
        """
        result = {
            'score': 100,
            'documents': {},
            'issues': []
        }
        
        if not ocr_results:
            result['score'] = 0
            result['issues'].append('No documents uploaded')
            return result
        
        total_confidence = 0
        doc_count = 0
        
        for doc_type, doc_data in ocr_results.items():
            doc_result = {
                'confidence': 0,
                'quality_check': None,
                'issues': []
            }
            
            # Check OCR confidence
            if 'confidence_score' in doc_data:
                confidence = doc_data['confidence_score']
                doc_result['confidence'] = confidence
                total_confidence += confidence
                doc_count += 1
                
                if confidence < self.thresholds['min_ocr_confidence']:
                    doc_result['issues'].append(f'Low OCR confidence: {confidence:.2%}')
            
            # Check quality validation
            if 'quality_check' in doc_data:
                quality = doc_data['quality_check']
                doc_result['quality_check'] = quality
                
                if not quality.get('valid', True):
                    doc_result['issues'].append(f"Quality issue: {quality.get('reason', 'Unknown')}")
            
            result['documents'][doc_type] = doc_result
            result['issues'].extend(doc_result['issues'])
        
        # Calculate overall quality score
        if doc_count > 0:
            avg_confidence = total_confidence / doc_count
            result['score'] = int(avg_confidence * 100)
        
        return result
    
    def _validate_completeness(self, form_data: Dict, ocr_results: Dict) -> Dict:
        """
        Check if all required fields are present
        """
        result = {
            'score': 100,
            'required_fields': [],
            'missing_fields': [],
            'empty_fields': []
        }
        
        # Required fields in form
        required_form_fields = ['customer_name', 'dob', 'address']
        
        for field in required_form_fields:
            result['required_fields'].append(field)
            
            if field not in form_data:
                result['missing_fields'].append(field)
            elif not form_data[field] or str(form_data[field]).strip() == '':
                result['empty_fields'].append(field)
        
        # Required documents
        required_docs = ['pan', 'aadhaar']
        
        for doc in required_docs:
            if doc not in ocr_results or not ocr_results[doc]:
                result['missing_fields'].append(f'{doc}_document')
        
        # Calculate score
        total_required = len(required_form_fields) + len(required_docs)
        missing_count = len(result['missing_fields']) + len(result['empty_fields'])
        
        if total_required > 0:
            result['score'] = int(((total_required - missing_count) / total_required) * 100)
        
        return result
    
    def _check_consistency(self, form_data: Dict, ocr_results: Dict) -> Dict:
        """
        Check internal consistency of data
        """
        result = {
            'score': 100,
            'consistent_fields': [],
            'inconsistencies': []
        }
        
        # Check age consistency
        dob = form_data.get('dob')
        if dob:
            age_check = self._validate_age(dob)
            if age_check['valid']:
                result['consistent_fields'].append('age')
            else:
                result['inconsistencies'].append({
                    'field': 'age',
                    'issue': age_check['reason']
                })
        
        # Check name consistency across documents
        if ocr_results:
            names = []
            for doc_type, doc_data in ocr_results.items():
                if 'extracted_fields' in doc_data and 'name' in doc_data['extracted_fields']:
                    names.append(doc_data['extracted_fields']['name'])
            
            if len(names) > 1:
                # Check if all names are similar
                base_name = names[0]
                for name in names[1:]:
                    similarity = self._calculate_similarity(base_name, name)
                    if similarity < 0.7:
                        result['inconsistencies'].append({
                            'field': 'name',
                            'issue': f'Name mismatch across documents: {base_name} vs {name}'
                        })
        
        # Check address format consistency
        address = form_data.get('address', '')
        if address and len(address) < 20:
            result['inconsistencies'].append({
                'field': 'address',
                'issue': 'Address too short (minimum 20 characters)'
            })
        
        # Calculate score
        total_checks = len(result['consistent_fields']) + len(result['inconsistencies'])
        if total_checks > 0:
            result['score'] = int((len(result['consistent_fields']) / total_checks) * 100)
        
        return result
    
    def _validate_formats(self, form_data: Dict, ocr_results: Dict) -> Dict:
        """
        Validate data format correctness
        """
        result = {
            'score': 100,
            'valid_formats': [],
            'invalid_formats': []
        }
        
        # Validate email format
        email = form_data.get('email')
        if email:
            if self._is_valid_email(email):
                result['valid_formats'].append('email')
            else:
                result['invalid_formats'].append({
                    'field': 'email',
                    'value': email,
                    'issue': 'Invalid email format'
                })
        
        # Validate phone format
        phone = form_data.get('phone')
        if phone:
            if self._is_valid_phone(phone):
                result['valid_formats'].append('phone')
            else:
                result['invalid_formats'].append({
                    'field': 'phone',
                    'value': phone,
                    'issue': 'Invalid phone format'
                })
        
        # Validate PAN format from OCR
        if ocr_results:
            for doc_type, doc_data in ocr_results.items():
                if 'extracted_fields' in doc_data:
                    pan = doc_data['extracted_fields'].get('pan')
                    if pan:
                        if self._is_valid_pan(pan):
                            result['valid_formats'].append('pan')
                        else:
                            result['invalid_formats'].append({
                                'field': 'pan',
                                'value': pan,
                                'issue': 'Invalid PAN format'
                            })
                        break
        
        # Validate Aadhaar format from OCR
        if ocr_results:
            for doc_type, doc_data in ocr_results.items():
                if 'extracted_fields' in doc_data:
                    aadhaar = doc_data['extracted_fields'].get('aadhaar')
                    if aadhaar:
                        if self._is_valid_aadhaar(aadhaar):
                            result['valid_formats'].append('aadhaar')
                        else:
                            result['invalid_formats'].append({
                                'field': 'aadhaar',
                                'value': aadhaar,
                                'issue': 'Invalid Aadhaar format'
                            })
                        break
        
        # Calculate score
        total_checks = len(result['valid_formats']) + len(result['invalid_formats'])
        if total_checks > 0:
            result['score'] = int((len(result['valid_formats']) / total_checks) * 100)
        
        return result
    
    def _detect_anomalies(
        self, 
        form_data: Dict, 
        ocr_results: Dict,
        validation_result: Dict
    ) -> List[Dict]:
        """
        Detect various types of anomalies
        """
        anomalies = []
        
        # 1. Missing fields anomalies
        completeness = validation_result['validations'].get('completeness', {})
        for field in completeness.get('missing_fields', []):
            anomalies.append({
                'type': AnomalyType.MISSING_FIELD,
                'field': field,
                'severity': 'high',
                'description': f'Required field "{field}" is missing'
            })
        
        # 2. Data mismatch anomalies
        data_match = validation_result['validations'].get('data_match', {})
        for mismatch in data_match.get('mismatches', []):
            severity = 'high' if mismatch['similarity'] < 0.5 else 'medium'
            anomalies.append({
                'type': AnomalyType.MISMATCH,
                'field': mismatch['field'],
                'severity': severity,
                'description': f"Mismatch: Form='{mismatch['form_value']}' vs OCR='{mismatch['ocr_value']}'",
                'similarity': mismatch['similarity']
            })
        
        # 3. Format validation anomalies
        format_val = validation_result['validations'].get('format_validation', {})
        for invalid in format_val.get('invalid_formats', []):
            anomalies.append({
                'type': AnomalyType.INVALID_FORMAT,
                'field': invalid['field'],
                'severity': 'medium',
                'description': invalid['issue']
            })
        
        # 4. Age consistency anomalies
        dob = form_data.get('dob')
        if dob:
            age_check = self._validate_age(dob)
            if not age_check['valid']:
                anomalies.append({
                    'type': AnomalyType.AGE_INCONSISTENCY,
                    'field': 'dob',
                    'severity': 'high',
                    'description': age_check['reason']
                })
        
        # 5. Document quality anomalies
        quality = validation_result['validations'].get('document_quality', {})
        for issue in quality.get('issues', []):
            anomalies.append({
                'type': AnomalyType.DOCUMENT_QUALITY,
                'field': 'document',
                'severity': 'medium',
                'description': issue
            })
        
        # 6. Suspicious patterns
        suspicious = self._detect_suspicious_patterns(form_data, ocr_results)
        anomalies.extend(suspicious)
        
        return anomalies
    
    def _detect_suspicious_patterns(self, form_data: Dict, ocr_results: Dict) -> List[Dict]:
        """
        Detect suspicious patterns in data
        """
        suspicious = []
        
        # Check for repeated characters in name
        name = form_data.get('customer_name', '')
        if name and self._has_repeated_pattern(name):
            suspicious.append({
                'type': AnomalyType.SUSPICIOUS_PATTERN,
                'field': 'customer_name',
                'severity': 'medium',
                'description': 'Name contains suspicious repeated patterns'
            })
        
        # Check for test/dummy data
        test_keywords = ['test', 'dummy', 'sample', 'xxx', 'example']
        for field, value in form_data.items():
            if isinstance(value, str):
                if any(keyword in value.lower() for keyword in test_keywords):
                    suspicious.append({
                        'type': AnomalyType.SUSPICIOUS_PATTERN,
                        'field': field,
                        'severity': 'high',
                        'description': f'Field contains test/dummy data: {value}'
                    })
        
        # Check for all caps or all lowercase names
        name = form_data.get('customer_name', '')
        if name and len(name) > 5:
            if name.isupper() or name.islower():
                # This is actually normal for OCR, so low severity
                pass
        
        return suspicious
    
    def _calculate_risk_score(self, scores_breakdown: Dict) -> int:
        """
        Calculate overall risk score (0-100, higher = more risky)
        """
        risk_score = 0
        
        for category, weight in self.weights.items():
            category_score = scores_breakdown.get(category, 0)
            # Invert score (100 - score) because higher validation score = lower risk
            risk_component = (100 - category_score) * weight
            risk_score += risk_component
        
        return int(risk_score)
    
    def _score_anomalies(self, anomalies: List[Dict]) -> int:
        """
        Convert anomaly count to a score (0-100)
        """
        if not anomalies:
            return 100
        
        # Weight anomalies by severity
        severity_weights = {
            'low': 5,
            'medium': 15,
            'high': 30
        }
        
        total_weight = sum(severity_weights.get(a.get('severity', 'medium'), 15) for a in anomalies)
        
        # Cap at 100
        score = max(0, 100 - total_weight)
        return score
    
    def _determine_risk_level(self, risk_score: int) -> RiskLevel:
        """
        Determine risk level based on score
        """
        if risk_score <= 20:
            return RiskLevel.VERY_LOW
        elif risk_score <= 40:
            return RiskLevel.LOW
        elif risk_score <= 60:
            return RiskLevel.MEDIUM
        elif risk_score <= 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _generate_recommendations(self, validation_result: Dict) -> List[str]:
        """
        Generate recommendations based on validation results
        """
        recommendations = []
        
        risk_level = validation_result['risk_level']
        anomalies = validation_result['anomalies']
        
        # Risk level recommendations
        if risk_level == RiskLevel.VERY_HIGH:
            recommendations.append('⛔ REJECT: Very high risk - Manual verification strongly recommended')
        elif risk_level == RiskLevel.HIGH:
            recommendations.append('⚠️ CAUTION: High risk - Thorough manual review required')
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append('⚡ REVIEW: Medium risk - Additional verification recommended')
        elif risk_level == RiskLevel.LOW:
            recommendations.append('✓ APPROVE: Low risk - Standard verification sufficient')
        else:
            recommendations.append('✓✓ APPROVE: Very low risk - Minimal verification needed')
        
        # Specific anomaly recommendations
        high_severity_count = sum(1 for a in anomalies if a.get('severity') == 'high')
        if high_severity_count > 0:
            recommendations.append(f'Address {high_severity_count} high-severity anomalies before approval')
        
        # Data match recommendations
        data_match = validation_result['validations'].get('data_match', {})
        if data_match.get('score', 100) < 80:
            recommendations.append('Re-upload documents with better quality for accurate OCR')
        
        # Completeness recommendations
        completeness = validation_result['validations'].get('completeness', {})
        missing = completeness.get('missing_fields', [])
        if missing:
            recommendations.append(f'Complete missing fields: {", ".join(missing)}')
        
        # Document quality recommendations
        quality = validation_result['validations'].get('document_quality', {})
        if quality.get('score', 100) < 70:
            recommendations.append('Request higher quality document scans')
        
        return recommendations
    
    def _is_validation_passed(self, validation_result: Dict) -> bool:
        """
        Determine if overall validation passed
        """
        risk_score = validation_result['risk_score']
        risk_level = validation_result['risk_level']
        anomalies = validation_result['anomalies']
        
        # High-severity anomalies = automatic fail
        high_severity = [a for a in anomalies if a.get('severity') == 'high']
        if len(high_severity) > self.thresholds['max_anomalies']:
            return False
        
        # Risk level check
        if risk_level in [RiskLevel.VERY_HIGH, RiskLevel.HIGH]:
            return False
        
        # Risk score check
        if risk_score > 70:
            return False
        
        # Completeness check
        completeness = validation_result['validations'].get('completeness', {})
        if completeness.get('score', 0) < 80:
            return False
        
        return True
    
    # Helper methods
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _validate_age(self, dob: str) -> Dict:
        """Validate age from date of birth"""
        try:
            if isinstance(dob, str):
                dob_date = datetime.strptime(dob, '%Y-%m-%d')
            else:
                dob_date = dob
            
            age = (datetime.now() - dob_date).days // 365
            
            if age < self.thresholds['min_age']:
                return {
                    'valid': False,
                    'age': age,
                    'reason': f'Age {age} is below minimum {self.thresholds["min_age"]}'
                }
            elif age > self.thresholds['max_age']:
                return {
                    'valid': False,
                    'age': age,
                    'reason': f'Age {age} exceeds maximum {self.thresholds["max_age"]}'
                }
            
            return {'valid': True, 'age': age}
        except:
            return {'valid': False, 'reason': 'Invalid date format'}
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone format"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        # Should be 10 digits (Indian) or 12 with country code
        return len(digits) in [10, 12]
    
    def _is_valid_pan(self, pan: str) -> bool:
        """Validate PAN format"""
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        return bool(re.match(pattern, pan))
    
    def _is_valid_aadhaar(self, aadhaar: str) -> bool:
        """Validate Aadhaar format"""
        digits = re.sub(r'\D', '', aadhaar)
        return len(digits) == 12 and not digits.startswith(('0', '1'))
    
    def _has_repeated_pattern(self, text: str) -> bool:
        """Check for suspicious repeated patterns"""
        # Check for 3+ repeated characters
        if re.search(r'(.)\1{2,}', text):
            return True
        # Check for repeated words
        words = text.lower().split()
        if len(words) != len(set(words)):
            return True
        return False


def format_validation_report(validation_result: Dict) -> str:
    """
    Format validation result as readable report
    """
    report = []
    report.append("=" * 60)
    report.append("KYC VALIDATION & RISK ASSESSMENT REPORT")
    report.append("=" * 60)
    report.append("")
    
    # Overall result
    status = "✓ PASSED" if validation_result['is_valid'] else "✗ FAILED"
    report.append(f"Overall Status: {status}")
    report.append(f"Risk Score: {validation_result['risk_score']}/100")
    report.append(f"Risk Level: {validation_result['risk_level']}")
    report.append("")
    
    # Scores breakdown
    report.append("Scores Breakdown:")
    report.append("-" * 60)
    for category, score in validation_result['scores_breakdown'].items():
        report.append(f"  {category.replace('_', ' ').title()}: {score}/100")
    report.append("")
    
    # Anomalies
    anomalies = validation_result['anomalies']
    report.append(f"Anomalies Detected: {len(anomalies)}")
    report.append("-" * 60)
    if anomalies:
        for i, anomaly in enumerate(anomalies, 1):
            report.append(f"{i}. [{anomaly['severity'].upper()}] {anomaly['type']}")
            report.append(f"   Field: {anomaly['field']}")
            report.append(f"   {anomaly['description']}")
            report.append("")
    else:
        report.append("  No anomalies detected")
        report.append("")
    
    # Recommendations
    report.append("Recommendations:")
    report.append("-" * 60)
    for i, rec in enumerate(validation_result['recommendations'], 1):
        report.append(f"{i}. {rec}")
    
    report.append("=" * 60)
    
    return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    scorer = ValidationRiskScorer()
    
    # Sample data
    form_data = {
        'customer_name': 'John Doe',
        'dob': '1990-06-15',
        'address': '123 Main Street, Mumbai, Maharashtra, 400001',
        'email': 'john.doe@example.com',
        'phone': '+919876543210'
    }
    
    ocr_results = {
        'pan': {
            'extracted_fields': {
                'name': 'JOHN DOE',
                'pan': 'ABCDE1234F',
                'dob': '15/06/1990'
            },
            'confidence_score': 0.89,
            'quality_check': {'valid': True}
        }
    }
    
    # Validate and score
    result = scorer.validate_and_score(form_data, ocr_results)
    
    # Print report
    print(format_validation_report(result))