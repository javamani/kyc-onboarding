# main.py - Updated with Authentication
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Import OCR, NLP, and Validation modules
from ocr_processor import OCRProcessor
from nlp_extractor import NLPEntityExtractor, process_document_with_nlp
from validation_scorer import ValidationRiskScorer, format_validation_report

# Import Authentication module
from auth import (
    UserCreate, UserLogin, Token, UserResponse,
    create_access_token, authenticate_user, create_user,
    get_current_user, require_role, security
)

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "kyc_onboarding"

# Initialize FastAPI
app = FastAPI(title="KYC Onboarding API with Authentication")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
db_client = None
db = None

# OCR, NLP, and Validation Processors
ocr_processor = None
nlp_extractor = None
validation_scorer = None

@app.on_event("startup")
async def startup_db_client():
    global db_client, db, ocr_processor, nlp_extractor, validation_scorer
    db_client = AsyncIOMotorClient(MONGODB_URL)
    db = db_client[DATABASE_NAME]
    
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.kyc_cases.create_index("created_by")
    await db.kyc_cases.create_index("status")
    
    # Initialize OCR, NLP, and Validation processors
    ocr_processor = OCRProcessor(use_gpu=False, lang='en')
    nlp_extractor = NLPEntityExtractor(model_name='en_core_web_sm')
    validation_scorer = ValidationRiskScorer()
    
    print("✅ Database connected")
    print("✅ OCR Processor initialized")
    print("✅ NLP Extractor initialized")
    print("✅ Validation & Risk Scorer initialized")

@app.on_event("shutdown")
async def shutdown_db_client():
    db_client.close()

# Enums
class UserRole(str, Enum):
    MAKER = "MAKER"
    CHECKER = "CHECKER"

class CaseStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    AI_REVIEWED = "AI_REVIEWED"
    CHECKER_APPROVED = "CHECKER_APPROVED"
    CHECKER_REJECTED = "CHECKER_REJECTED"

class AuditAction(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    AI_REVIEWED = "AI_REVIEWED"
    CHECKER_APPROVED = "CHECKER_APPROVED"
    CHECKER_REJECTED = "CHECKER_REJECTED"
    UPDATED = "UPDATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    OCR_PROCESSED = "OCR_PROCESSED"

# Pydantic Models
class CaseCreateRequest(BaseModel):
    customer_name: str
    dob: str
    address: str
    email: Optional[str] = None
    phone: Optional[str] = None

class CaseActionRequest(BaseModel):
    comments: Optional[str] = None

# Helper Functions
def case_helper(case) -> dict:
    """Convert MongoDB document to dictionary"""
    return {
        "id": str(case["_id"]),
        "customer_name": case["customer_profile"]["name"],
        "dob": case["customer_profile"]["dob"],
        "address": case["customer_profile"]["address"],
        "email": case["customer_profile"].get("email"),
        "phone": case["customer_profile"].get("phone"),
        "status": case["status"],
        "created_by": case["created_by"],
        "created_by_name": case.get("created_by_name"),
        "created_at": case["created_at"].isoformat(),
        "updated_at": case["updated_at"].isoformat(),
        "reviewed_by": case.get("reviewed_by"),
        "reviewed_by_name": case.get("reviewed_by_name"),
        "documents": case.get("documents", {}),
        "ocr_results": case.get("ocr_results", {}),
        "validation_result": case.get("validation_result", {}),
        "risk_score": case.get("risk_score"),
        "risk_level": case.get("risk_level"),
        "ai_score": case.get("ai_score"),
        "data_match_score": case.get("data_match_score"),
        "audit_trail": [
            {
                "timestamp": audit["timestamp"].isoformat(),
                "action": audit["action"],
                "by": audit["by"],
                "role": audit.get("role", "UNKNOWN"),
                "comments": audit.get("comments")
            }
            for audit in case.get("audit_trail", [])
        ]
    }

async def run_ai_review(case_id: str):
    """Enhanced AI review with OCR validation and data matching"""
    import random
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        return
    
    ocr_results = case.get("ocr_results", {})
    base_score = random.randint(70, 85)
    
    data_match_score = case.get("data_match_score", 0)
    if data_match_score > 0.8:
        base_score += 10
    elif data_match_score > 0.6:
        base_score += 5
    
    ocr_confidence = 0
    ocr_count = 0
    for doc_type, ocr_data in ocr_results.items():
        if ocr_data and 'confidence_score' in ocr_data:
            ocr_confidence += ocr_data['confidence_score']
            ocr_count += 1
    
    if ocr_count > 0:
        avg_ocr_confidence = ocr_confidence / ocr_count
        if avg_ocr_confidence > 0.8:
            base_score += 5
    
    ai_score = min(base_score, 100)
    
    await db.kyc_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                "status": CaseStatus.AI_REVIEWED,
                "ai_score": ai_score,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "audit_trail": {
                    "timestamp": datetime.utcnow(),
                    "action": AuditAction.AI_REVIEWED,
                    "by": "AI System",
                    "role": "SYSTEM",
                    "comments": f"AI verification score: {ai_score}/100"
                }
            }
        }
    )

