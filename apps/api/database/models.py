"""
SQLAlchemy Relational Models for NETRA-X Database
Enforces authoritative evidence ledger, UUIDv7 time-ordered PKs, and immutable audit chains.
"""

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), nullable=False, default="ANALYST")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    members = relationship("CaseMember", back_populates="case", cascade="all, delete-orphan")


class CaseMember(Base):
    __tablename__ = "case_members"

    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="ANALYST")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="members")
    user = relationship("User")


class Actor(Base):
    __tablename__ = "actors"

    id = Column(String(36), primary_key=True)
    primary_alias = Column(String(255), nullable=False, index=True)
    category = Column(String(100), default="Threat Actor", nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_synthetic = Column(Boolean, default=True, nullable=False)

    aliases = relationship("Alias", back_populates="actor", cascade="all, delete-orphan")
    pgp_keys = relationship("PGPKey", back_populates="actor")
    wallets = relationship("Wallet", back_populates="actor")


class Alias(Base):
    __tablename__ = "aliases"

    id = Column(String(36), primary_key=True)
    actor_id = Column(String(36), ForeignKey("actors.id"), nullable=False, index=True)
    value = Column(String(255), nullable=False, index=True)
    platform = Column(String(100), nullable=True)
    source = Column(String(255), nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("Actor", back_populates="aliases")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True)
    actor_id = Column(String(36), ForeignKey("actors.id"), nullable=True, index=True)
    platform = Column(String(100), nullable=False)
    handle = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PGPKey(Base):
    __tablename__ = "pgp_keys"

    id = Column(String(36), primary_key=True)
    fingerprint = Column(String(255), unique=True, nullable=False, index=True)
    key_id = Column(String(100), nullable=False)
    actor_id = Column(String(36), ForeignKey("actors.id"), nullable=True, index=True)
    key_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("Actor", back_populates="pgp_keys")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    chain = Column(String(50), default="BTC", nullable=False)
    cluster_id = Column(String(255), nullable=True)
    actor_id = Column(String(36), ForeignKey("actors.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("Actor", back_populates="wallets")


class OnionService(Base):
    __tablename__ = "onion_services"

    id = Column(String(36), primary_key=True)
    onion_address = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    favicon_mmh3 = Column(Integer, nullable=True, index=True)
    tls_cert_fingerprint = Column(String(255), nullable=True, index=True)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class Server(Base):
    __tablename__ = "servers"

    id = Column(String(36), primary_key=True)
    ip_address = Column(String(100), unique=True, nullable=False, index=True)
    asn = Column(String(100), nullable=True)
    provider = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True)
    sha256 = Column(String(64), unique=True, nullable=False, index=True)
    storage_uri = Column(String(512), nullable=False)
    content_type = Column(String(100), default="text/plain", nullable=False)
    size = Column(Integer, nullable=False)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True)
    artifact_id = Column(String(36), ForeignKey("artifacts.id"), nullable=False, index=True)
    source_uri = Column(String(512), nullable=False)
    collector_version = Column(String(50), nullable=False)
    extraction_method = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    dependence_group = Column(String(255), nullable=False, index=True)
    is_immutable = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    artifact = relationship("Artifact")


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id = Column(String(36), primary_key=True)
    subject_entity_id = Column(String(36), nullable=False, index=True)
    object_entity_id = Column(String(36), nullable=False, index=True)
    raw_log_lr = Column(Float, nullable=False, default=0.0)
    calibrated_prob = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), default="PROPOSED", nullable=False, index=True)  # PROPOSED, ACCEPTED, REJECTED, INSUFFICIENT
    model_version = Column(String(50), default="v1.0-LLR", nullable=False)
    calibration_version = Column(String(50), default="v1.0-Isotonic", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    reviewer = relationship("User")
    evidence_items = relationship("HypothesisEvidence", back_populates="hypothesis", cascade="all, delete-orphan")


class HypothesisEvidence(Base):
    __tablename__ = "hypothesis_evidence"

    id = Column(String(36), primary_key=True)
    hypothesis_id = Column(String(36), ForeignKey("hypotheses.id"), nullable=False, index=True)
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=False, index=True)
    family = Column(String(100), nullable=False)
    reliability_weight = Column(Float, default=1.0, nullable=False)
    raw_llr = Column(Float, nullable=False, default=0.0)
    contribution = Column(Float, nullable=False, default=0.0)
    is_contradiction = Column(Boolean, default=False, nullable=False)

    hypothesis = relationship("Hypothesis", back_populates="evidence_items")
    evidence = relationship("Evidence")


class AnalystReview(Base):
    __tablename__ = "analyst_reviews"

    id = Column(String(36), primary_key=True)
    hypothesis_id = Column(String(36), ForeignKey("hypotheses.id"), nullable=False, index=True)
    decision = Column(String(50), nullable=False)  # ACCEPT, REJECT, INSUFFICIENT
    notes = Column(Text, nullable=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    actor_user_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(36), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(100), nullable=False)  # PASSIVE_ONION, FORUM_CRAWL, HONEYPOT, SYNTHETIC
    lawful_basis = Column(String(100), nullable=False)  # passive_osint, synthetic_seed, honeypot
    base_uri = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False, index=True)
    raw_content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    observed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = Column(Text, nullable=True)

