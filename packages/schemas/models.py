"""
Shared Pydantic Schemas for NETRA-X Platform
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RoleName(str, Enum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"
    ANALYST = "ANALYST"
    RESEARCHER = "RESEARCHER"
    VIEWER = "VIEWER"


class CaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    CLOSED = "CLOSED"


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INSUFFICIENT = "INSUFFICIENT"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class DecisionEnum(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    INSUFFICIENT = "INSUFFICIENT"


class EvidenceFamily(str, Enum):
    EXACT_IDENTITY = "Exact Identity"
    FINANCIAL = "Financial"
    INFRASTRUCTURE = "Infrastructure"
    CONTENT_NLP = "Content / NLP"
    STYLOMETRY = "Stylometry"
    TEMPORAL = "Temporal"
    SEMANTIC_HANDLE = "Semantic / Handle"


# User & Auth
class UserBase(BaseModel):
    email: str
    mfa_enabled: bool = False


class UserCreate(UserBase):
    password: str
    role: RoleName = RoleName.ANALYST


class UserResponse(UserBase):
    id: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: str
    password: str


# Case
class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    member_count: int = 1


# Entity Schemas
class AliasSchema(BaseModel):
    id: str
    actor_id: str
    value: str
    platform: Optional[str] = None
    source: str
    confidence: float


class PGPKeySchema(BaseModel):
    id: str
    fingerprint: str
    key_id: str
    actor_id: Optional[str]
    key_body: Optional[str]
    created_at: datetime


class WalletSchema(BaseModel):
    id: str
    address: str
    chain: str
    cluster_id: Optional[str]
    actor_id: Optional[str]


class OnionServiceSchema(BaseModel):
    id: str
    onion_address: str
    title: Optional[str]
    favicon_mmh3: Optional[int]
    tls_cert_fingerprint: Optional[str]
    first_seen: datetime
    last_seen: datetime


class ServerSchema(BaseModel):
    id: str
    ip_address: str
    asn: Optional[str]
    provider: Optional[str]


class ActorSchema(BaseModel):
    id: str
    primary_alias: str
    category: str
    confidence: float
    last_seen: datetime
    is_synthetic: bool = True
    aliases: List[AliasSchema] = []
    pgp_keys: List[PGPKeySchema] = []
    wallets: List[WalletSchema] = []
    onion_services: List[OnionServiceSchema] = []


# Evidence & Provenance
class EvidenceSchema(BaseModel):
    id: str
    artifact_id: str
    source_uri: str
    collector_version: str
    extraction_method: str
    value: str
    confidence: float
    dependence_group: str
    is_immutable: bool = True
    created_at: datetime
    sha256: Optional[str] = None


class EvidenceWaterfallItem(BaseModel):
    evidence_id: str
    family: str
    source_uri: str
    extraction_method: str
    value: str
    reliability: float
    raw_llr: float
    contribution: float
    is_contradiction: bool
    dependence_group: str
    timestamp: datetime
    sha256: str


# Hypothesis & Attribution
class HypothesisSchema(BaseModel):
    id: str
    subject_entity_id: str
    subject_label: str
    object_entity_id: str
    object_label: str
    raw_log_lr: float
    calibrated_prob: float
    confidence_tier: str
    status: HypothesisStatus
    model_version: str
    calibration_version: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    reviewer_email: Optional[str] = None
    supporting_evidence: List[EvidenceWaterfallItem] = []
    contradictions: List[EvidenceWaterfallItem] = []
    family_breakdown: Dict[str, float] = {}


class ReviewRequest(BaseModel):
    decision: DecisionEnum
    notes: Optional[str] = None


# Audit Log
class AuditLogSchema(BaseModel):
    id: str
    actor_user_id: str
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    payload_hash: str
    prev_hash: str
    created_at: datetime


# Search
class SearchResultItem(BaseModel):
    entity_id: str
    entity_type: str
    title: str
    snippet: str
    source_uri: str
    confidence: float
    provenance_hash: str


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    results: List[SearchResultItem]


# Ingestion
#
# `lawful_basis` is a closed enum rather than a free string on purpose. The
# column is NOT NULL in the ledger because collection legality is a property of
# every observation, not an annotation someone may forget -- so the API refuses
# to record an observation that cannot state its basis.
class LawfulBasis(str, Enum):
    PASSIVE_OSINT = "passive_osint"
    SYNTHETIC_SEED = "synthetic_seed"
    HONEYPOT = "honeypot"


class SourceType(str, Enum):
    PASSIVE_ONION = "PASSIVE_ONION"
    FORUM_CRAWL = "FORUM_CRAWL"
    HONEYPOT = "HONEYPOT"
    SYNTHETIC = "SYNTHETIC"


class IngestRequest(BaseModel):
    raw_content: str = Field(..., min_length=1, max_length=200_000)
    source_name: str = Field(..., min_length=1, max_length=255)
    source_type: SourceType = SourceType.FORUM_CRAWL
    lawful_basis: LawfulBasis = LawfulBasis.PASSIVE_OSINT
    source_uri: Optional[str] = Field(default=None, max_length=512)


class ExtractedEvidence(BaseModel):
    id: str
    kind: str
    value: str
    dependence_group: str
    confidence: float


class IngestResponse(BaseModel):
    observation_id: str
    artifact_sha256: str
    source_id: str
    lawful_basis: str
    duplicate: bool
    extracted_count: int
    xmr_abstain: bool
    evidence: List[ExtractedEvidence]