# Dependency to get current user with db
async def get_current_user_with_db(credentials = Depends(security)):
    """Get current user with database access"""
    from auth import decode_access_token
    
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"]
    }

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user"""
    created_user = await create_user(db, user_data)
    
    return UserResponse(
        id=str(created_user["_id"]),
        email=created_user["email"],
        full_name=created_user["full_name"],
        role=created_user["role"],
        created_at=created_user["created_at"].isoformat()
    )

@app.post("/api/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Login and get access token"""
    user = await authenticate_user(db, user_credentials.email, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=timedelta(hours=8)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            created_at=user["created_at"].isoformat()
        )
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user_with_db)):
    """Get current logged-in user"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        created_at=datetime.utcnow().isoformat()
    )

# ============================================================================
# CASE MANAGEMENT ENDPOINTS (Protected)
# ============================================================================

@app.post("/api/cases", status_code=status.HTTP_201_CREATED)
async def create_case(
    request: CaseCreateRequest,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Create a new KYC case (MAKER only)"""
    if current_user["role"] != "MAKER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only MAKER can create cases"
        )
    
    case_data = {
        "customer_profile": {
            "name": request.customer_name,
            "dob": request.dob,
            "address": request.address,
            "email": request.email,
            "phone": request.phone
        },
        "status": CaseStatus.DRAFT,
        "created_by": current_user["id"],
        "created_by_name": current_user["full_name"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "documents": {},
        "ocr_results": {},
        "validation_result": {},
        "risk_score": 0,
        "risk_level": "LOW",
        "data_match_score": 0.0,
        "audit_trail": [
            {
                "timestamp": datetime.utcnow(),
                "action": AuditAction.CREATED,
                "by": current_user["full_name"],
                "role": current_user["role"],
                "comments": "Case created"
            }
        ]
    }
    
    result = await db.kyc_cases.insert_one(case_data)
    created_case = await db.kyc_cases.find_one({"_id": result.inserted_id})
    
    return case_helper(created_case)

@app.get("/api/cases")
async def get_cases(
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Get all cases (filtered based on role)"""
    query = {}
    
    if status_filter:
        query["status"] = status_filter
    
    # MAKER can only see their own cases
    if current_user["role"] == "MAKER":
        query["created_by"] = current_user["id"]
    
    # CHECKER can see all submitted cases
    
    cases = await db.kyc_cases.find(query).sort("created_at", -1).to_list(100)
    return [case_helper(case) for case in cases]

@app.get("/api/cases/{case_id}")
async def get_case(
    case_id: str,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Get a specific case by ID"""
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # MAKER can only view their own cases
    if current_user["role"] == "MAKER" and case["created_by"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own cases"
        )
    
    return case_helper(case)

@app.post("/api/cases/{case_id}/upload")
async def upload_document(
    case_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Upload KYC document with automatic OCR and NLP processing"""
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Only case creator can upload documents
    if case["created_by"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload documents to your own cases"
        )
    
    if doc_type not in ["pan", "aadhaar", "passport"]:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    try:
        file_content = await file.read()
        
        # Validate document quality
        quality_check = ocr_processor.validate_document_quality(file_content)
        
        if not quality_check['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Document quality check failed: {quality_check['reason']}"
            )
        
        # Process document with OCR
        if doc_type == 'pan':
            ocr_result = ocr_processor.extract_pan_specific(file_content)
        elif doc_type == 'aadhaar':
            ocr_result = ocr_processor.extract_aadhaar_specific(file_content)
        elif doc_type == 'passport':
            ocr_result = ocr_processor.extract_passport_specific(file_content)
        
        # Process with NLP
        combined_result = process_document_with_nlp(ocr_result, nlp_extractor)
        
        # Cross-validate with form data
        form_data = {
            'customer_name': case['customer_profile']['name'],
            'dob': case['customer_profile']['dob'],
            'address': case['customer_profile']['address']
        }
        
        validation_result = nlp_extractor.cross_validate_fields(
            combined_result['nlp_extracted_fields'],
            form_data
        )
        
        # Get all OCR results
        all_ocr_results = case.get("ocr_results", {})
        all_ocr_results[doc_type] = {
            "raw_text": combined_result['raw_text'],
            "extracted_fields": combined_result.get('final_extracted_data', {}),
            "confidence_score": combined_result.get('confidence_score', 0.0),
            "quality_check": quality_check,
            "validation": validation_result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Perform comprehensive validation and risk scoring
        risk_assessment = validation_scorer.validate_and_score(
            form_data,
            all_ocr_results
        )
        
        # Update case
        update_data = {
            f"documents.{doc_type}": file.filename,
            f"ocr_results.{doc_type}": all_ocr_results[doc_type],
            "validation_result": risk_assessment,
            "risk_score": risk_assessment['risk_score'],
            "risk_level": risk_assessment['risk_level'],
            "data_match_score": validation_result['overall_match_score'],
            "updated_at": datetime.utcnow()
        }
        
        await db.kyc_cases.update_one(
            {"_id": ObjectId(case_id)},
            {
                "$set": update_data,
                "$push": {
                    "audit_trail": {
                        "timestamp": datetime.utcnow(),
                        "action": AuditAction.OCR_PROCESSED,
                        "by": current_user["full_name"],
                        "role": current_user["role"],
                        "comments": f"{doc_type.upper()} processed - Confidence: {combined_result.get('confidence_score', 0):.2%}, Risk: {risk_assessment['risk_level']}"
                    }
                }
            }
        )
        
        return {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "ocr_confidence": combined_result.get('confidence_score', 0.0),
            "data_match_score": validation_result['overall_match_score'],
            "extracted_fields": combined_result.get('final_extracted_data', {}),
            "validation": validation_result,
            "risk_assessment": {
                "risk_score": risk_assessment['risk_score'],
                "risk_level": risk_assessment['risk_level'],
                "is_valid": risk_assessment['is_valid'],
                "anomalies_count": len(risk_assessment['anomalies']),
                "recommendations": risk_assessment['recommendations']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/api/cases/{case_id}/submit")
async def submit_case(
    case_id: str,
    request: CaseActionRequest,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Submit a case for review (MAKER only)"""
    if current_user["role"] != "MAKER":
        raise HTTPException(status_code=403, detail="Only MAKER can submit cases")
    
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Can only submit your own cases")
    
    if case["status"] != CaseStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only submit DRAFT cases")
    
    await db.kyc_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                "status": CaseStatus.SUBMITTED,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "audit_trail": {
                    "timestamp": datetime.utcnow(),
                    "action": AuditAction.SUBMITTED,
                    "by": current_user["full_name"],
                    "role": current_user["role"],
                    "comments": request.comments or "Case submitted for review"
                }
            }
        }
    )
    
    await run_ai_review(case_id)
    
    updated_case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    return case_helper(updated_case)

