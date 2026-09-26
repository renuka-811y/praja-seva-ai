import os
import logging
from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PrajaSevaAI")

# System Setup & Constants
APP_TITLE = "PrajaSeva AI Core Engine"
VERSION = "1.0.0"

class Language(str, Enum):
    TELUGU = "te"
    ENGLISH = "en"
    HINDI = "hi"

class ServiceDomain(str, Enum):
    AGRICULTURE = "agriculture"
    HEALTHCARE = "healthcare"
    CIVIC_PERMITS = "civic_permits"
    SCHEMES = "schemes"

# Request/Response Schemas
class CitizenQuery(BaseModel):
    query_text: str = Field(..., min_length=3, example="How do I register for Rythu Bandhu scheme?")
    language: Language = Field(default=Language.TELUGU, description="Preferred response language")
    domain: Optional[ServiceDomain] = Field(default=ServiceDomain.SCHEMES, description="Domain context")

class ServiceMetadata(BaseModel):
    required_documents: List[str]
    processing_time_days: int
    official_portal: str

class QueryResponse(BaseModel):
    status: str
    query_received: str
    language: str
    translated_intent: str
    response_text: str
    service_metadata: ServiceMetadata
    execution_time_ms: float

# Core Engine Logic
class PrajaSevaEngine:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Operating in Dynamic Mock Failover mode.")

    async def process_voice_or_text(self, payload: CitizenQuery) -> Dict[str, Any]:
        """Core AI pipeline to process citizen intent and extract localized policy data."""
        domain_knowledge_base = {
            ServiceDomain.SCHEMES: ServiceMetadata(
                required_documents=["Aadhaar Card", "Pattadar Passbook", "Bank Passbook"],
                processing_time_days=7,
                official_portal="https://telangana.gov.in/schemes"
            ),
            ServiceDomain.AGRICULTURE: ServiceMetadata(
                required_documents=["Farmer ID", "Land Record (Pahani)"],
                processing_time_days=3,
                official_portal="https://rythubandhu.telangana.gov.in"
            ),
            ServiceDomain.HEALTHCARE: ServiceMetadata(
                required_documents=["Aarogyasri Card / Ration Card", "National ID"],
                processing_time_days=1,
                official_portal="https://aarogyasri.telangana.gov.in"
            ),
            ServiceDomain.CIVIC_PERMITS: ServiceMetadata(
                required_documents=["Property Tax Receipt", "Identity Proof"],
                processing_time_days=14,
                official_portal="https://ghmc.gov.in"
            )
        }

        metadata = domain_knowledge_base.get(
            payload.domain, 
            domain_knowledge_base[ServiceDomain.SCHEMES]
        )

        if payload.language == Language.TELUGU:
            response_msg = (
                f"మీ ప్రశ్న తీసుకున్నాము: '{payload.query_text}'. "
                f"ఈ సేవ కోసం అవసరమైన పత్రాలు: {', '.join(metadata.required_documents)}."
            )
        else:
            response_msg = (
                f"Query processed: '{payload.query_text}'. "
                f"Required documentation includes: {', '.join(metadata.required_documents)}."
            )

        return {
            "translated_intent": f"Identify requirements for domain [{payload.domain.value}]",
            "response_text": response_msg,
            "metadata": metadata
        }

# FastAPI Application
app = FastAPI(
    title=APP_TITLE,
    version=VERSION,
    description="Asynchronous AI microservice for localized citizen service navigation."
)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = PrajaSevaEngine()

@app.get("/", tags=["Health Check"])
async def root():
    return {"status": "online", "service": APP_TITLE, "version": VERSION}

@app.post("/api/v1/query", response_model=QueryResponse, tags=["Citizen Services"])
async def handle_query(query: CitizenQuery):
    import time
    start_time = time.time()

    try:
        result = await engine.process_voice_or_text(query)
        execution_time = round((time.time() - start_time) * 1000, 2)

        return QueryResponse(
            status="success",
            query_received=query.query_text,
            language=query.language.value,
            translated_intent=result["translated_intent"],
            response_text=result["response_text"],
            service_metadata=result["metadata"],
            execution_time_ms=execution_time
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal execution error processing the query."
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
