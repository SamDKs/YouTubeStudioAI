CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE channels (
 channel_id TEXT PRIMARY KEY, name TEXT NOT NULL CHECK(length(trim(name))>0),
 description TEXT NOT NULL, category TEXT NOT NULL, primary_language TEXT NOT NULL,
 target_market TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE channel_storage (
 channel_id TEXT PRIMARY KEY REFERENCES channels(channel_id), color TEXT NOT NULL,
 record_reference TEXT NOT NULL UNIQUE, ordinal INTEGER NOT NULL UNIQUE,
 creation_token TEXT UNIQUE, record_hash TEXT
);
CREATE TABLE audit_events (
 audit_id TEXT PRIMARY KEY, channel_id TEXT REFERENCES channels(channel_id), entity_id TEXT NOT NULL,
 action TEXT NOT NULL, actor TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX audit_channel_time ON audit_events(channel_id,created_at);
CREATE TABLE ideas (
 idea_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(channel_id),
 source_reference_id TEXT, title TEXT NOT NULL CHECK(length(trim(title))>0), description TEXT NOT NULL,
 normalized_fingerprint TEXT NOT NULL, exact_fingerprint TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('candidate','researching','selected','script','archived')),
 origin TEXT NOT NULL CHECK(origin IN ('manual','markdown')), source_status TEXT,
 version INTEGER NOT NULL DEFAULT 1 CHECK(version>0), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(channel_id,source_reference_id), UNIQUE(channel_id,idea_id)
);
CREATE INDEX ideas_channel_status ON ideas(channel_id,status);
CREATE INDEX ideas_fingerprint ON ideas(channel_id,normalized_fingerprint);
CREATE INDEX ideas_exact ON ideas(channel_id,exact_fingerprint);
CREATE TABLE editorial_imports (
 channel_id TEXT NOT NULL REFERENCES channels(channel_id), source_reference_id TEXT NOT NULL,
 idea_id TEXT NOT NULL, source_snapshot TEXT NOT NULL, record_hash TEXT NOT NULL,
 applied_version INTEGER NOT NULL CHECK(applied_version>0), updated_at TEXT NOT NULL,
 PRIMARY KEY(channel_id,source_reference_id),
 FOREIGN KEY(channel_id,idea_id) REFERENCES ideas(channel_id,idea_id)
);
CREATE TABLE research_notes (
 research_id TEXT PRIMARY KEY, idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
 content TEXT NOT NULL CHECK(length(trim(content))>0), origin TEXT NOT NULL DEFAULT 'user', created_at TEXT NOT NULL
);
CREATE TABLE idea_sources (
 source_id TEXT PRIMARY KEY, idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
 reference TEXT NOT NULL CHECK(length(trim(reference))>0), title TEXT NOT NULL, publisher TEXT NOT NULL,
 source_type TEXT NOT NULL CHECK(source_type IN ('web','document','other')),
 provenance TEXT NOT NULL CHECK(provenance IN ('user','researched','pending')),
 retrieved_at TEXT, verification_status TEXT NOT NULL CHECK(verification_status IN ('pending','verified','rejected')),
 notes TEXT NOT NULL, created_at TEXT NOT NULL,
 CHECK(verification_status!='verified' OR length(trim(notes))>0)
);
CREATE TABLE idea_assessments (
 assessment_id TEXT PRIMARY KEY, idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
 methodology_version TEXT NOT NULL, score_total REAL CHECK(score_total IS NULL OR score_total BETWEEN 0 AND 5),
 rationale TEXT NOT NULL, evidence_summary TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE assessment_factors (
 assessment_id TEXT NOT NULL REFERENCES idea_assessments(assessment_id), factor_name TEXT NOT NULL,
 weight REAL NOT NULL CHECK(weight>0), score REAL CHECK(score IS NULL OR score BETWEEN 0 AND 5),
 rationale TEXT NOT NULL, PRIMARY KEY(assessment_id,factor_name)
);
CREATE INDEX sources_idea ON idea_sources(idea_id);
CREATE INDEX research_idea ON research_notes(idea_id,created_at);
CREATE INDEX assessment_idea ON idea_assessments(idea_id,created_at);
CREATE TABLE scripts (
 script_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(channel_id), idea_id TEXT NOT NULL,
 language TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('draft','in_review','approved')),
 current_version_id TEXT, version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(channel_id,script_id), UNIQUE(channel_id,idea_id,language),
 FOREIGN KEY(channel_id,idea_id) REFERENCES ideas(channel_id,idea_id),
 FOREIGN KEY(script_id,current_version_id) REFERENCES script_versions(script_id,script_version_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE script_versions (
 script_version_id TEXT PRIMARY KEY, script_id TEXT NOT NULL REFERENCES scripts(script_id),
 version_number INTEGER NOT NULL CHECK(version_number>0), content TEXT NOT NULL,
 content_hash TEXT NOT NULL, creation_origin TEXT NOT NULL, created_at TEXT NOT NULL,
 change_summary TEXT NOT NULL, UNIQUE(script_id,version_number), UNIQUE(script_id,script_version_id)
);
CREATE TABLE script_approvals (
 approval_id TEXT PRIMARY KEY, script_id TEXT NOT NULL, script_version_id TEXT NOT NULL,
 content_hash TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(script_version_id), FOREIGN KEY(script_id,script_version_id) REFERENCES script_versions(script_id,script_version_id)
);
CREATE INDEX scripts_channel ON scripts(channel_id,idea_id);
CREATE TRIGGER immutable_script_version_update BEFORE UPDATE ON script_versions BEGIN SELECT RAISE(ABORT,'immutable script version'); END;
CREATE TRIGGER immutable_script_version_delete BEFORE DELETE ON script_versions BEGIN SELECT RAISE(ABORT,'immutable script version'); END;
CREATE TRIGGER immutable_approval_update BEFORE UPDATE ON script_approvals BEGIN SELECT RAISE(ABORT,'immutable approval'); END;
CREATE TRIGGER immutable_approval_delete BEFORE DELETE ON script_approvals BEGIN SELECT RAISE(ABORT,'immutable approval'); END;
CREATE TRIGGER immutable_audit_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT,'immutable audit event'); END;
CREATE TRIGGER immutable_audit_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT,'immutable audit event'); END;
CREATE TABLE idea_revisions (
 idea_id TEXT NOT NULL REFERENCES ideas(idea_id), version INTEGER NOT NULL CHECK(version>0),
 snapshot TEXT NOT NULL, source_snapshot TEXT, created_at TEXT NOT NULL, PRIMARY KEY(idea_id,version)
);
CREATE TRIGGER immutable_idea_revision_update BEFORE UPDATE ON idea_revisions BEGIN SELECT RAISE(ABORT,'immutable idea revision'); END;
CREATE TRIGGER immutable_idea_revision_delete BEFORE DELETE ON idea_revisions BEGIN SELECT RAISE(ABORT,'immutable idea revision'); END;