@app.post("/api/cases/{case_id}/approve")
async def approve_case(
    case_id: str,
    request: CaseActionRequest,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Approve a case (CHECKER only)"""
    if current_user["role"] != "CHECKER":
        raise HTTPException(status_code=403, detail="Only CHECKER can approve cases")
    
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case["created_by"] == current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Cannot approve your own case - Segregation of duties violation"
        )
    
    if case["status"] not in [CaseStatus.SUBMITTED, CaseStatus.AI_REVIEWED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve case in {case['status']} status"
        )
    
    await db.kyc_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                "status": CaseStatus.CHECKER_APPROVED,
                "reviewed_by": current_user["id"],
                "reviewed_by_name": current_user["full_name"],
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "audit_trail": {
                    "timestamp": datetime.utcnow(),
                    "action": AuditAction.CHECKER_APPROVED,
                    "by": current_user["full_name"],
                    "role": current_user["role"],
                    "comments": request.comments or "Case approved"
                }
            }
        }
    )
    
    updated_case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    return case_helper(updated_case)

@app.post("/api/cases/{case_id}/reject")
async def reject_case(
    case_id: str,
    request: CaseActionRequest,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Reject a case (CHECKER only)"""
    if current_user["role"] != "CHECKER":
        raise HTTPException(status_code=403, detail="Only CHECKER can reject cases")
    
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case["created_by"] == current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Cannot reject your own case - Segregation of duties violation"
        )
    
    if case["status"] not in [CaseStatus.SUBMITTED, CaseStatus.AI_REVIEWED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject case in {case['status']} status"
        )
    
    await db.kyc_cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                "status": CaseStatus.CHECKER_REJECTED,
                "reviewed_by": current_user["id"],
                "reviewed_by_name": current_user["full_name"],
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "audit_trail": {
                    "timestamp": datetime.utcnow(),
                    "action": AuditAction.CHECKER_REJECTED,
                    "by": current_user["full_name"],
                    "role": current_user["role"],
                    "comments": request.comments or "Case rejected"
                }
            }
        }
    )
    
    updated_case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    return case_helper(updated_case)

@app.get("/api/audit/{case_id}")
async def get_audit_trail(
    case_id: str,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Get audit trail for a case"""
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {
        "case_id": case_id,
        "audit_trail": [
            {
                "timestamp": audit["timestamp"].isoformat(),
                "action": audit["action"],
                "by": audit["by"],
                "role": audit.get("role", "UNKNOWN"),
                "comments": audit.get("comments")
            }
            for audit in case.get("audit_trail", [])
        ]
    }

@app.get("/api/cases/{case_id}/validation")
async def get_validation_results(
    case_id: str,
    current_user: dict = Depends(get_current_user_with_db)
):
    """Get validation and risk assessment for a case"""
    if not ObjectId.is_valid(case_id):
        raise HTTPException(status_code=400, detail="Invalid case ID")
    
    case = await db.kyc_cases.find_one({"_id": ObjectId(case_id)})
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    validation_result = case.get("validation_result", {})
    
    return {
        "case_id": case_id,
        "validation_result": validation_result,
        "risk_score": case.get("risk_score", 0),
        "risk_level": case.get("risk_level", "UNKNOWN"),
        "is_valid": validation_result.get("is_valid", False),
        "report": format_validation_report(validation_result) if validation_result else "No validation data available"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)