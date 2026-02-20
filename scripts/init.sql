-- Creator Onboarding Database Initialization
-- This script runs automatically when the PostgreSQL container starts for the first time.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Creator evaluations table
CREATE TABLE IF NOT EXISTS creator_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform VARCHAR(50) NOT NULL,
    handle VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    grade VARCHAR(2),
    score DECIMAL(5,2),
    decision VARCHAR(50),
    raw_profile JSONB,
    score_breakdown JSONB,
    tags TEXT[],
    risks TEXT[],
    report TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Creator history snapshots
CREATE TABLE IF NOT EXISTS creator_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    handle VARCHAR(255) NOT NULL,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    posts INTEGER DEFAULT 0,
    avg_likes INTEGER DEFAULT 0,
    avg_comments INTEGER DEFAULT 0,
    engagement_rate DECIMAL(8,4) DEFAULT 0,
    grade VARCHAR(2),
    score DECIMAL(5,2),
    decision VARCHAR(50),
    tags TEXT[],
    risks TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    username VARCHAR(255),
    role VARCHAR(50),
    action VARCHAR(255) NOT NULL,
    severity VARCHAR(50) DEFAULT 'info',
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_creator_evaluations_handle ON creator_evaluations(platform, handle);
CREATE INDEX IF NOT EXISTS idx_creator_snapshots_creator ON creator_snapshots(creator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action, created_at DESC);
