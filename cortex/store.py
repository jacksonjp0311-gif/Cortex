from __future__ import annotations

import json
import math
import sqlite3
import time
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any

from .embeddings import VECTOR_MAGIC, deserialize_vector, vector_bucket, vector_to_bytes

VECTOR_BUCKET_MODEL = "random-hyperplane-v1"
ACTIVATION_CONFORMANCE_LEDGER_SCHEMA = "cortex-activation-conformance-ledger/1.0"
ACTIVATION_CONFORMANCE_ZERO_HASH = "0" * 64
ACTIVATION_CONFORMANCE_ADMISSION_SCHEMA = (
    "cortex-activation-conformance-ledger-admission/1.0"
)
ACTIVATION_CONFORMANCE_PARTITION_FIELDS = (
    "repository_id",
    "operator_id",
    "body_epoch_id",
    "measurement_cohort_id",
    "coordinate_schema_digest",
)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS repositories(
    name TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    path TEXT NOT NULL,
    attached_at REAL NOT NULL,
    last_indexed REAL,
    last_bootstrap REAL,
    manifest_hash TEXT,
    bootstrap_status TEXT NOT NULL DEFAULT 'uninitialized',
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS files(
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    language TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    authoritative INTEGER NOT NULL DEFAULT 0,
    indexed_at REAL NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY(repo, path),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_files_repo_kind ON files(repo, kind);
CREATE INDEX IF NOT EXISTS idx_files_repo_status ON files(repo, status);

CREATE TABLE IF NOT EXISTS memories(
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    vector TEXT,
    embedding_model TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(repo, path, chunk_index, content_hash),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mem_repo_path ON memories(repo, path);
CREATE INDEX IF NOT EXISTS idx_mem_repo_kind ON memories(repo, kind);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    text, path, kind, content='memories', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, text, path, kind)
    VALUES(new.id, new.text, new.path, new.kind);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text, path, kind)
    VALUES('delete', old.id, old.text, old.path, old.kind);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text, path, kind)
    VALUES('delete', old.id, old.text, old.path, old.kind);
    INSERT INTO memories_fts(rowid, text, path, kind)
    VALUES(new.id, new.text, new.path, new.kind);
END;

CREATE TABLE IF NOT EXISTS memory_vector_buckets(
    memory_id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    bucket INTEGER NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_vector_buckets_repo_bucket
ON memory_vector_buckets(repo, bucket);

CREATE TABLE IF NOT EXISTS edges(
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    UNIQUE(repo, source, target, relation, evidence),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_edges_repo_source ON edges(repo, source);
CREATE INDEX IF NOT EXISTS idx_edges_repo_target ON edges(repo, target);
CREATE INDEX IF NOT EXISTS idx_edges_repo_relation ON edges(repo, relation);

CREATE TABLE IF NOT EXISTS symbols(
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_kind TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    signature TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    UNIQUE(repo, path, qualified_name, start_line),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_symbols_repo_name ON symbols(repo, name);
CREATE INDEX IF NOT EXISTS idx_symbols_repo_path ON symbols(repo, path);

CREATE TABLE IF NOT EXISTS git_commits(
    repo TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    authored_at REAL,
    author TEXT,
    subject TEXT,
    files TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY(repo, commit_hash),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS file_telemetry(
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    commit_count INTEGER NOT NULL DEFAULT 0,
    additions INTEGER NOT NULL DEFAULT 0,
    deletions INTEGER NOT NULL DEFAULT 0,
    last_changed REAL,
    cochange_degree INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY(repo, path),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions(
    session_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    task TEXT NOT NULL,
    started_at REAL NOT NULL,
    ended_at REAL,
    status TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    repo TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_repo_session ON events(repo, session_id);

CREATE TABLE IF NOT EXISTS bootstrap_runs(
    run_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at REAL NOT NULL,
    completed_at REAL,
    manifest_hash TEXT,
    certificate TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS environment_profiles(
    repo TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    profile_hash TEXT NOT NULL,
    observed_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS neural_nodes(
    repo TEXT NOT NULL,
    node_id TEXT NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    threshold REAL NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    updated_at REAL NOT NULL,
    PRIMARY KEY(repo, node_id),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_neural_nodes_repo_path ON neural_nodes(repo, path);

CREATE TABLE IF NOT EXISTS neural_synapses(
    repo TEXT NOT NULL,
    synapse_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    base_weight REAL NOT NULL,
    weight REAL NOT NULL,
    minimum_weight REAL NOT NULL,
    maximum_weight REAL NOT NULL,
    plasticity_rule TEXT NOT NULL,
    update_count INTEGER NOT NULL DEFAULT 0,
    evidence TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    updated_at REAL NOT NULL,
    PRIMARY KEY(repo, synapse_id),
    UNIQUE(repo, source_id, target_id, relation),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_neural_synapses_repo_source ON neural_synapses(repo, source_id);
CREATE INDEX IF NOT EXISTS idx_neural_synapses_repo_target ON neural_synapses(repo, target_id);

CREATE TABLE IF NOT EXISTS neural_ledger(
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL,
    previous_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    UNIQUE(repo, sequence),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_neural_ledger_repo_sequence ON neural_ledger(repo, sequence);

CREATE TABLE IF NOT EXISTS neural_activations(
    activation_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    session_id TEXT,
    task_hash TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_neural_activations_repo_created ON neural_activations(repo, created_at);

CREATE TABLE IF NOT EXISTS task_outcomes(
    outcome_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    session_id TEXT,
    activation_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reward REAL NOT NULL,
    verification_type TEXT NOT NULL,
    verification_payload_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE,
    FOREIGN KEY(activation_id) REFERENCES neural_activations(activation_id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_task_outcomes_repo_created ON task_outcomes(repo, created_at);

-- v8.2 typed informational interlocks.  This is a bounded observation ledger,
-- not a second memory substrate: activations remain the source of route truth
-- and task_outcomes remain the source of verified outcome truth.
CREATE TABLE IF NOT EXISTS information_interlock_observations(
    observation_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    activation_id TEXT NOT NULL,
    session_id TEXT,
    body_epoch_id TEXT NOT NULL,
    task_family TEXT NOT NULL,
    evidence_paths_json TEXT NOT NULL DEFAULT '[]',
    learned_paths_json TEXT NOT NULL DEFAULT '[]',
    u_before REAL,
    u_after REAL,
    delta_u REAL,
    constitutional_valid INTEGER NOT NULL DEFAULT 0,
    outcome_id TEXT,
    outcome_status TEXT,
    reward REAL,
    witness_valid INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    resolved_at REAL,
    receipt_hash TEXT NOT NULL,
    resolution_receipt_hash TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(repo, activation_id),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE,
    FOREIGN KEY(activation_id) REFERENCES neural_activations(activation_id) ON DELETE CASCADE,
    FOREIGN KEY(outcome_id) REFERENCES task_outcomes(outcome_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_info_interlock_repo_created
ON information_interlock_observations(repo, created_at);
CREATE INDEX IF NOT EXISTS idx_info_interlock_repo_epoch
ON information_interlock_observations(repo, body_epoch_id, created_at);
CREATE INDEX IF NOT EXISTS idx_info_interlock_repo_task
ON information_interlock_observations(repo, task_family, created_at);

-- v8.3.3 canonical activation-conformance evidence.  Scientific receipt
-- content is hashed independently from its append-only ledger envelope so a
-- receipt can be verified without a circular self-hash.  The partition tip is
-- updated in the same BEGIN IMMEDIATE transaction as every canonical append.
CREATE TABLE IF NOT EXISTS activation_conformance_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    subject_receipt_hash TEXT NOT NULL CHECK(length(subject_receipt_hash) = 64),
    previous_receipt_hash TEXT NOT NULL CHECK(length(previous_receipt_hash) = 64),
    chain_sequence INTEGER NOT NULL CHECK(chain_sequence >= 1),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    comparison_arm TEXT NOT NULL,
    body_epoch_id TEXT NOT NULL,
    measurement_cohort_id TEXT NOT NULL,
    coordinate_schema_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, operator_id, event_id),
    UNIQUE(
        repository_id,
        operator_id,
        body_epoch_id,
        measurement_cohort_id,
        coordinate_schema_digest,
        chain_sequence
    )
);
CREATE INDEX IF NOT EXISTS idx_activation_conformance_repo_created
ON activation_conformance_receipts(repo, created_at DESC, receipt_hash);
CREATE INDEX IF NOT EXISTS idx_activation_conformance_partition
ON activation_conformance_receipts(
    repository_id,
    operator_id,
    body_epoch_id,
    measurement_cohort_id,
    coordinate_schema_digest,
    chain_sequence
);
CREATE INDEX IF NOT EXISTS idx_activation_conformance_cases
ON activation_conformance_receipts(
    repo,
    operator_id,
    case_id,
    comparison_arm,
    created_at DESC
);

CREATE TABLE IF NOT EXISTS activation_conformance_chain_tips(
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    body_epoch_id TEXT NOT NULL,
    measurement_cohort_id TEXT NOT NULL,
    coordinate_schema_digest TEXT NOT NULL,
    tip_receipt_hash TEXT NOT NULL,
    receipt_count INTEGER NOT NULL CHECK(receipt_count >= 1),
    updated_at REAL NOT NULL,
    PRIMARY KEY(
        repository_id,
        operator_id,
        body_epoch_id,
        measurement_cohort_id,
        coordinate_schema_digest
    ),
    FOREIGN KEY(tip_receipt_hash)
        REFERENCES activation_conformance_receipts(receipt_hash) ON DELETE RESTRICT
);

CREATE TRIGGER IF NOT EXISTS activation_conformance_receipts_no_delete
BEFORE DELETE ON activation_conformance_receipts
BEGIN
    SELECT RAISE(ABORT, 'canonical activation conformance receipts cannot be deleted');
END;

-- Migrate the narrower v8.3.3 development trigger in place.  Canonical rows
-- are immutable in full; append advances only the separate chain-tip row.
DROP TRIGGER IF EXISTS activation_conformance_receipt_identity_immutable;
DROP TRIGGER IF EXISTS activation_conformance_receipts_no_update;
CREATE TRIGGER activation_conformance_receipts_no_update
BEFORE UPDATE ON activation_conformance_receipts
BEGIN
    SELECT RAISE(ABORT, 'canonical activation conformance receipts cannot be updated');
END;

-- A tip advances, but its partition identity never changes.  In particular,
-- the human-facing repository name remains bound to the repository identity
-- used by the canonical receipt chain.
DROP TRIGGER IF EXISTS activation_conformance_chain_tip_identity_immutable;
CREATE TRIGGER activation_conformance_chain_tip_identity_immutable
BEFORE UPDATE OF
    repository_id,
    repo,
    operator_id,
    body_epoch_id,
    measurement_cohort_id,
    coordinate_schema_digest
ON activation_conformance_chain_tips
WHEN OLD.repository_id IS NOT NEW.repository_id
  OR OLD.repo IS NOT NEW.repo
  OR OLD.operator_id IS NOT NEW.operator_id
  OR OLD.body_epoch_id IS NOT NEW.body_epoch_id
  OR OLD.measurement_cohort_id IS NOT NEW.measurement_cohort_id
  OR OLD.coordinate_schema_digest IS NOT NEW.coordinate_schema_digest
BEGIN
    SELECT RAISE(ABORT, 'activation conformance chain-tip identity cannot be updated');
END;

-- v8.4.2 recurrent symbiotic circulation ledger.  Append-only hash chain per
-- repository/session.  Exactly-once per (session, turn, kind) permits repeated
-- [context→proposal→evaluation→action→outcome] turns; event_id is immutable.
CREATE TABLE IF NOT EXISTS symbiotic_circulation_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    subject_receipt_hash TEXT NOT NULL CHECK(length(subject_receipt_hash) = 64),
    previous_receipt_hash TEXT NOT NULL CHECK(length(previous_receipt_hash) = 64),
    chain_sequence INTEGER NOT NULL CHECK(chain_sequence >= 1),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL DEFAULT 0,
    event_id TEXT NOT NULL DEFAULT '',
    body_epoch_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, session_id, turn_id, kind),
    UNIQUE(repository_id, session_id, chain_sequence),
    UNIQUE(repository_id, session_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_symbiotic_receipts_repo_session
ON symbiotic_circulation_receipts(repo, session_id, chain_sequence);
CREATE INDEX IF NOT EXISTS idx_symbiotic_receipts_repo_created
ON symbiotic_circulation_receipts(repo, created_at DESC, receipt_hash);
CREATE INDEX IF NOT EXISTS idx_symbiotic_receipts_turn
ON symbiotic_circulation_receipts(repo, session_id, turn_id, kind);

CREATE TABLE IF NOT EXISTS symbiotic_circulation_chain_tips(
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    body_epoch_id TEXT NOT NULL,
    tip_receipt_hash TEXT NOT NULL,
    receipt_count INTEGER NOT NULL CHECK(receipt_count >= 1),
    updated_at REAL NOT NULL,
    PRIMARY KEY(repository_id, session_id),
    FOREIGN KEY(tip_receipt_hash)
        REFERENCES symbiotic_circulation_receipts(receipt_hash) ON DELETE RESTRICT
);

CREATE TRIGGER IF NOT EXISTS symbiotic_circulation_receipts_no_delete
BEFORE DELETE ON symbiotic_circulation_receipts
BEGIN
    SELECT RAISE(ABORT, 'canonical symbiotic circulation receipts cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS symbiotic_circulation_receipts_no_update
BEFORE UPDATE ON symbiotic_circulation_receipts
BEGIN
    SELECT RAISE(ABORT, 'canonical symbiotic circulation receipts cannot be updated');
END;

-- v8.4.4 interconnect trajectory ledger (frames + transitions)
CREATE TABLE IF NOT EXISTS interconnect_frames(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    body_epoch_id TEXT NOT NULL,
    frame_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    overall_state TEXT NOT NULL DEFAULT 'unknown',
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, session_id, turn_id),
    UNIQUE(repository_id, session_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_interconnect_frames_repo_session
ON interconnect_frames(repo, session_id, turn_id);

CREATE TABLE IF NOT EXISTS interconnect_transitions(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    prior_frame_hash TEXT NOT NULL,
    next_frame_hash TEXT NOT NULL,
    outcome_hash TEXT,
    transition_class TEXT NOT NULL,
    causal_status TEXT NOT NULL,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(prior_frame_hash, next_frame_hash),
    UNIQUE(repository_id, session_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_interconnect_transitions_session
ON interconnect_transitions(repo, session_id, turn_id);

CREATE TABLE IF NOT EXISTS interconnect_trajectory_tips(
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tip_frame_hash TEXT NOT NULL,
    tip_transition_hash TEXT,
    frame_count INTEGER NOT NULL DEFAULT 0,
    transition_count INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL,
    PRIMARY KEY(repository_id, session_id)
);

CREATE TRIGGER IF NOT EXISTS interconnect_frames_no_delete
BEFORE DELETE ON interconnect_frames
BEGIN
    SELECT RAISE(ABORT, 'canonical interconnect frames cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS interconnect_frames_no_update
BEFORE UPDATE ON interconnect_frames
BEGIN
    SELECT RAISE(ABORT, 'canonical interconnect frames cannot be updated');
END;
CREATE TRIGGER IF NOT EXISTS interconnect_transitions_no_delete
BEFORE DELETE ON interconnect_transitions
BEGIN
    SELECT RAISE(ABORT, 'canonical interconnect transitions cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS interconnect_transitions_no_update
BEFORE UPDATE ON interconnect_transitions
BEGIN
    SELECT RAISE(ABORT, 'canonical interconnect transitions cannot be updated');
END;

-- v8.4.5 distillation candidate ledger (candidates only — not durable memory)
CREATE TABLE IF NOT EXISTS distillation_candidate_batches(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    transition_hash TEXT,
    prior_frame_hash TEXT,
    next_frame_hash TEXT,
    extraction_status TEXT NOT NULL,
    candidate_count INTEGER NOT NULL DEFAULT 0,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, session_id, turn_id),
    UNIQUE(repository_id, session_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_distill_cand_session
ON distillation_candidate_batches(repo, session_id, turn_id);

CREATE TRIGGER IF NOT EXISTS distillation_candidate_batches_no_delete
BEFORE DELETE ON distillation_candidate_batches
BEGIN
    SELECT RAISE(ABORT, 'canonical distillation candidate batches cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS distillation_candidate_batches_no_update
BEFORE UPDATE ON distillation_candidate_batches
BEGIN
    SELECT RAISE(ABORT, 'canonical distillation candidate batches cannot be updated');
END;

-- v8.5 authenticated will + membrane admission ledgers
CREATE TABLE IF NOT EXISTS will_principals(
    repo TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    secret_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(repo, principal_id),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS will_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    will_id TEXT NOT NULL,
    session_id TEXT,
    body_epoch_id TEXT,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, will_id),
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_will_receipts_repo
ON will_receipts(repo, principal_id, created_at);

CREATE TRIGGER IF NOT EXISTS will_receipts_no_delete
BEFORE DELETE ON will_receipts
BEGIN
    SELECT RAISE(ABORT, 'canonical will receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS will_receipts_no_update
BEFORE UPDATE ON will_receipts
BEGIN
    SELECT RAISE(ABORT, 'canonical will receipts cannot be updated');
END;

CREATE TABLE IF NOT EXISTS membrane_admissions(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT,
    will_id TEXT,
    will_receipt_hash TEXT,
    admitted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    deferred_count INTEGER NOT NULL DEFAULT 0,
    durable_write_authorized INTEGER NOT NULL DEFAULT 0,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_membrane_admissions_repo
ON membrane_admissions(repo, session_id, created_at);

CREATE TRIGGER IF NOT EXISTS membrane_admissions_no_delete
BEFORE DELETE ON membrane_admissions
BEGIN
    SELECT RAISE(ABORT, 'canonical membrane admissions cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS membrane_admissions_no_update
BEFORE UPDATE ON membrane_admissions
BEGIN
    SELECT RAISE(ABORT, 'canonical membrane admissions cannot be updated');
END;

-- v8.6 will-bound admitted memory ledger (durable lessons, not host mutation)
CREATE TABLE IF NOT EXISTS admitted_memories(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    memory_id TEXT NOT NULL,
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL DEFAULT 0,
    body_epoch_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    candidate_type TEXT NOT NULL,
    will_receipt_hash TEXT,
    membrane_receipt_hash TEXT,
    transition_hash TEXT,
    outcome_hash TEXT,
    support_level TEXT NOT NULL DEFAULT 'none',
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, candidate_id),
    UNIQUE(repository_id, memory_id),
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_admitted_memories_session
ON admitted_memories(repo, session_id, turn_id);
CREATE INDEX IF NOT EXISTS idx_admitted_memories_type
ON admitted_memories(repo, candidate_type);

CREATE TRIGGER IF NOT EXISTS admitted_memories_no_delete
BEFORE DELETE ON admitted_memories
BEGIN
    SELECT RAISE(ABORT, 'canonical admitted memories cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS admitted_memories_no_update
BEFORE UPDATE ON admitted_memories
BEGIN
    SELECT RAISE(ABORT, 'canonical admitted memories cannot be updated');
END;

-- v8.7 governed memory rehydration / revision ledgers
CREATE TABLE IF NOT EXISTS memory_state_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    state TEXT NOT NULL,
    state_sequence INTEGER NOT NULL,
    prior_state_receipt_hash TEXT,
    will_receipt_hash TEXT,
    effective_epoch_id TEXT,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, memory_id, state_sequence),
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_memory_state_memory
ON memory_state_receipts(repo, memory_id, state_sequence);

CREATE TABLE IF NOT EXISTS memory_projection_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL DEFAULT 0,
    projection_id TEXT NOT NULL,
    task_hash TEXT NOT NULL,
    body_epoch_id TEXT,
    current_will_hash TEXT,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, session_id, turn_id, projection_id),
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_memory_projection_session
ON memory_projection_receipts(repo, session_id, turn_id);

CREATE TABLE IF NOT EXISTS memory_use_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    projection_id TEXT NOT NULL,
    outcome_hash TEXT,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, projection_id, outcome_hash),
    UNIQUE(repository_id, event_id)
);

CREATE TABLE IF NOT EXISTS memory_credit_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    use_receipt_hash TEXT,
    credit_status TEXT NOT NULL,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_memory_credit_memory
ON memory_credit_receipts(repo, memory_id, created_at);

CREATE TABLE IF NOT EXISTS memory_challenge_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    challenged_memory_id TEXT NOT NULL,
    challenger_candidate_id TEXT NOT NULL,
    contradiction_kind TEXT NOT NULL,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, challenged_memory_id, challenger_candidate_id),
    UNIQUE(repository_id, event_id)
);

CREATE TABLE IF NOT EXISTS memory_supersession_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    superseded_memory_id TEXT NOT NULL,
    replacement_memory_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, superseded_memory_id, replacement_memory_id),
    UNIQUE(repository_id, event_id)
);

CREATE TRIGGER IF NOT EXISTS memory_state_receipts_no_delete
BEFORE DELETE ON memory_state_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory state receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_state_receipts_no_update
BEFORE UPDATE ON memory_state_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory state receipts cannot be updated');
END;
CREATE TRIGGER IF NOT EXISTS memory_projection_receipts_no_delete
BEFORE DELETE ON memory_projection_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory projection receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_projection_receipts_no_update
BEFORE UPDATE ON memory_projection_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory projection receipts cannot be updated');
END;
CREATE TRIGGER IF NOT EXISTS memory_use_receipts_no_delete
BEFORE DELETE ON memory_use_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory use receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_use_receipts_no_update
BEFORE UPDATE ON memory_use_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory use receipts cannot be updated');
END;
CREATE TRIGGER IF NOT EXISTS memory_credit_receipts_no_delete
BEFORE DELETE ON memory_credit_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory credit receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_credit_receipts_no_update
BEFORE UPDATE ON memory_credit_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory credit receipts cannot be updated');
END;
CREATE TRIGGER IF NOT EXISTS memory_challenge_receipts_no_delete
BEFORE DELETE ON memory_challenge_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory challenge receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_challenge_receipts_no_update
BEFORE UPDATE ON memory_challenge_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory challenge receipts cannot be updated');
END;
CREATE TRIGGER IF NOT EXISTS memory_supersession_receipts_no_delete
BEFORE DELETE ON memory_supersession_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory supersession receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_supersession_receipts_no_update
BEFORE UPDATE ON memory_supersession_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory supersession receipts cannot be updated');
END;

-- v8.8 cross-instantiation memory trial receipts
CREATE TABLE IF NOT EXISTS memory_trial_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    task_hash TEXT NOT NULL,
    g_rehydration REAL,
    g_credit REAL,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_memory_trial_repo
ON memory_trial_receipts(repo, created_at);

CREATE TRIGGER IF NOT EXISTS memory_trial_receipts_no_delete
BEFORE DELETE ON memory_trial_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory trial receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS memory_trial_receipts_no_update
BEFORE UPDATE ON memory_trial_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical memory trial receipts cannot be updated');
END;

-- v8.9 trial-guided projection budget apply receipts
CREATE TABLE IF NOT EXISTS projection_budget_receipts(
    receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
    repository_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    budget_policy_hash TEXT NOT NULL,
    mode TEXT,
    event_id TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(repository_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_projection_budget_repo
ON projection_budget_receipts(repo, created_at);

CREATE TRIGGER IF NOT EXISTS projection_budget_receipts_no_delete
BEFORE DELETE ON projection_budget_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical projection budget receipts cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS projection_budget_receipts_no_update
BEFORE UPDATE ON projection_budget_receipts BEGIN
    SELECT RAISE(ABORT, 'canonical projection budget receipts cannot be updated');
END;

CREATE TABLE IF NOT EXISTS evidence_credit(
    outcome_id TEXT NOT NULL,
    memory_id INTEGER,
    node_id TEXT,
    synapse_id TEXT,
    contribution REAL NOT NULL,
    reward_share REAL NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY(outcome_id, node_id, synapse_id),
    FOREIGN KEY(outcome_id) REFERENCES task_outcomes(outcome_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS continuation_packets(
    packet_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    origin_version TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_continuation_packets_repo_created
ON continuation_packets(repo, created_at);

CREATE TABLE IF NOT EXISTS canonical_states(
    repo TEXT NOT NULL,
    state_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY(repo, state_key),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS continuation_receipts(
    receipt_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    action TEXT NOT NULL,
    state_key TEXT NOT NULL,
    previous_json TEXT,
    candidate_json TEXT,
    evidence_json TEXT NOT NULL,
    verification_json TEXT NOT NULL,
    authority_json TEXT NOT NULL,
    rollback_of TEXT,
    previous_hash TEXT NOT NULL,
    receipt_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_continuation_receipts_repo_created
ON continuation_receipts(repo, created_at);

CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- ── v5.0 governed local cognition substrate (additive; one body) ──────────
CREATE TABLE IF NOT EXISTS coverage_facts(
    repo TEXT NOT NULL,
    test_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    coverage_kind TEXT NOT NULL,
    weight REAL NOT NULL,
    source TEXT NOT NULL,
    observed_at REAL NOT NULL,
    PRIMARY KEY(repo, test_node_id, target_node_id, coverage_kind),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ranker_models(
    repo TEXT NOT NULL,
    model_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    feature_names_json TEXT NOT NULL,
    weights_json TEXT NOT NULL,
    bias REAL NOT NULL,
    train_count INTEGER NOT NULL DEFAULT 0,
    last_outcome_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY(repo, model_id),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ranker_examples(
    example_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    outcome_id TEXT NOT NULL,
    activation_id TEXT NOT NULL,
    feature_vector_json TEXT NOT NULL,
    label REAL NOT NULL,
    verification_type TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_ranker_examples_repo ON ranker_examples(repo, created_at);

CREATE TABLE IF NOT EXISTS prediction_traces(
    trace_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    session_id TEXT,
    task_hash TEXT NOT NULL,
    predicted_paths_json TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    materialize_cost INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prediction_outcomes(
    trace_id TEXT PRIMARY KEY,
    used_count INTEGER NOT NULL,
    unused_count INTEGER NOT NULL,
    precision REAL NOT NULL,
    outcome_id TEXT,
    FOREIGN KEY(trace_id) REFERENCES prediction_traces(trace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contract_checks(
    check_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    packet_id TEXT NOT NULL,
    contract_hash TEXT NOT NULL,
    result TEXT NOT NULL,
    breaks_json TEXT NOT NULL,
    differential_json TEXT NOT NULL DEFAULT '{}',
    checked_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_principals(
    repo TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    secret_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(repo, agent_id),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS capability_tokens(
    token_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    not_before REAL NOT NULL,
    not_after REAL NOT NULL,
    issued_by TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_conflicts(
    conflict_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    session_a TEXT NOT NULL,
    session_b TEXT NOT NULL,
    path_or_claim TEXT NOT NULL,
    resolution TEXT NOT NULL,
    receipt_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shared_locks(
    repo TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    holder_agent_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY(repo, resource_key),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vector_indices(
    repo TEXT NOT NULL,
    index_id TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    dim INTEGER NOT NULL,
    metric TEXT NOT NULL,
    params_json TEXT NOT NULL,
    build_fingerprint TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(repo, index_id),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vector_index_nodes(
    repo TEXT NOT NULL,
    index_id TEXT NOT NULL,
    node_key TEXT NOT NULL,
    vector_kind TEXT NOT NULL,
    layer INTEGER NOT NULL DEFAULT 0,
    neighbors_json TEXT NOT NULL DEFAULT '[]',
    vector_blob BLOB NOT NULL,
    path TEXT NOT NULL DEFAULT '',
    memory_id INTEGER,
    PRIMARY KEY(repo, index_id, node_key, vector_kind),
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_vin_repo_index ON vector_index_nodes(repo, index_id);

CREATE TABLE IF NOT EXISTS causal_episodes(
    episode_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    task_family TEXT NOT NULL,
    baseline_fingerprint TEXT NOT NULL,
    treatment_json TEXT NOT NULL,
    metrics_before_json TEXT NOT NULL,
    metrics_after_json TEXT NOT NULL,
    delta_json TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confounds_json TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL,
    FOREIGN KEY(repo) REFERENCES repositories(name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS causal_links(
    episode_id TEXT NOT NULL,
    cause_kind TEXT NOT NULL,
    cause_id TEXT NOT NULL,
    effect_metric TEXT NOT NULL,
    effect_delta REAL NOT NULL,
    PRIMARY KEY(episode_id, cause_kind, cause_id, effect_metric),
    FOREIGN KEY(episode_id) REFERENCES causal_episodes(episode_id) ON DELETE CASCADE
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # The local Cortex UI serializes its shared connection and gives active
        # model turns independent Store connections. Disabling Python's thread
        # affinity guard permits that governed loopback-service boundary.
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript(SCHEMA)
        self._ensure_v5_columns()
        self._ensure_v625_tables()
        self._ensure_symbiotic_v842()

    def _ensure_symbiotic_v842(self) -> None:
        """Migrate v8.4.1 session/kind uniqueness to v8.4.2 turn-scoped uniqueness."""
        row = self.db.execute(
            """SELECT name FROM sqlite_master
               WHERE type='table' AND name='symbiotic_circulation_receipts'"""
        ).fetchone()
        if row is None:
            return
        cols = {
            item[1]
            for item in self.db.execute(
                "PRAGMA table_info(symbiotic_circulation_receipts)"
            ).fetchall()
        }
        if "turn_id" in cols and "event_id" in cols:
            return
        # Rebuild: preserve rows with turn_id=0 and synthetic event_ids.
        self.db.executescript(
            """
            ALTER TABLE symbiotic_circulation_receipts
                RENAME TO symbiotic_circulation_receipts_pre_v842;
            CREATE TABLE symbiotic_circulation_receipts(
                receipt_hash TEXT PRIMARY KEY CHECK(length(receipt_hash) = 64),
                subject_receipt_hash TEXT NOT NULL CHECK(length(subject_receipt_hash) = 64),
                previous_receipt_hash TEXT NOT NULL CHECK(length(previous_receipt_hash) = 64),
                chain_sequence INTEGER NOT NULL CHECK(chain_sequence >= 1),
                repository_id TEXT NOT NULL,
                repo TEXT NOT NULL,
                session_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL DEFAULT 0,
                event_id TEXT NOT NULL DEFAULT '',
                body_epoch_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                receipt_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(repository_id, session_id, turn_id, kind),
                UNIQUE(repository_id, session_id, chain_sequence),
                UNIQUE(repository_id, session_id, event_id)
            );
            INSERT INTO symbiotic_circulation_receipts(
                receipt_hash, subject_receipt_hash, previous_receipt_hash,
                chain_sequence, repository_id, repo, session_id, turn_id, event_id,
                body_epoch_id, kind, status, receipt_json, created_at
            )
            SELECT
                receipt_hash, subject_receipt_hash, previous_receipt_hash,
                chain_sequence, repository_id, repo, session_id, 0,
                'evt_legacy_' || kind || '_' || printf('%04d', chain_sequence),
                body_epoch_id, kind, status, receipt_json, created_at
            FROM symbiotic_circulation_receipts_pre_v842;
            DROP TABLE symbiotic_circulation_receipts_pre_v842;
            CREATE INDEX IF NOT EXISTS idx_symbiotic_receipts_repo_session
            ON symbiotic_circulation_receipts(repo, session_id, chain_sequence);
            CREATE INDEX IF NOT EXISTS idx_symbiotic_receipts_repo_created
            ON symbiotic_circulation_receipts(repo, created_at DESC, receipt_hash);
            CREATE INDEX IF NOT EXISTS idx_symbiotic_receipts_turn
            ON symbiotic_circulation_receipts(repo, session_id, turn_id, kind);
            DROP TRIGGER IF EXISTS symbiotic_circulation_receipts_no_delete;
            DROP TRIGGER IF EXISTS symbiotic_circulation_receipts_no_update;
            CREATE TRIGGER symbiotic_circulation_receipts_no_delete
            BEFORE DELETE ON symbiotic_circulation_receipts
            BEGIN
                SELECT RAISE(ABORT, 'canonical symbiotic circulation receipts cannot be deleted');
            END;
            CREATE TRIGGER symbiotic_circulation_receipts_no_update
            BEFORE UPDATE ON symbiotic_circulation_receipts
            BEGIN
                SELECT RAISE(ABORT, 'canonical symbiotic circulation receipts cannot be updated');
            END;
            """
        )
        self.db.commit()

    def _ensure_v5_columns(self) -> None:
        """Additive columns on pre-v5 neural_nodes without rebuilding the table."""

        cols = {
            row[1]
            for row in self.db.execute("PRAGMA table_info(neural_nodes)").fetchall()
        }
        alters: list[str] = []
        if "resolution" not in cols:
            alters.append(
                "ALTER TABLE neural_nodes ADD COLUMN resolution TEXT NOT NULL DEFAULT 'file'"
            )
        if "parent_node_id" not in cols:
            alters.append("ALTER TABLE neural_nodes ADD COLUMN parent_node_id TEXT")
        if "span_start" not in cols:
            alters.append("ALTER TABLE neural_nodes ADD COLUMN span_start INTEGER")
        if "span_end" not in cols:
            alters.append("ALTER TABLE neural_nodes ADD COLUMN span_end INTEGER")
        if "fingerprint" not in cols:
            alters.append("ALTER TABLE neural_nodes ADD COLUMN fingerprint TEXT")
        for stmt in alters:
            self.db.execute(stmt)
        if alters:
            self.db.commit()

    def _ensure_v625_tables(self) -> None:
        """Constitutional Immunity + Seal tables."""
        try:
            from .adapter_provenance import ensure_adapter_provenance_tables
            from .competence import ensure_competence_tables
            from .competence_assimilation import ensure_assimilation_tables
            from .competence_distribution import ensure_distribution_tables
            from .competence_revision import ensure_revision_tables
            from .competence_transfer import ensure_transfer_tables
            from .immunity import ensure_immunity_tables
            from .lineage import ensure_lineage_tables
            from .quarantine import ensure_quarantine_tables
            from .ranker.model import ensure_training_events
            from .state_transition import ensure_transition_tables
            from .unlearning import ensure_unlearning_tables
            from .witness import ensure_witness_tables

            ensure_lineage_tables(self)
            ensure_quarantine_tables(self)
            ensure_unlearning_tables(self)
            ensure_immunity_tables(self)
            ensure_transition_tables(self)
            ensure_training_events(self)
            ensure_witness_tables(self)
            ensure_competence_tables(self)
            ensure_transfer_tables(self)
            ensure_distribution_tables(self)
            ensure_adapter_provenance_tables(self)
            ensure_assimilation_tables(self)
            ensure_revision_tables(self)
            from .epoch import ensure_epoch_tables
            from .phases import ensure_phase_tables

            ensure_epoch_tables(self)
            ensure_phase_tables(self)
        except Exception:
            pass

    def close(self) -> None:
        self.db.close()

    def commit(self) -> None:
        self.db.commit()

    @contextmanager
    def transaction(self):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            yield self.db
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def integrity_check(self) -> bool:
        row = self.db.execute("PRAGMA integrity_check").fetchone()
        return bool(row and row[0] == "ok")

    def attach(self, name: str, repository_id: str, path: Path) -> None:
        now = time.time()
        existing = self.repo(name)
        resolved_path = str(path.resolve())
        if existing and (existing["repository_id"] != repository_id or existing["path"] != resolved_path):
            self.db.execute("DELETE FROM repositories WHERE name=?", (name,))
            self.db.commit()
        self.db.execute(
            """
            INSERT INTO repositories(name, repository_id, path, attached_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
              repository_id=excluded.repository_id,
              path=excluded.path
            """,
            (name, repository_id, resolved_path, now),
        )
        self.db.commit()

    def repo(self, name: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM repositories WHERE name=?", (name,)).fetchone()

    def repo_by_path(self, path: Path) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM repositories WHERE path=?", (str(path.resolve()),)
        ).fetchone()

    def repos(self) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM repositories ORDER BY name").fetchall()

    def update_repo_state(
        self,
        repo: str,
        *,
        manifest_hash: str | None = None,
        bootstrap_status: str | None = None,
        indexed: bool = False,
        bootstrapped: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        fields: list[str] = []
        values: list[Any] = []
        if manifest_hash is not None:
            fields.append("manifest_hash=?")
            values.append(manifest_hash)
        if bootstrap_status is not None:
            fields.append("bootstrap_status=?")
            values.append(bootstrap_status)
        if indexed:
            fields.append("last_indexed=?")
            values.append(time.time())
        if bootstrapped:
            fields.append("last_bootstrap=?")
            values.append(time.time())
        if metadata is not None:
            fields.append("metadata=?")
            values.append(json.dumps(metadata, sort_keys=True))
        if not fields:
            return
        values.append(repo)
        self.db.execute(f"UPDATE repositories SET {', '.join(fields)} WHERE name=?", values)
        self.db.commit()

    def file(self, repo: str, path: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM files WHERE repo=? AND path=?", (repo, path)
        ).fetchone()

    def files(self, repo: str, status: str | None = None) -> list[sqlite3.Row]:
        if status:
            return self.db.execute(
                "SELECT * FROM files WHERE repo=? AND status=? ORDER BY path", (repo, status)
            ).fetchall()
        return self.db.execute("SELECT * FROM files WHERE repo=? ORDER BY path", (repo,)).fetchall()

    def upsert_file(self, record: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO files(
              repo, path, kind, language, size_bytes, mtime_ns, content_hash,
              status, authoritative, indexed_at, metadata
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo, path) DO UPDATE SET
              kind=excluded.kind,
              language=excluded.language,
              size_bytes=excluded.size_bytes,
              mtime_ns=excluded.mtime_ns,
              content_hash=excluded.content_hash,
              status=excluded.status,
              authoritative=excluded.authoritative,
              indexed_at=excluded.indexed_at,
              metadata=excluded.metadata
            """,
            (
                record["repo"], record["path"], record["kind"], record["language"],
                record["size_bytes"], record["mtime_ns"], record["content_hash"],
                record["status"], int(record.get("authoritative", False)), time.time(),
                json.dumps(record.get("metadata", {}), sort_keys=True),
            ),
        )

    def delete_missing_files(self, repo: str, live_paths: set[str]) -> list[str]:
        existing = {row["path"] for row in self.files(repo)}
        missing = sorted(existing - live_paths)
        for path in missing:
            self.remove_path(repo, path)
            self.db.execute("DELETE FROM files WHERE repo=? AND path=?", (repo, path))
        return missing

    def remove_path(self, repo: str, path: str) -> None:
        self.db.execute("DELETE FROM memories WHERE repo=? AND path=?", (repo, path))
        self.db.execute("DELETE FROM symbols WHERE repo=? AND path=?", (repo, path))
        self.db.execute(
            "DELETE FROM edges WHERE repo=? AND (source=? OR target=?)", (repo, path, path)
        )

    def upsert_memory(self, **memory: Any) -> None:
        now = time.time()
        vector = memory.get("vector")
        self.db.execute(
            """
            INSERT INTO memories(
              repo, path, chunk_index, start_line, end_line, kind, text, content_hash,
              vector, embedding_model, metadata, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo, path, chunk_index, content_hash) DO UPDATE SET
              start_line=excluded.start_line,
              end_line=excluded.end_line,
              kind=excluded.kind,
              text=excluded.text,
              vector=excluded.vector,
              embedding_model=excluded.embedding_model,
              metadata=excluded.metadata,
              updated_at=excluded.updated_at
            """,
            (
                memory["repo"], memory["path"], memory["chunk_index"],
                memory["start_line"], memory["end_line"], memory["kind"],
                memory["text"], memory["content_hash"],
                vector_to_bytes(vector), memory.get("embedding_model"),
                json.dumps(memory.get("metadata", {}), sort_keys=True), now, now,
            ),
        )
        if vector is not None:
            row = self.db.execute(
                """SELECT id FROM memories
                   WHERE repo=? AND path=? AND chunk_index=? AND content_hash=?""",
                (
                    memory["repo"], memory["path"], memory["chunk_index"],
                    memory["content_hash"],
                ),
            ).fetchone()
            if row:
                self.db.execute(
                    """INSERT INTO memory_vector_buckets(memory_id, repo, bucket)
                       VALUES(?, ?, ?)
                       ON CONFLICT(memory_id) DO UPDATE SET
                         repo=excluded.repo, bucket=excluded.bucket""",
                    (row["id"], memory["repo"], vector_bucket(vector)),
                )

    def memory(self, memory_id: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()

    def memories_for_path(self, repo: str, path: str) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM memories WHERE repo=? AND path=? ORDER BY chunk_index",
            (repo, path),
        ).fetchall()

    def all_vectors(
        self, repo: str, excluded_prefixes: tuple[str, ...] = ()
    ) -> list[sqlite3.Row]:
        exclusions = " ".join("AND path NOT LIKE ?" for _ in excluded_prefixes)
        return self.db.execute(
            f"""SELECT * FROM memories
                WHERE repo=? AND vector IS NOT NULL {exclusions}""",
            [repo, *(f"{prefix}%" for prefix in excluded_prefixes)],
        ).fetchall()

    def vector_candidates(
        self, repo: str, preferred_ids: list[int], limit: int, seed: int,
        query_vector: list[float] | None = None,
        excluded_prefixes: tuple[str, ...] = (),
    ) -> list[sqlite3.Row]:
        output: dict[int, sqlite3.Row] = {}
        memory_exclusions = " ".join(
            "AND path NOT LIKE ?" for _ in excluded_prefixes
        )
        aliased_exclusions = " ".join(
            "AND m.path NOT LIKE ?" for _ in excluded_prefixes
        )
        exclusion_args = [f"{prefix}%" for prefix in excluded_prefixes]
        if preferred_ids:
            marks = ",".join("?" for _ in preferred_ids)
            rows = self.db.execute(
                f"""SELECT * FROM memories
                    WHERE repo=? AND id IN ({marks}) AND vector IS NOT NULL
                    {memory_exclusions}""",
                [repo, *preferred_ids, *exclusion_args],
            ).fetchall()
            output.update({row["id"]: row for row in rows})
        remaining = max(0, limit - len(output))
        if remaining == 0:
            return list(output.values())
        if query_vector:
            bucket = vector_bucket(query_vector)
            nearby = [bucket, *(bucket ^ (1 << bit) for bit in range(16))]
            marks = ",".join("?" for _ in nearby)
            rows = self.db.execute(
                f"""SELECT m.* FROM memory_vector_buckets b
                    JOIN memories m ON m.id=b.memory_id
                    WHERE b.repo=? AND b.bucket IN ({marks}) AND m.vector IS NOT NULL
                    {aliased_exclusions}
                    ORDER BY CASE WHEN b.bucket=? THEN 0 ELSE 1 END, m.id
                    LIMIT ?""",
                [repo, *nearby, *exclusion_args, bucket, remaining],
            ).fetchall()
            output.update({row["id"]: row for row in rows})
            remaining = max(0, limit - len(output))
            if remaining == 0:
                return list(output.values())
        bounds = self.db.execute(
            f"""SELECT MIN(id), MAX(id), COUNT(*) FROM memories
                WHERE repo=? AND vector IS NOT NULL {memory_exclusions}""",
            [repo, *exclusion_args],
        ).fetchone()
        if not bounds or not bounds[2]:
            return list(output.values())
        minimum, maximum, count = int(bounds[0]), int(bounds[1]), int(bounds[2])
        if count <= remaining:
            rows = self.all_vectors(repo, excluded_prefixes)
        else:
            span = max(1, maximum - minimum + 1)
            pivot = minimum + (seed % span)
            rows = self.db.execute(
                f"""SELECT * FROM memories
                    WHERE repo=? AND vector IS NOT NULL AND id>=?
                    {memory_exclusions} ORDER BY id LIMIT ?""",
                [repo, pivot, *exclusion_args, remaining],
            ).fetchall()
            if len(rows) < remaining:
                rows += self.db.execute(
                    f"""SELECT * FROM memories
                        WHERE repo=? AND vector IS NOT NULL AND id<?
                        {memory_exclusions} ORDER BY id LIMIT ?""",
                    [repo, pivot, *exclusion_args, remaining - len(rows)],
                ).fetchall()
        output.update({row["id"]: row for row in rows})
        return list(output.values())

    def ensure_vector_buckets(self, repo: str) -> int:
        """Backfill ANN sketches for databases created before Cortex v3."""
        setting_key = f"vector_bucket_model:{repo}"
        if self.get_setting(setting_key) != VECTOR_BUCKET_MODEL:
            self.db.execute("DELETE FROM memory_vector_buckets WHERE repo=?", (repo,))
            self.db.commit()
            self.set_setting(setting_key, VECTOR_BUCKET_MODEL)
        rows = self.db.execute(
            """SELECT m.id, m.vector FROM memories m
               LEFT JOIN memory_vector_buckets b ON b.memory_id=m.id
               WHERE m.repo=? AND m.vector IS NOT NULL AND b.memory_id IS NULL""",
            (repo,),
        ).fetchall()
        for row in rows:
            vector = deserialize_vector(row["vector"])
            if vector:
                self.db.execute(
                    "INSERT OR REPLACE INTO memory_vector_buckets(memory_id, repo, bucket) VALUES(?, ?, ?)",
                    (row["id"], repo, vector_bucket(vector)),
                )
        if rows:
            self.db.commit()
        return len(rows)

    def lexical(
        self,
        repo: str,
        query: str,
        limit: int = 40,
        excluded_prefixes: tuple[str, ...] = (),
    ) -> list[sqlite3.Row]:
        tokens = [token for token in query.replace('"', " ").split() if token]
        if not tokens:
            return []
        safe = " OR ".join(f'"{token}"' for token in tokens[:24])
        exclusions = " ".join(
            "AND m.path NOT LIKE ?" for _ in excluded_prefixes
        )
        try:
            return self.db.execute(
                f"""
                SELECT m.*, bm25(memories_fts) AS bm
                FROM memories_fts
                JOIN memories m ON m.id=memories_fts.rowid
                WHERE m.repo=? AND memories_fts MATCH ?
                {exclusions}
                ORDER BY bm LIMIT ?
                """,
                [
                    repo,
                    safe,
                    *(f"{prefix}%" for prefix in excluded_prefixes),
                    limit,
                ],
            ).fetchall()
        except sqlite3.OperationalError:
            return []

    def add_symbol(self, repo: str, path: str, symbol: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO symbols(
              repo, path, name, qualified_name, symbol_kind, start_line, end_line,
              signature, metadata
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo, path, symbol["name"], symbol["qualified_name"], symbol["symbol_kind"],
                symbol["start_line"], symbol["end_line"], symbol.get("signature", ""),
                json.dumps(symbol.get("metadata", {}), sort_keys=True),
            ),
        )

    def migrate_vectors(self, repo: str | None = None) -> dict[str, int]:
        """Upgrade legacy JSON or unversioned BLOB vectors without re-indexing source."""
        where = "WHERE vector IS NOT NULL"
        args: list[Any] = []
        if repo:
            where += " AND repo=?"
            args.append(repo)
        rows = self.db.execute(f"SELECT id, vector FROM memories {where}", args).fetchall()
        migrated = 0
        skipped = 0
        for row in rows:
            raw = row["vector"]
            if isinstance(raw, bytes) and raw.startswith(VECTOR_MAGIC):
                skipped += 1
                continue
            vector = deserialize_vector(raw)
            if not vector:
                skipped += 1
                continue
            self.db.execute("UPDATE memories SET vector=?, updated_at=? WHERE id=?", (vector_to_bytes(vector), time.time(), row["id"]))
            migrated += 1
        self.db.commit()
        result = {"scanned": len(rows), "migrated": migrated, "already_current_or_invalid": skipped}
        self.set_setting(f"vector_migration:{repo or 'all'}", {"completed_at": time.time(), **result})
        return result

    def vector_format_status(self, repo: str | None = None) -> dict[str, int]:
        where = "WHERE vector IS NOT NULL"
        args: list[Any] = []
        if repo:
            where += " AND repo=?"
            args.append(repo)
        rows = self.db.execute(f"SELECT vector FROM memories {where}", args).fetchall()
        current = sum(isinstance(row["vector"], bytes) and row["vector"].startswith(VECTOR_MAGIC) for row in rows)
        return {"total": len(rows), "current_versioned_blob": current, "legacy_or_invalid": len(rows) - current}

    def symbols(self, repo: str, path: str | None = None) -> list[sqlite3.Row]:
        if path:
            return self.db.execute(
                "SELECT * FROM symbols WHERE repo=? AND path=? ORDER BY start_line", (repo, path)
            ).fetchall()
        return self.db.execute(
            "SELECT * FROM symbols WHERE repo=? ORDER BY path, start_line", (repo,)
        ).fetchall()

    def add_edge(self, repo: str, edge: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT OR IGNORE INTO edges(
              repo, source, target, relation, confidence, evidence, metadata
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo, edge["source"], edge["target"], edge["relation"],
                float(edge["confidence"]), edge.get("evidence", ""),
                json.dumps(edge.get("metadata", {}), sort_keys=True),
            ),
        )

    def edges(
        self, repo: str, *, source: str | None = None, target: str | None = None,
        relation: str | None = None, limit: int = 500
    ) -> list[sqlite3.Row]:
        clauses = ["repo=?"]
        values: list[Any] = [repo]
        if source:
            clauses.append("source=?")
            values.append(source)
        if target:
            clauses.append("target=?")
            values.append(target)
        if relation:
            clauses.append("relation=?")
            values.append(relation)
        values.append(limit)
        return self.db.execute(
            f"SELECT * FROM edges WHERE {' AND '.join(clauses)} ORDER BY confidence DESC LIMIT ?",
            values,
        ).fetchall()

    def clear_edges(self, repo: str, relations: Iterable[str] | None = None) -> None:
        if relations:
            marks = ",".join("?" for _ in relations)
            values = [repo, *relations]
            self.db.execute(
                f"DELETE FROM edges WHERE repo=? AND relation IN ({marks})", values
            )
        else:
            self.db.execute("DELETE FROM edges WHERE repo=?", (repo,))

    def add_commit(self, repo: str, commit: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO git_commits(
              repo, commit_hash, authored_at, author, subject, files
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                repo, commit["commit_hash"], commit.get("authored_at"), commit.get("author"),
                commit.get("subject"), json.dumps(commit.get("files", [])),
            ),
        )

    def commits(self, repo: str, limit: int = 100) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM git_commits WHERE repo=? ORDER BY authored_at DESC LIMIT ?",
            (repo, limit),
        ).fetchall()

    def set_file_telemetry(self, repo: str, path: str, telemetry: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO file_telemetry(
              repo, path, commit_count, additions, deletions, last_changed,
              cochange_degree, metadata
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo, path) DO UPDATE SET
              commit_count=excluded.commit_count,
              additions=excluded.additions,
              deletions=excluded.deletions,
              last_changed=excluded.last_changed,
              cochange_degree=excluded.cochange_degree,
              metadata=excluded.metadata
            """,
            (
                repo, path, telemetry.get("commit_count", 0), telemetry.get("additions", 0),
                telemetry.get("deletions", 0), telemetry.get("last_changed"),
                telemetry.get("cochange_degree", 0),
                json.dumps(telemetry.get("metadata", {}), sort_keys=True),
            ),
        )

    def file_telemetry(self, repo: str, path: str | None = None) -> list[sqlite3.Row]:
        if path:
            return self.db.execute(
                "SELECT * FROM file_telemetry WHERE repo=? AND path=?", (repo, path)
            ).fetchall()
        return self.db.execute(
            "SELECT * FROM file_telemetry WHERE repo=? ORDER BY commit_count DESC", (repo,)
        ).fetchall()

    def begin_bootstrap(self, run_id: str, repo: str) -> None:
        self.db.execute(
            "INSERT INTO bootstrap_runs(run_id, repo, status, started_at) VALUES(?, ?, ?, ?)",
            (run_id, repo, "running", time.time()),
        )
        self.db.commit()

    def finish_bootstrap(
        self, run_id: str, status: str, manifest_hash: str, certificate: dict[str, Any]
    ) -> None:
        self.db.execute(
            """
            UPDATE bootstrap_runs
            SET status=?, completed_at=?, manifest_hash=?, certificate=?
            WHERE run_id=?
            """,
            (status, time.time(), manifest_hash, json.dumps(certificate, sort_keys=True), run_id),
        )
        self.db.commit()

    def latest_bootstrap(self, repo: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM bootstrap_runs WHERE repo=? ORDER BY started_at DESC LIMIT 1", (repo,)
        ).fetchone()

    def start_session(
        self, session_id: str, repo: str, task: str, metadata: dict[str, Any] | None = None
    ) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO sessions(
              session_id, repo, task, started_at, status, metadata
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (session_id, repo, task, time.time(), "active", json.dumps(metadata or {})),
        )
        self.db.commit()

    def end_session(self, session_id: str, status: str = "consolidated") -> None:
        self.db.execute(
            "UPDATE sessions SET ended_at=?, status=? WHERE session_id=?",
            (time.time(), status, session_id),
        )
        self.db.commit()

    def update_session_metadata(self, session_id: str, metadata: dict[str, Any]) -> None:
        self.db.execute(
            "UPDATE sessions SET metadata=? WHERE session_id=?",
            (json.dumps(metadata, sort_keys=True), session_id),
        )
        self.db.commit()

    def update_session_task(self, session_id: str, task: str) -> None:
        self.db.execute(
            "UPDATE sessions SET task=? WHERE session_id=?",
            (str(task), session_id),
        )
        self.db.commit()

    def session(self, session_id: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()

    def latest_session(self, repo: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM sessions WHERE repo=? ORDER BY started_at DESC LIMIT 1", (repo,)
        ).fetchone()

    def list_sessions(self, repo: str, limit: int = 100) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM sessions WHERE repo=? ORDER BY started_at DESC LIMIT ?",
            (repo, max(1, min(int(limit), 500))),
        ).fetchall()

    def add_event(
        self,
        session_id: str | None,
        repo: str,
        kind: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO events(session_id, repo, kind, text, metadata, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (session_id, repo, kind, text, json.dumps(metadata or {}), time.time()),
        )
        self.db.commit()

    def events(self, repo: str, session_id: str | None = None) -> list[sqlite3.Row]:
        if session_id:
            return self.db.execute(
                "SELECT * FROM events WHERE repo=? AND session_id=? ORDER BY id",
                (repo, session_id),
            ).fetchall()
        return self.db.execute(
            "SELECT * FROM events WHERE repo=? ORDER BY id DESC LIMIT 500", (repo,)
        ).fetchall()

    def set_environment_profile(self, repo: str, profile: dict[str, Any]) -> None:
        profile_hash = str(profile.get("profile_hash", ""))
        self.db.execute(
            """
            INSERT INTO environment_profiles(repo, profile_json, profile_hash, observed_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(repo) DO UPDATE SET
              profile_json=excluded.profile_json,
              profile_hash=excluded.profile_hash,
              observed_at=excluded.observed_at
            """,
            (repo, json.dumps(profile, sort_keys=True), profile_hash, time.time()),
        )
        self.db.commit()

    def environment_profile(self, repo: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT profile_json FROM environment_profiles WHERE repo=?", (repo,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def sync_neural_graph(self, repo: str, nodes: list[Any], synapses: list[Any]) -> None:
        live_nodes = {node.node_id for node in nodes}
        live_synapses = {synapse.synapse_id for synapse in synapses}
        now = time.time()
        with self.transaction() as conn:
            for node in nodes:
                resolution = getattr(node, "resolution", None) or (
                    (node.metadata or {}).get("resolution") or "file"
                )
                parent = getattr(node, "parent_node_id", None) or (
                    (node.metadata or {}).get("parent_node_id")
                )
                span_start = getattr(node, "span_start", None)
                if span_start is None:
                    span_start = (node.metadata or {}).get("span_start")
                span_end = getattr(node, "span_end", None)
                if span_end is None:
                    span_end = (node.metadata or {}).get("span_end")
                fingerprint = getattr(node, "fingerprint", None) or (
                    (node.metadata or {}).get("fingerprint")
                )
                conn.execute(
                    """
                    INSERT INTO neural_nodes(
                      repo, node_id, path, kind, threshold, tags_json, metadata, updated_at,
                      resolution, parent_node_id, span_start, span_end, fingerprint
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(repo, node_id) DO UPDATE SET
                      path=excluded.path, kind=excluded.kind, threshold=excluded.threshold,
                      tags_json=excluded.tags_json, metadata=excluded.metadata,
                      updated_at=excluded.updated_at, resolution=excluded.resolution,
                      parent_node_id=excluded.parent_node_id, span_start=excluded.span_start,
                      span_end=excluded.span_end, fingerprint=excluded.fingerprint
                    """,
                    (
                        repo, node.node_id, node.path, node.kind, node.threshold,
                        json.dumps(node.tags), json.dumps(node.metadata, sort_keys=True), now,
                        resolution, parent, span_start, span_end, fingerprint,
                    ),
                )
            for synapse in synapses:
                conn.execute(
                    """
                    INSERT INTO neural_synapses(
                      repo, synapse_id, source_id, target_id, relation, base_weight, weight,
                      minimum_weight, maximum_weight, plasticity_rule, update_count,
                      evidence, metadata, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(repo, synapse_id) DO UPDATE SET
                      source_id=excluded.source_id, target_id=excluded.target_id,
                      relation=excluded.relation, base_weight=excluded.base_weight,
                      weight=MIN(excluded.maximum_weight, MAX(excluded.minimum_weight, neural_synapses.weight)),
                      minimum_weight=excluded.minimum_weight, maximum_weight=excluded.maximum_weight,
                      plasticity_rule=excluded.plasticity_rule, evidence=excluded.evidence,
                      metadata=excluded.metadata, updated_at=excluded.updated_at
                    """,
                    (
                        repo, synapse.synapse_id, synapse.source_id, synapse.target_id,
                        synapse.relation, synapse.base_weight, synapse.weight,
                        synapse.minimum_weight, synapse.maximum_weight, synapse.plasticity_rule,
                        synapse.update_count, synapse.evidence,
                        json.dumps(synapse.metadata, sort_keys=True), now,
                    ),
                )
            if live_nodes:
                marks = ",".join("?" for _ in live_nodes)
                conn.execute(
                    f"DELETE FROM neural_nodes WHERE repo=? AND node_id NOT IN ({marks})",
                    [repo, *sorted(live_nodes)],
                )
            else:
                conn.execute("DELETE FROM neural_nodes WHERE repo=?", (repo,))
            if live_synapses:
                marks = ",".join("?" for _ in live_synapses)
                conn.execute(
                    f"DELETE FROM neural_synapses WHERE repo=? AND synapse_id NOT IN ({marks})",
                    [repo, *sorted(live_synapses)],
                )
            else:
                conn.execute("DELETE FROM neural_synapses WHERE repo=?", (repo,))

    def neural_nodes(self, repo: str) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM neural_nodes WHERE repo=? ORDER BY node_id", (repo,)
        ).fetchall()

    def neural_synapses(self, repo: str) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM neural_synapses WHERE repo=? ORDER BY synapse_id", (repo,)
        ).fetchall()

    def neural_graph_hash(self, repo: str) -> str:
        material = {
            "nodes": [
                [
                    row["node_id"],
                    row["path"],
                    row["kind"],
                    row["threshold"],
                    json.loads(row["metadata"] or "{}").get(
                        "neural_region", "repository"
                    ),
                ]
                for row in self.neural_nodes(repo)
            ],
            "synapses": [
                [
                    row["synapse_id"], row["source_id"], row["target_id"],
                    row["relation"], row["base_weight"], row["weight"], row["update_count"],
                ]
                for row in self.neural_synapses(repo)
            ],
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def update_neural_synapse_weight(self, repo: str, synapse_id: str, weight: float) -> None:
        self.db.execute(
            """
            UPDATE neural_synapses
            SET weight=MIN(maximum_weight, MAX(minimum_weight, ?)),
                update_count=update_count+1, updated_at=?
            WHERE repo=? AND synapse_id=?
            """,
            (float(weight), time.time(), repo, synapse_id),
        )
        self.db.commit()

    @staticmethod
    def _neural_event_hash(record: dict[str, Any]) -> str:
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _append_neural_event_conn(
        self, conn: sqlite3.Connection, repo: str, *, event_type: str,
        entity_id: str, payload: dict[str, Any]
    ) -> str:
        tail = conn.execute(
            "SELECT sequence, event_hash FROM neural_ledger WHERE repo=? ORDER BY sequence DESC LIMIT 1",
            (repo,),
        ).fetchone()
        sequence = int(tail["sequence"]) + 1 if tail else 1
        previous_hash = str(tail["event_hash"]) if tail else "0" * 64
        created_at = time.time()
        record = {
            "repo": repo,
            "sequence": sequence,
            "event_type": event_type,
            "entity_id": entity_id,
            "payload": payload,
            "created_at": created_at,
            "previous_hash": previous_hash,
        }
        event_hash = self._neural_event_hash(record)
        conn.execute(
            """
            INSERT INTO neural_ledger(
              repo, sequence, event_type, entity_id, payload, created_at, previous_hash, event_hash
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo, sequence, event_type, entity_id,
                json.dumps(payload, sort_keys=True), created_at, previous_hash, event_hash,
            ),
        )
        return event_hash

    def append_neural_event(
        self, repo: str, *, event_type: str, entity_id: str, payload: dict[str, Any]
    ) -> str:
        with self.transaction() as conn:
            return self._append_neural_event_conn(
                conn, repo, event_type=event_type, entity_id=entity_id, payload=payload
            )

    def apply_neural_plasticity(
        self, repo: str, activation_id: str, updates: list[dict[str, Any]]
    ) -> str | None:
        if not updates:
            return None
        with self.transaction() as conn:
            for update in updates:
                conn.execute(
                    """
                    UPDATE neural_synapses
                    SET weight=MIN(maximum_weight, MAX(minimum_weight, ?)),
                        update_count=update_count+1, updated_at=?
                    WHERE repo=? AND synapse_id=?
                    """,
                    (
                        float(update["proposed_weight"]), time.time(), repo,
                        str(update["synapse_id"]),
                    ),
                )
            return self._append_neural_event_conn(
                conn,
                repo,
                event_type="plasticity_applied",
                entity_id=activation_id,
                payload={"updates": updates},
            )

    def neural_events(self, repo: str, limit: int = 100) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM neural_ledger WHERE repo=? ORDER BY sequence DESC LIMIT ?",
            (repo, limit),
        ).fetchall()

    def verify_neural_ledger(self, repo: str) -> bool:
        previous = "0" * 64
        expected = 1
        rows = self.db.execute(
            "SELECT * FROM neural_ledger WHERE repo=? ORDER BY sequence", (repo,)
        ).fetchall()
        for row in rows:
            if int(row["sequence"]) != expected or row["previous_hash"] != previous:
                return False
            payload = json.loads(row["payload"] or "{}")
            record = {
                "repo": repo,
                "sequence": int(row["sequence"]),
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "payload": payload,
                "created_at": float(row["created_at"]),
                "previous_hash": row["previous_hash"],
            }
            if self._neural_event_hash(record) != row["event_hash"]:
                return False
            previous = row["event_hash"]
            expected += 1
        return True

    def record_neural_activation(
        self, repo: str, session_id: str | None, payload: dict[str, Any]
    ) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO neural_activations(
              activation_id, repo, session_id, task_hash, state_hash, payload, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["activation_id"], repo, session_id, payload["task_hash"],
                payload["state_hash"], json.dumps(payload, sort_keys=True), time.time(),
            ),
        )
        self.db.commit()

    def neural_activations(self, repo: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT payload FROM neural_activations WHERE repo=? ORDER BY created_at DESC LIMIT ?",
            (repo, limit),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def neural_activation(self, repo: str, activation_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload FROM neural_activations WHERE repo=? AND activation_id=?", (repo, activation_id)
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def record_outcome(
        self, repo: str, *, outcome_id: str, activation_id: str, status: str, reward: float,
        verification_type: str, verification_payload: dict[str, Any], credits: list[dict[str, Any]],
        updates: list[dict[str, Any]], apply_updates: bool,
    ) -> None:
        activation = self.db.execute(
            "SELECT session_id FROM neural_activations WHERE repo=? AND activation_id=?", (repo, activation_id)
        ).fetchone()
        if not activation:
            raise ValueError("Activation does not belong to this repository")
        now = time.time()
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO task_outcomes(outcome_id, repo, session_id, activation_id, status, reward,
                   verification_type, verification_payload_json, created_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (outcome_id, repo, activation["session_id"], activation_id, status, reward,
                 verification_type, json.dumps(verification_payload, sort_keys=True), now),
            )
            for credit in credits:
                conn.execute(
                    """INSERT INTO evidence_credit(outcome_id, memory_id, node_id, synapse_id, contribution,
                       reward_share, reason) VALUES(?, ?, ?, ?, ?, ?, ?)""",
                    (outcome_id, credit.get("memory_id"), credit.get("node_id"), credit.get("synapse_id"),
                     credit["contribution"], credit["reward_share"], credit["reason"]),
                )
            if apply_updates:
                for update in updates:
                    conn.execute(
                        """UPDATE neural_synapses SET weight=MIN(maximum_weight, MAX(minimum_weight, ?)),
                           update_count=update_count+1, updated_at=? WHERE repo=? AND synapse_id=?""",
                        (float(update["proposed_weight"]), now, repo, update["synapse_id"]),
                    )
            self._append_neural_event_conn(
                conn, repo, event_type="verified_outcome", entity_id=outcome_id,
                payload={"activation_id": activation_id, "status": status, "reward": reward,
                         "verification_type": verification_type, "credits": len(credits),
                         "updates": updates, "applied": apply_updates},
            )

    def outcomes(self, repo: str, limit: int = 100) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM task_outcomes WHERE repo=? ORDER BY created_at DESC LIMIT ?", (repo, limit)
        ).fetchall()

    def record_interlock_observation(
        self,
        repo: str,
        *,
        activation_id: str,
        session_id: str | None,
        body_epoch_id: str,
        task_family: str,
        evidence_paths: list[str],
        learned_paths: list[str],
        constitutional_valid: bool,
        u_before: float | None = None,
        u_after: float | None = None,
        metadata: dict[str, Any] | None = None,
        max_observations: int = 4096,
    ) -> dict[str, Any]:
        """Append one bounded E-L observation for an existing activation.

        Outcome resolution is deliberately separate so learned association can
        never masquerade as independently witnessed task utility.
        """
        activation = self.db.execute(
            "SELECT 1 FROM neural_activations WHERE repo=? AND activation_id=?",
            (repo, activation_id),
        ).fetchone()
        if not activation:
            raise ValueError("Activation does not belong to this repository")
        now = time.time()
        evidence = sorted({str(p) for p in evidence_paths if str(p).strip()})[:64]
        learned = sorted({str(p) for p in learned_paths if str(p).strip()})[:64]
        delta_u = (
            float(u_after) - float(u_before)
            if u_before is not None and u_after is not None
            else None
        )
        material = {
            "repo": repo,
            "activation_id": activation_id,
            "session_id": session_id,
            "body_epoch_id": body_epoch_id,
            "task_family": task_family,
            "evidence_paths": evidence,
            "learned_paths": learned,
            "u_before": u_before,
            "u_after": u_after,
            "delta_u": delta_u,
            "constitutional_valid": bool(constitutional_valid),
            "metadata": metadata or {},
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
        receipt_hash = sha256(canonical.encode("utf-8")).hexdigest()
        observation_id = "ilo_" + receipt_hash[:24]
        with self.transaction() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO information_interlock_observations(
                   observation_id, repo, activation_id, session_id, body_epoch_id,
                   task_family, evidence_paths_json, learned_paths_json, u_before,
                   u_after, delta_u, constitutional_valid, created_at, receipt_hash,
                   metadata_json
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    observation_id, repo, activation_id, session_id, body_epoch_id,
                    task_family, json.dumps(evidence), json.dumps(learned), u_before,
                    u_after, delta_u, int(bool(constitutional_valid)), now, receipt_hash,
                    json.dumps(metadata or {}, sort_keys=True),
                ),
            )
            cap = max(128, int(max_observations))
            conn.execute(
                """DELETE FROM information_interlock_observations
                   WHERE repo=? AND observation_id IN (
                     SELECT observation_id FROM information_interlock_observations
                     WHERE repo=? ORDER BY created_at DESC LIMIT -1 OFFSET ?
                   )""",
                (repo, repo, cap),
            )
        return {
            "observation_id": observation_id,
            "activation_id": activation_id,
            "receipt_hash": receipt_hash,
            "body_epoch_id": body_epoch_id,
            "inserted_or_present": True,
        }

    def resolve_interlock_outcome(
        self,
        repo: str,
        *,
        activation_id: str,
        outcome_id: str,
        status: str,
        reward: float,
        verification_type: str,
    ) -> dict[str, Any]:
        """Bind independently recorded outcome truth to its E-L observation."""
        row = self.db.execute(
            """SELECT observation_id, receipt_hash
               FROM information_interlock_observations
               WHERE repo=? AND activation_id=?""",
            (repo, activation_id),
        ).fetchone()
        if not row:
            return {"resolved": False, "reason": "observation_missing"}
        verification = str(verification_type).strip().casefold()
        witness_valid = bool(
            verification
            and verification
            not in {"self_report", "unverified", "unknown", "manual_claim"}
        )
        resolved_at = time.time()
        resolution = {
            "observation_id": row["observation_id"],
            "observation_receipt_hash": row["receipt_hash"],
            "outcome_id": outcome_id,
            "status": status,
            "reward": float(reward),
            "verification_type": verification_type,
            "witness_valid": witness_valid,
        }
        canonical = json.dumps(resolution, sort_keys=True, separators=(",", ":"))
        resolution_hash = sha256(canonical.encode("utf-8")).hexdigest()
        self.db.execute(
            """UPDATE information_interlock_observations
               SET outcome_id=?, outcome_status=?, reward=?, witness_valid=?,
                   resolved_at=?, resolution_receipt_hash=?
               WHERE repo=? AND activation_id=?""",
            (
                outcome_id, status, float(reward), int(witness_valid), resolved_at,
                resolution_hash, repo, activation_id,
            ),
        )
        self.db.commit()
        return {
            "resolved": True,
            "observation_id": row["observation_id"],
            "resolution_receipt_hash": resolution_hash,
            "witness_valid": witness_valid,
        }

    def interlock_observations(self, repo: str, limit: int = 2048) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """SELECT * FROM information_interlock_observations
               WHERE repo=? ORDER BY created_at DESC LIMIT ?""",
            (repo, max(1, int(limit))),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["evidence_paths"] = json.loads(item.pop("evidence_paths_json") or "[]")
            item["learned_paths"] = json.loads(item.pop("learned_paths_json") or "[]")
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            item["constitutional_valid"] = bool(item["constitutional_valid"])
            item["witness_valid"] = bool(item["witness_valid"])
            out.append(item)
        return out

    @staticmethod
    def _activation_conformance_canonical_json(value: Any) -> str:
        """Encode strict canonical JSON used by both receipt hash layers."""
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @staticmethod
    def _activation_conformance_is_sha256(value: Any) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    @staticmethod
    def _activation_conformance_ledger_integer(value: Any) -> int | None:
        """Return a SQLite INTEGER without accepting coercible TEXT/BLOB/REAL."""
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value

    @staticmethod
    def _activation_conformance_ledger_real(value: Any) -> float | None:
        """Return one finite SQLite numeric scalar without string coercion."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        try:
            result = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return result if math.isfinite(result) else None

    @classmethod
    def _activation_conformance_admit_body(
        cls, body: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the canonical body and its verifier-bound admission marker.

        A scientific finalizer may propose ``conformance_candidate``, but only
        this transactional append boundary may promote it to Gate B.  Direct
        ``conformance_measured`` claims traverse the identical independent
        validation path.  The import is intentionally local so Store remains
        usable while the OSTT package is importing its persistence surface.
        """

        status = str(body.get("status") or "")
        if status in {"observed", "observed_incomplete"}:
            return body, {
                "schema_version": ACTIVATION_CONFORMANCE_ADMISSION_SCHEMA,
                "admission_status": "observation_only",
                "scientific_status": status,
            }
        if status not in {"conformance_candidate", "conformance_measured"}:
            raise ValueError(
                "activation conformance receipt status is not ledger-admissible"
            )

        from .ostt.independent_verifier import (
            VERIFIER_DIGEST,
            VERIFIER_IMPLEMENTATION_VERSION,
            validate_conformance_payload,
        )

        promoted = dict(body)
        promoted.update(
            {
                "status": "conformance_measured",
                "gate_state": "CONFORMANCE_MEASURED",
                "evidence_ready": True,
                "conformance_ready": True,
            }
        )
        invariant_values = promoted.get("invariant_results")
        if isinstance(invariant_values, list):
            projected_invariants: list[Any] = []
            for value in invariant_values:
                if not isinstance(value, dict):
                    projected_invariants.append(value)
                    continue
                projection = dict(value)
                invariant_id = str(projection.get("invariant_id") or "")
                if invariant_id == "exactly_once_event":
                    projection.update(
                        {
                            "passed": True,
                            "observed": "enforced_by_transactional_ledger",
                            "reason": (
                                "the canonical repository/operator/event identity "
                                "is checked and appended under BEGIN IMMEDIATE"
                            ),
                        }
                    )
                elif invariant_id == "receipt_hash_valid":
                    projection.update(
                        {
                            "passed": True,
                            "observed": "verified_on_ledger_append_and_read",
                            "reason": (
                                "the scientific subject and canonical envelope are "
                                "recomputed at append and verification boundaries"
                            ),
                        }
                    )
                projected_invariants.append(projection)
            promoted["invariant_results"] = projected_invariants
        validation = validate_conformance_payload(promoted)
        if validation.get("valid") is not True:
            errors = validation.get("errors")
            if not isinstance(errors, list):
                errors = ["independent_validator_failed"]
            raise ValueError(
                "activation conformance receipt is not independently valid: "
                + ",".join(sorted({str(error) for error in errors}))
            )

        witness = promoted.get("measurement_witness")
        # Replays of already-admitted bodies must preserve the original
        # admission marker.  Rewriting submitted_status from
        # conformance_candidate → conformance_measured on every append would
        # make exactly-once replay look like different content.
        prior_admission = body.get("ledger_admission")
        if (
            status == "conformance_measured"
            and isinstance(prior_admission, dict)
            and prior_admission.get("admission_status") == "verifier_bound"
            and prior_admission.get("verifier_digest") == VERIFIER_DIGEST
        ):
            marker = dict(prior_admission)
            marker.setdefault("schema_version", ACTIVATION_CONFORMANCE_ADMISSION_SCHEMA)
            marker["scientific_status"] = "conformance_measured"
            marker["measurement_subject_hash"] = str(
                validation.get("measurement_subject_hash")
                or prior_admission.get("measurement_subject_hash")
                or ""
            )
        else:
            marker = {
                "schema_version": ACTIVATION_CONFORMANCE_ADMISSION_SCHEMA,
                "admission_status": "verifier_bound",
                "submitted_status": status,
                "scientific_status": "conformance_measured",
                "verifier_implementation_version": VERIFIER_IMPLEMENTATION_VERSION,
                "verifier_digest": VERIFIER_DIGEST,
                "measurement_subject_hash": str(
                    validation.get("measurement_subject_hash") or ""
                ),
                "measurement_witness_id": (
                    str(witness.get("witness_id") or "")
                    if isinstance(witness, dict)
                    else ""
                ),
            }
        return promoted, marker

    @staticmethod
    def _activation_conformance_required_text(
        receipt_body: dict[str, Any],
        field: str,
        *aliases: str,
    ) -> str:
        values: list[str] = []
        for key in (field, *aliases):
            raw = receipt_body.get(key)
            if raw is None:
                continue
            value = str(raw).strip()
            if value:
                values.append(value)
        if not values:
            raise ValueError(f"activation conformance receipt missing {field}")
        if any(value != values[0] for value in values[1:]):
            raise ValueError(f"activation conformance receipt has conflicting {field}")
        return values[0]

    def _normalize_activation_conformance_body(
        self,
        *,
        repo: str,
        repository_id: str,
        receipt_body: dict[str, Any],
        created_at: float,
    ) -> tuple[dict[str, Any], str, str]:
        """Return normalized scientific content, canonical JSON, and subject hash.

        Ledger linkage fields are deliberately excluded from this subject.  They
        are committed by the final receipt hash after the current partition tip
        is read under ``BEGIN IMMEDIATE``.
        """
        if not isinstance(receipt_body, dict):
            raise TypeError("activation conformance receipt body must be a dict")
        body = dict(receipt_body)
        # Preserve prior admission for idempotent replay of measured bodies.
        # Envelope fields are still stripped from the scientific subject.
        prior_admission = body.get("ledger_admission")
        for key in (
            "receipt_hash",
            "subject_receipt_hash",
            "previous_receipt_hash",
            "chain_sequence",
            "inserted",
            "duplicate",
            "chain_valid",
            "receipt_body",
            "receipt_json",
            "ledger_admission",
        ):
            body.pop(key, None)
        if isinstance(prior_admission, dict):
            body["ledger_admission"] = prior_admission

        claimed_repo = str(body.get("repo") or repo).strip()
        claimed_repository_id = str(body.get("repository_id") or repository_id).strip()
        if claimed_repo != repo:
            raise ValueError("activation conformance receipt repository name mismatch")
        if claimed_repository_id != repository_id:
            raise ValueError("activation conformance receipt repository_id mismatch")

        body_epoch = body.get("body_epoch")
        if isinstance(body_epoch, dict) and body_epoch.get("epoch_id"):
            nested_epoch = str(body_epoch["epoch_id"]).strip()
            direct_epoch = str(
                body.get("body_epoch_id") or body.get("epoch_id") or nested_epoch
            ).strip()
            if direct_epoch != nested_epoch:
                raise ValueError(
                    "activation conformance receipt has conflicting body_epoch_id"
                )
            body.setdefault("body_epoch_id", nested_epoch)
        interlock = body.get("information_interlock")
        if isinstance(interlock, dict) and interlock.get("measurement_cohort_id"):
            nested_cohort = str(interlock["measurement_cohort_id"]).strip()
            direct_cohort = str(
                body.get("measurement_cohort_id")
                or body.get("cohort_id")
                or nested_cohort
            ).strip()
            if direct_cohort != nested_cohort:
                raise ValueError(
                    "activation conformance receipt has conflicting measurement_cohort_id"
                )
            body.setdefault("measurement_cohort_id", nested_cohort)

        operator_id = self._activation_conformance_required_text(body, "operator_id")
        event_id = self._activation_conformance_required_text(body, "event_id")
        case_id = self._activation_conformance_required_text(body, "case_id")
        comparison_arm = self._activation_conformance_required_text(
            body, "comparison_arm"
        )
        body_epoch_id = self._activation_conformance_required_text(
            body, "body_epoch_id", "epoch_id"
        )
        measurement_cohort_id = self._activation_conformance_required_text(
            body, "measurement_cohort_id", "cohort_id"
        )
        coordinate_schema_digest = self._activation_conformance_required_text(
            body, "coordinate_schema_digest"
        )
        status = self._activation_conformance_required_text(body, "status")
        timestamp = float(created_at)
        if timestamp != timestamp or timestamp in (float("inf"), float("-inf")):
            raise ValueError("activation conformance receipt created_at must be finite")

        body.update(
            {
                "ledger_schema_version": ACTIVATION_CONFORMANCE_LEDGER_SCHEMA,
                "repository_id": repository_id,
                "repo": repo,
                "operator_id": operator_id,
                "event_id": event_id,
                "case_id": case_id,
                "comparison_arm": comparison_arm,
                "body_epoch_id": body_epoch_id,
                "measurement_cohort_id": measurement_cohort_id,
                "coordinate_schema_digest": coordinate_schema_digest,
                "status": status,
                "created_at": timestamp,
            }
        )
        body, admission = self._activation_conformance_admit_body(body)
        body["ledger_admission"] = admission
        receipt_json = self._activation_conformance_canonical_json(body)
        normalized = json.loads(receipt_json)
        if not isinstance(normalized, dict):
            raise ValueError("activation conformance receipt body must encode an object")
        subject_hash = sha256(receipt_json.encode("utf-8")).hexdigest()
        return normalized, receipt_json, subject_hash

    @staticmethod
    def _activation_conformance_partition(row: Any) -> dict[str, str]:
        return {
            "repository_id": str(row["repository_id"]),
            "repo": str(row["repo"]),
            "operator_id": str(row["operator_id"]),
            "body_epoch_id": str(row["body_epoch_id"]),
            "measurement_cohort_id": str(row["measurement_cohort_id"]),
            "coordinate_schema_digest": str(row["coordinate_schema_digest"]),
        }

    @classmethod
    def _activation_conformance_final_hash(cls, row: Any) -> str:
        material = {
            "ledger_schema_version": ACTIVATION_CONFORMANCE_LEDGER_SCHEMA,
            "subject_receipt_hash": str(row["subject_receipt_hash"]),
            "previous_receipt_hash": str(row["previous_receipt_hash"]),
            "chain_sequence": int(row["chain_sequence"]),
            "repository_id": str(row["repository_id"]),
            "repo": str(row["repo"]),
            "operator_id": str(row["operator_id"]),
            "event_id": str(row["event_id"]),
            "case_id": str(row["case_id"]),
            "comparison_arm": str(row["comparison_arm"]),
            "body_epoch_id": str(row["body_epoch_id"]),
            "measurement_cohort_id": str(row["measurement_cohort_id"]),
            "coordinate_schema_digest": str(row["coordinate_schema_digest"]),
            "status": str(row["status"]),
            "receipt_json": str(row["receipt_json"]),
            "created_at": float(row["created_at"]),
        }
        canonical = cls._activation_conformance_canonical_json(material)
        return sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode_activation_conformance_row(row: sqlite3.Row) -> dict[str, Any]:
        decode_error: str | None = None
        try:
            receipt_json = row["receipt_json"]
            if not isinstance(receipt_json, str):
                raise TypeError("receipt_json_not_text")
            body = json.loads(receipt_json)
            if not isinstance(body, dict):
                raise ValueError("receipt_json_not_object")
            # JSON permits escaped lone surrogates, while the canonical ledger
            # explicitly requires UTF-8.  Validate that boundary on reads too.
            Store._activation_conformance_canonical_json(body).encode("utf-8")
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
            UnicodeError,
            RecursionError,
            OverflowError,
        ) as exc:
            body = {}
            decode_error = f"{type(exc).__name__}:{exc}"
        chain_sequence = Store._activation_conformance_ledger_integer(
            row["chain_sequence"]
        )
        if chain_sequence is None:
            decode_error = decode_error or "chain_sequence_invalid"
        created_at = Store._activation_conformance_ledger_real(row["created_at"])
        if created_at is None:
            decode_error = decode_error or "created_at_invalid"
        envelope = {
            "ledger_schema_version": ACTIVATION_CONFORMANCE_LEDGER_SCHEMA,
            "receipt_hash": row["receipt_hash"],
            "subject_receipt_hash": row["subject_receipt_hash"],
            "previous_receipt_hash": row["previous_receipt_hash"],
            "chain_sequence": chain_sequence,
            "repository_id": row["repository_id"],
            "repo": row["repo"],
            "operator_id": row["operator_id"],
            "event_id": row["event_id"],
            "case_id": row["case_id"],
            "comparison_arm": row["comparison_arm"],
            "body_epoch_id": row["body_epoch_id"],
            "measurement_cohort_id": row["measurement_cohort_id"],
            "coordinate_schema_digest": row["coordinate_schema_digest"],
            "status": row["status"],
            "created_at": created_at,
            "receipt_json": row["receipt_json"],
        }
        decoded = {**body, **envelope, "receipt_body": body}
        if decode_error:
            decoded["receipt_decode_error"] = decode_error
        return decoded

    def _verify_activation_conformance_partition(
        self,
        conn: sqlite3.Connection,
        partition: dict[str, str],
    ) -> dict[str, Any]:
        args = (
            partition["repository_id"],
            partition["operator_id"],
            partition["body_epoch_id"],
            partition["measurement_cohort_id"],
            partition["coordinate_schema_digest"],
        )
        rows = conn.execute(
            """SELECT * FROM activation_conformance_receipts
               WHERE repository_id=? AND operator_id=? AND body_epoch_id=?
                 AND measurement_cohort_id=? AND coordinate_schema_digest=?
               ORDER BY chain_sequence ASC""",
            args,
        ).fetchall()
        tip = conn.execute(
            """SELECT * FROM activation_conformance_chain_tips
               WHERE repository_id=? AND operator_id=? AND body_epoch_id=?
                 AND measurement_cohort_id=? AND coordinate_schema_digest=?""",
            args,
        ).fetchone()
        errors: list[str] = []
        repo_row = conn.execute(
            "SELECT 1 FROM repositories WHERE name=? AND repository_id=? LIMIT 1",
            (partition["repo"], partition["repository_id"]),
        ).fetchone()
        repository_current = repo_row is not None
        if not repository_current:
            errors.append("repository_identity_not_current")
        if not rows:
            errors.append("receipt_chain_empty")
        if tip is None:
            errors.append("chain_tip_missing")

        previous = ACTIVATION_CONFORMANCE_ZERO_HASH
        seen_events: set[tuple[str, str, str]] = set()
        invalid_receipt_hashes: list[str] = []
        indexed_body_fields = (
            "repository_id",
            "repo",
            "operator_id",
            "event_id",
            "case_id",
            "comparison_arm",
            "body_epoch_id",
            "measurement_cohort_id",
            "coordinate_schema_digest",
            "status",
        )
        for expected_sequence, row in enumerate(rows, start=1):
            receipt_hash = (
                row["receipt_hash"] if isinstance(row["receipt_hash"], str) else ""
            )
            prefix = f"receipt:{receipt_hash or expected_sequence}:"
            errors_before = len(errors)
            if not self._activation_conformance_is_sha256(receipt_hash):
                errors.append(prefix + "receipt_hash_invalid")
            sequence = self._activation_conformance_ledger_integer(
                row["chain_sequence"]
            )
            if sequence is None:
                errors.append(prefix + "chain_sequence_invalid")
            if sequence != expected_sequence:
                errors.append(prefix + "chain_sequence_mismatch")
            previous_receipt_hash = (
                row["previous_receipt_hash"]
                if isinstance(row["previous_receipt_hash"], str)
                else ""
            )
            if not self._activation_conformance_is_sha256(previous_receipt_hash):
                errors.append(prefix + "previous_receipt_hash_invalid")
            if previous_receipt_hash != previous:
                errors.append(prefix + "previous_receipt_hash_mismatch")
            for field in (
                "repository_id",
                "repo",
                "operator_id",
                "body_epoch_id",
                "measurement_cohort_id",
                "coordinate_schema_digest",
            ):
                if not isinstance(row[field], str) or not row[field]:
                    errors.append(prefix + f"partition_field_invalid:{field}")
                if row[field] != partition[field]:
                    errors.append(prefix + f"partition_field_mismatch:{field}")
            try:
                raw_receipt_json = row["receipt_json"]
                if not isinstance(raw_receipt_json, str):
                    raise TypeError("receipt_json_not_text")
                body = json.loads(raw_receipt_json)
                if not isinstance(body, dict):
                    raise ValueError("not_object")
                canonical_body = self._activation_conformance_canonical_json(body)
                canonical_body_bytes = canonical_body.encode("utf-8")
            except (
                TypeError,
                ValueError,
                json.JSONDecodeError,
                UnicodeError,
                RecursionError,
                OverflowError,
            ):
                body = {}
                canonical_body = ""
                canonical_body_bytes = b""
                errors.append(prefix + "receipt_json_invalid")
            if canonical_body and canonical_body != row["receipt_json"]:
                errors.append(prefix + "receipt_json_not_canonical")
            for field in indexed_body_fields:
                body_value = body.get(field)
                if not isinstance(body_value, str) or not body_value:
                    errors.append(prefix + f"body_field_invalid:{field}")
                if body_value != row[field]:
                    errors.append(prefix + f"indexed_field_mismatch:{field}")
            body_created_at = self._activation_conformance_ledger_real(
                body.get("created_at")
            )
            row_created_at = self._activation_conformance_ledger_real(
                row["created_at"]
            )
            if body_created_at is None or row_created_at is None:
                errors.append(prefix + "created_at_invalid")
            elif body_created_at != row_created_at:
                errors.append(prefix + "indexed_field_mismatch:created_at")
            expected_subject = (
                sha256(canonical_body_bytes).hexdigest()
                if canonical_body_bytes
                else ""
            )
            if not self._activation_conformance_is_sha256(
                row["subject_receipt_hash"]
            ):
                errors.append(prefix + "subject_receipt_hash_invalid")
            if expected_subject != str(row["subject_receipt_hash"]):
                errors.append(prefix + "subject_receipt_hash_mismatch")
            try:
                expected_receipt_hash = self._activation_conformance_final_hash(row)
            except (
                TypeError,
                ValueError,
                OverflowError,
                KeyError,
                UnicodeError,
                RecursionError,
            ) as exc:
                expected_receipt_hash = ""
                errors.append(
                    prefix + f"receipt_hash_material_invalid:{type(exc).__name__}"
                )
            if expected_receipt_hash != receipt_hash:
                errors.append(prefix + "receipt_hash_mismatch")
            event_key = (row["repository_id"], row["operator_id"], row["event_id"])
            if event_key in seen_events:
                errors.append(prefix + "duplicate_operator_event")
            seen_events.add(event_key)
            if len(errors) > errors_before:
                invalid_receipt_hashes.append(receipt_hash)
            previous = receipt_hash

        if tip is not None:
            for field in (
                "repository_id",
                "repo",
                "operator_id",
                "body_epoch_id",
                "measurement_cohort_id",
                "coordinate_schema_digest",
            ):
                if not isinstance(tip[field], str) or not tip[field]:
                    errors.append(f"chain_tip_partition_invalid:{field}")
                if tip[field] != partition[field]:
                    errors.append(f"chain_tip_partition_mismatch:{field}")
            tip_count = self._activation_conformance_ledger_integer(
                tip["receipt_count"]
            )
            if tip_count is None:
                errors.append("chain_tip_count_invalid")
            if tip_count != len(rows):
                errors.append("chain_tip_count_mismatch")
            expected_tip = str(rows[-1]["receipt_hash"]) if rows else ""
            tip_receipt_hash = (
                tip["tip_receipt_hash"]
                if isinstance(tip["tip_receipt_hash"], str)
                else ""
            )
            if not self._activation_conformance_is_sha256(tip_receipt_hash):
                errors.append("chain_tip_hash_invalid")
            if tip_receipt_hash != expected_tip:
                errors.append("chain_tip_hash_mismatch")
            tip_updated_at = self._activation_conformance_ledger_real(
                tip["updated_at"]
            )
            if tip_updated_at is None:
                errors.append("chain_tip_updated_at_invalid")
            elif rows:
                expected_updated_at = self._activation_conformance_ledger_real(
                    rows[-1]["created_at"]
                )
                if expected_updated_at is None or tip_updated_at != expected_updated_at:
                    errors.append("chain_tip_updated_at_mismatch")
        return {
            "valid": not errors,
            "chain_valid": not errors,
            "partition": dict(partition),
            "receipt_count": len(rows),
            "tip_receipt_hash": str(tip["tip_receipt_hash"]) if tip else None,
            "repository_current": repository_current,
            "invalid_receipt_hashes": invalid_receipt_hashes,
            "errors": errors,
        }

    def append_activation_conformance_receipt(
        self,
        repo: str,
        receipt_body: dict[str, Any] | None = None,
        *,
        receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one immutable receipt and atomically advance its partition tip.

        Replaying byte-equivalent scientific content for the same
        repository/operator/event returns the existing row with ``duplicate``
        true.  Reusing that identity for different content fails closed.
        """
        if receipt_body is None:
            receipt_body = receipt
        elif receipt is not None:
            raise ValueError("provide receipt_body or receipt, not both")
        if not isinstance(receipt_body, dict):
            raise TypeError("activation conformance receipt body must be a dict")
        operator_id = self._activation_conformance_required_text(
            receipt_body, "operator_id"
        )
        event_id = self._activation_conformance_required_text(receipt_body, "event_id")

        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "").strip()
            if not repository_id:
                raise ValueError("repository_id is required for conformance evidence")

            existing = conn.execute(
                """SELECT * FROM activation_conformance_receipts
                   WHERE repository_id=? AND operator_id=? AND event_id=?""",
                (repository_id, operator_id, event_id),
            ).fetchone()
            created_at = float(existing["created_at"]) if existing else time.time()
            _, receipt_json, subject_hash = self._normalize_activation_conformance_body(
                repo=repo,
                repository_id=repository_id,
                receipt_body=receipt_body,
                created_at=created_at,
            )
            if existing is not None:
                if (
                    str(existing["subject_receipt_hash"]) != subject_hash
                    or str(existing["receipt_json"]) != receipt_json
                ):
                    raise ValueError(
                        "activation conformance operator/event already has different content"
                    )
                partition = self._activation_conformance_partition(existing)
                verification = self._verify_activation_conformance_partition(
                    conn, partition
                )
                if not verification["valid"]:
                    raise RuntimeError(
                        "activation conformance duplicate belongs to an invalid chain: "
                        + ",".join(verification["errors"])
                    )
                result = self._decode_activation_conformance_row(existing)
                result.update(
                    {
                        "inserted": False,
                        "duplicate": True,
                        "chain_valid": True,
                    }
                )
                return result

            normalized = json.loads(receipt_json)
            partition = {
                "repository_id": repository_id,
                "repo": repo,
                "operator_id": str(normalized["operator_id"]),
                "body_epoch_id": str(normalized["body_epoch_id"]),
                "measurement_cohort_id": str(normalized["measurement_cohort_id"]),
                "coordinate_schema_digest": str(
                    normalized["coordinate_schema_digest"]
                ),
            }
            partition_args = tuple(
                partition[field] for field in ACTIVATION_CONFORMANCE_PARTITION_FIELDS
            )
            tip = conn.execute(
                """SELECT * FROM activation_conformance_chain_tips
                   WHERE repository_id=? AND repo=? AND operator_id=? AND body_epoch_id=?
                     AND measurement_cohort_id=? AND coordinate_schema_digest=?""",
                (repository_id, repo, *partition_args[1:]),
            ).fetchone()
            partition_count = int(
                conn.execute(
                    """SELECT COUNT(*) AS n FROM activation_conformance_receipts
                       WHERE repository_id=? AND repo=? AND operator_id=? AND body_epoch_id=?
                         AND measurement_cohort_id=? AND coordinate_schema_digest=?""",
                    (repository_id, repo, *partition_args[1:]),
                ).fetchone()["n"]
            )
            if tip is None and partition_count:
                raise RuntimeError(
                    "activation conformance partition has receipts but no chain tip"
                )
            if tip is not None:
                verification = self._verify_activation_conformance_partition(
                    conn, partition
                )
                if not verification["valid"]:
                    raise RuntimeError(
                        "refusing to extend invalid activation conformance chain: "
                        + ",".join(verification["errors"])
                    )
                previous_hash = str(tip["tip_receipt_hash"])
                chain_sequence = int(tip["receipt_count"]) + 1
            else:
                previous_hash = ACTIVATION_CONFORMANCE_ZERO_HASH
                chain_sequence = 1

            final_material = {
                "subject_receipt_hash": subject_hash,
                "previous_receipt_hash": previous_hash,
                "chain_sequence": chain_sequence,
                "repository_id": repository_id,
                "repo": repo,
                "operator_id": normalized["operator_id"],
                "event_id": normalized["event_id"],
                "case_id": normalized["case_id"],
                "comparison_arm": normalized["comparison_arm"],
                "body_epoch_id": normalized["body_epoch_id"],
                "measurement_cohort_id": normalized["measurement_cohort_id"],
                "coordinate_schema_digest": normalized["coordinate_schema_digest"],
                "status": normalized["status"],
                "receipt_json": receipt_json,
                "created_at": created_at,
            }
            receipt_hash = self._activation_conformance_final_hash(final_material)
            conn.execute(
                """INSERT INTO activation_conformance_receipts(
                       receipt_hash, subject_receipt_hash, previous_receipt_hash,
                       chain_sequence, repository_id, repo, operator_id, event_id,
                       case_id, comparison_arm, body_epoch_id, measurement_cohort_id,
                       coordinate_schema_digest, status, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    subject_hash,
                    previous_hash,
                    chain_sequence,
                    repository_id,
                    repo,
                    normalized["operator_id"],
                    normalized["event_id"],
                    normalized["case_id"],
                    normalized["comparison_arm"],
                    normalized["body_epoch_id"],
                    normalized["measurement_cohort_id"],
                    normalized["coordinate_schema_digest"],
                    normalized["status"],
                    receipt_json,
                    created_at,
                ),
            )
            if tip is None:
                conn.execute(
                    """INSERT INTO activation_conformance_chain_tips(
                           repository_id, repo, operator_id, body_epoch_id,
                           measurement_cohort_id, coordinate_schema_digest,
                           tip_receipt_hash, receipt_count, updated_at
                       ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        repository_id,
                        repo,
                        normalized["operator_id"],
                        normalized["body_epoch_id"],
                        normalized["measurement_cohort_id"],
                        normalized["coordinate_schema_digest"],
                        receipt_hash,
                        chain_sequence,
                        created_at,
                    ),
                )
            else:
                cursor = conn.execute(
                    """UPDATE activation_conformance_chain_tips
                       SET tip_receipt_hash=?, receipt_count=?, updated_at=?
                       WHERE repository_id=? AND repo=? AND operator_id=? AND body_epoch_id=?
                         AND measurement_cohort_id=? AND coordinate_schema_digest=?
                         AND tip_receipt_hash=? AND receipt_count=?""",
                    (
                        receipt_hash,
                        chain_sequence,
                        created_at,
                        repository_id,
                        repo,
                        *partition_args[1:],
                        previous_hash,
                        chain_sequence - 1,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "activation conformance chain tip changed during append"
                    )

            verification = self._verify_activation_conformance_partition(conn, partition)
            if not verification["valid"]:
                raise RuntimeError(
                    "activation conformance append failed verification: "
                    + ",".join(verification["errors"])
                )
            row = conn.execute(
                "SELECT * FROM activation_conformance_receipts WHERE receipt_hash=?",
                (receipt_hash,),
            ).fetchone()
            if row is None:
                raise RuntimeError("activation conformance append was not persisted")
            result = self._decode_activation_conformance_row(row)
            result.update(
                {"inserted": True, "duplicate": False, "chain_valid": True}
            )
            return result

    def activation_conformance_receipt(
        self, receipt_hash: str, *, repo: str | None = None
    ) -> dict[str, Any] | None:
        if repo is None:
            row = self.db.execute(
                "SELECT * FROM activation_conformance_receipts WHERE receipt_hash=?",
                (str(receipt_hash),),
            ).fetchone()
        else:
            repository = self.db.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                return None
            row = self.db.execute(
                """SELECT * FROM activation_conformance_receipts
                   WHERE receipt_hash=? AND repository_id=? AND repo=?""",
                (str(receipt_hash), str(repository["repository_id"]), str(repo)),
            ).fetchone()
        return self._decode_activation_conformance_row(row) if row else None

    def get_activation_conformance_receipt(
        self, receipt_hash: str, *, repo: str | None = None
    ) -> dict[str, Any] | None:
        return self.activation_conformance_receipt(receipt_hash, repo=repo)

    def activation_conformance_receipts(
        self,
        repo: str,
        *,
        operator_id: str | None = None,
        event_id: str | None = None,
        case_id: str | None = None,
        comparison_arm: str | None = None,
        body_epoch_id: str | None = None,
        measurement_cohort_id: str | None = None,
        coordinate_schema_digest: str | None = None,
        status: str | None = None,
        limit: int = 128,
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        clauses = ["repository_id=?", "repo=?"]
        args: list[Any] = [str(repository["repository_id"]), str(repo)]
        for field, value in (
            ("operator_id", operator_id),
            ("event_id", event_id),
            ("case_id", case_id),
            ("comparison_arm", comparison_arm),
            ("body_epoch_id", body_epoch_id),
            ("measurement_cohort_id", measurement_cohort_id),
            ("coordinate_schema_digest", coordinate_schema_digest),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{field}=?")
                args.append(str(value))
        bounded_limit = max(1, min(4096, int(limit)))
        args.append(bounded_limit)
        rows = self.db.execute(
            "SELECT * FROM activation_conformance_receipts WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC, receipt_hash DESC LIMIT ?",
            tuple(args),
        ).fetchall()
        return [self._decode_activation_conformance_row(row) for row in rows]

    def latest_activation_conformance_receipt(
        self,
        repo: str,
        *,
        operator_id: str | None = None,
        body_epoch_id: str | None = None,
        measurement_cohort_id: str | None = None,
        coordinate_schema_digest: str | None = None,
    ) -> dict[str, Any] | None:
        rows = self.activation_conformance_receipts(
            repo,
            operator_id=operator_id,
            body_epoch_id=body_epoch_id,
            measurement_cohort_id=measurement_cohort_id,
            coordinate_schema_digest=coordinate_schema_digest,
            limit=1,
        )
        return rows[0] if rows else None

    def verify_activation_conformance_chain(
        self,
        repo: str,
        operator_id: str,
        body_epoch_id: str,
        measurement_cohort_id: str,
        coordinate_schema_digest: str,
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            current = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if current is None:
                return {
                    "valid": False,
                    "chain_valid": False,
                    "partition": {
                        "repository_id": "",
                        "repo": str(repo),
                        "operator_id": str(operator_id),
                        "body_epoch_id": str(body_epoch_id),
                        "measurement_cohort_id": str(measurement_cohort_id),
                        "coordinate_schema_digest": str(coordinate_schema_digest),
                    },
                    "receipt_count": 0,
                    "tip_receipt_hash": None,
                    "repository_current": False,
                    "invalid_receipt_hashes": [],
                    "errors": ["repository_missing"],
                }
            repository_id = str(current["repository_id"])
            partition = {
                "repository_id": repository_id,
                "repo": str(repo),
                "operator_id": str(operator_id),
                "body_epoch_id": str(body_epoch_id),
                "measurement_cohort_id": str(measurement_cohort_id),
                "coordinate_schema_digest": str(coordinate_schema_digest),
            }
            return self._verify_activation_conformance_partition(conn, partition)

    def verify_all_activation_conformance_chains(
        self, repo: str | None = None
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            if repo is not None:
                repository = conn.execute(
                    "SELECT repository_id FROM repositories WHERE name=?", (repo,)
                ).fetchone()
                if repository is None:
                    return {
                        "valid": False,
                        "chain_valid": False,
                        "repo": repo,
                        "chain_count": 0,
                        "valid_chain_count": 0,
                        "invalid_chain_count": 0,
                        "receipt_count": 0,
                        "partitions": [],
                        "invalid_receipt_hashes": [],
                        "errors": ["repository_missing"],
                    }
                args: tuple[Any, ...] = (str(repository["repository_id"]), str(repo))
                where = " WHERE repository_id=? AND repo=?"
            else:
                args = ()
                where = ""
            tips = conn.execute(
                """SELECT repository_id, repo, operator_id, body_epoch_id,
                          measurement_cohort_id, coordinate_schema_digest
                   FROM activation_conformance_chain_tips"""
                + where,
                args,
            ).fetchall()
            receipts = conn.execute(
                """SELECT DISTINCT repository_id, repo, operator_id, body_epoch_id,
                          measurement_cohort_id, coordinate_schema_digest
                   FROM activation_conformance_receipts"""
                + where,
                args,
            ).fetchall()
            partitions: dict[tuple[str, ...], dict[str, str]] = {}
            for row in [*tips, *receipts]:
                partition = self._activation_conformance_partition(row)
                key = (
                    partition["repo"],
                    *(
                        partition[field]
                        for field in ACTIVATION_CONFORMANCE_PARTITION_FIELDS
                    ),
                )
                partitions[key] = partition
            reports = [
                self._verify_activation_conformance_partition(conn, partition)
                for _, partition in sorted(partitions.items())
            ]
            errors = [
                error
                for report in reports
                for error in report.get("errors", [])
            ]
            valid_count = sum(1 for report in reports if report["valid"])
            invalid_receipt_hashes = sorted(
                {
                    receipt_hash
                    for report in reports
                    for receipt_hash in report.get("invalid_receipt_hashes", [])
                }
            )
            return {
                "valid": not errors,
                "chain_valid": not errors,
                "repo": repo,
                "chain_count": len(reports),
                "valid_chain_count": valid_count,
                "invalid_chain_count": len(reports) - valid_count,
                "receipt_count": sum(
                    int(report["receipt_count"]) for report in reports
                ),
                "partitions": reports,
                "invalid_receipt_hashes": invalid_receipt_hashes,
                "errors": errors,
            }

    # ------------------------------------------------------------------
    # v8.4.1 symbiotic circulation ledger
    # ------------------------------------------------------------------

    SYMBIOTIC_ZERO_HASH = "0" * 64
    SYMBIOTIC_LEDGER_SCHEMA = "cortex-symbiotic-circulation-ledger/1.1"

    @staticmethod
    def _symbiotic_canonical_json(body: dict[str, Any]) -> str:
        return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)

    def _decode_symbiotic_row(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            body = json.loads(row["receipt_json"])
            if not isinstance(body, dict):
                body = {}
        except (TypeError, ValueError, json.JSONDecodeError):
            body = {}
        keys = row.keys()
        turn_id = int(row["turn_id"]) if "turn_id" in keys else int(body.get("turn_id") or 0)
        event_id = (
            str(row["event_id"])
            if "event_id" in keys
            else str(body.get("event_id") or "")
        )
        return {
            **body,
            "receipt_hash": row["receipt_hash"],
            "subject_receipt_hash": row["subject_receipt_hash"],
            "previous_receipt_hash": row["previous_receipt_hash"],
            "chain_sequence": int(row["chain_sequence"]),
            "repository_id": row["repository_id"],
            "repo": row["repo"],
            "session_id": row["session_id"],
            "turn_id": turn_id,
            "event_id": event_id,
            "body_epoch_id": row["body_epoch_id"],
            "kind": row["kind"],
            "status": row["status"],
            "created_at": float(row["created_at"]),
            "ledger_schema_version": self.SYMBIOTIC_LEDGER_SCHEMA,
        }

    def append_symbiotic_receipt(
        self,
        repo: str,
        receipt_body: dict[str, Any],
    ) -> dict[str, Any]:
        """Append one immutable symbiotic receipt and advance the session tip.

        Exactly-once identity is ``(repository_id, session_id, turn_id, kind)``.
        Replaying byte-equivalent content returns the existing row; different
        content fails closed.
        """
        if not isinstance(receipt_body, dict):
            raise TypeError("symbiotic receipt body must be a dict")
        kind = str(receipt_body.get("kind") or "").strip()
        session_id = str(receipt_body.get("session_id") or "").strip()
        body_epoch_id = str(receipt_body.get("body_epoch_id") or "").strip()
        try:
            turn_id = int(receipt_body.get("turn_id", 0))
        except (TypeError, ValueError):
            turn_id = 0
        event_id = str(receipt_body.get("event_id") or "").strip()
        if not kind or not session_id or not body_epoch_id:
            raise ValueError("symbiotic receipt requires kind, session_id, body_epoch_id")
        if not event_id:
            raise ValueError("symbiotic receipt requires immutable event_id")

        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "").strip()
            if not repository_id:
                raise ValueError("repository_id is required for symbiotic evidence")

            body = dict(receipt_body)
            for key in (
                "receipt_hash",
                "subject_receipt_hash",
                "previous_receipt_hash",
                "chain_sequence",
                "inserted",
                "duplicate",
                "chain_valid",
                "ledger_schema_version",
            ):
                body.pop(key, None)
            body.update(
                {
                    "repository_id": repository_id,
                    "repo": repo,
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "event_id": event_id,
                    "body_epoch_id": body_epoch_id,
                    "kind": kind,
                    "status": str(body.get("status") or kind),
                }
            )
            # Scientific subject excludes ledger linkage.
            subject_material = {
                key: value
                for key, value in body.items()
                if key
                not in {
                    "created_at",
                    "previous_receipt_hash",
                    "chain_sequence",
                    "ledger_schema_version",
                }
            }
            subject_json = self._symbiotic_canonical_json(subject_material)
            subject_hash = sha256(subject_json.encode("utf-8")).hexdigest()
            existing = conn.execute(
                """SELECT * FROM symbiotic_circulation_receipts
                   WHERE repository_id=? AND session_id=? AND turn_id=? AND kind=?""",
                (repository_id, session_id, turn_id, kind),
            ).fetchone()
            created_at = float(existing["created_at"]) if existing else time.time()
            body["created_at"] = created_at
            receipt_json = self._symbiotic_canonical_json(body)

            if existing is not None:
                if (
                    str(existing["subject_receipt_hash"]) != subject_hash
                    or str(existing["receipt_json"]) != receipt_json
                ):
                    raise ValueError(
                        "symbiotic receipt kind already has different content "
                        f"for session {session_id} turn {turn_id}"
                    )
                decoded = self._decode_symbiotic_row(existing)
                decoded.update({"inserted": False, "duplicate": True, "chain_valid": True})
                return decoded

            tip = conn.execute(
                """SELECT * FROM symbiotic_circulation_chain_tips
                   WHERE repository_id=? AND session_id=?""",
                (repository_id, session_id),
            ).fetchone()
            if tip is None:
                previous_hash = self.SYMBIOTIC_ZERO_HASH
                chain_sequence = 1
            else:
                previous_hash = str(tip["tip_receipt_hash"])
                chain_sequence = int(tip["receipt_count"]) + 1

            final_material = {
                "subject_receipt_hash": subject_hash,
                "previous_receipt_hash": previous_hash,
                "chain_sequence": chain_sequence,
                "repository_id": repository_id,
                "repo": repo,
                "session_id": session_id,
                "body_epoch_id": body_epoch_id,
                "kind": kind,
                "status": body["status"],
                "receipt_json": receipt_json,
                "created_at": created_at,
            }
            receipt_hash = sha256(
                self._symbiotic_canonical_json(final_material).encode("utf-8")
            ).hexdigest()
            conn.execute(
                """INSERT INTO symbiotic_circulation_receipts(
                       receipt_hash, subject_receipt_hash, previous_receipt_hash,
                       chain_sequence, repository_id, repo, session_id, turn_id,
                       event_id, body_epoch_id, kind, status, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    subject_hash,
                    previous_hash,
                    chain_sequence,
                    repository_id,
                    repo,
                    session_id,
                    turn_id,
                    event_id,
                    body_epoch_id,
                    kind,
                    body["status"],
                    receipt_json,
                    created_at,
                ),
            )
            if tip is None:
                conn.execute(
                    """INSERT INTO symbiotic_circulation_chain_tips(
                           repository_id, repo, session_id, body_epoch_id,
                           tip_receipt_hash, receipt_count, updated_at
                       ) VALUES(?, ?, ?, ?, ?, ?, ?)""",
                    (
                        repository_id,
                        repo,
                        session_id,
                        body_epoch_id,
                        receipt_hash,
                        chain_sequence,
                        created_at,
                    ),
                )
            else:
                cursor = conn.execute(
                    """UPDATE symbiotic_circulation_chain_tips
                       SET tip_receipt_hash=?, receipt_count=?, updated_at=?, body_epoch_id=?
                       WHERE repository_id=? AND session_id=?
                         AND tip_receipt_hash=? AND receipt_count=?""",
                    (
                        receipt_hash,
                        chain_sequence,
                        created_at,
                        body_epoch_id,
                        repository_id,
                        session_id,
                        previous_hash,
                        chain_sequence - 1,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("symbiotic chain tip changed during append")

            verification = self._verify_symbiotic_session_conn(
                conn, repository_id, repo, session_id
            )
            if not verification["valid"]:
                raise RuntimeError(
                    "symbiotic append failed verification: "
                    + ",".join(verification["errors"])
                )
            row = conn.execute(
                "SELECT * FROM symbiotic_circulation_receipts WHERE receipt_hash=?",
                (receipt_hash,),
            ).fetchone()
            if row is None:
                raise RuntimeError("symbiotic receipt append was not persisted")
            result = self._decode_symbiotic_row(row)
            result.update({"inserted": True, "duplicate": False, "chain_valid": True})
            return result

    def symbiotic_receipt(
        self, receipt_hash: str, *, repo: str | None = None
    ) -> dict[str, Any] | None:
        if repo is None:
            row = self.db.execute(
                "SELECT * FROM symbiotic_circulation_receipts WHERE receipt_hash=?",
                (str(receipt_hash),),
            ).fetchone()
        else:
            repository = self.db.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                return None
            row = self.db.execute(
                """SELECT * FROM symbiotic_circulation_receipts
                   WHERE receipt_hash=? AND repository_id=? AND repo=?""",
                (str(receipt_hash), str(repository["repository_id"]), str(repo)),
            ).fetchone()
        return self._decode_symbiotic_row(row) if row else None

    def symbiotic_session_receipts(
        self, repo: str, session_id: str
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        rows = self.db.execute(
            """SELECT * FROM symbiotic_circulation_receipts
               WHERE repository_id=? AND repo=? AND session_id=?
               ORDER BY chain_sequence ASC""",
            (str(repository["repository_id"]), str(repo), str(session_id)),
        ).fetchall()
        return [self._decode_symbiotic_row(row) for row in rows]

    def symbiotic_receipts_by_kind(
        self, repo: str, kind: str, *, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Read immutable receipts of one canonical kind, newest first."""

        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        rows = self.db.execute(
            """SELECT * FROM symbiotic_circulation_receipts
               WHERE repository_id=? AND repo=? AND kind=?
               ORDER BY created_at DESC, receipt_hash DESC LIMIT ?""",
            (
                str(repository["repository_id"]),
                str(repo),
                str(kind),
                max(1, min(int(limit), 10_000)),
            ),
        ).fetchall()
        return [self._decode_symbiotic_row(row) for row in rows]

    def append_interconnect_frame(
        self, repo: str, frame: dict[str, Any]
    ) -> dict[str, Any]:
        """Append one immutable interconnect frame (exactly-once per session/turn)."""
        if not isinstance(frame, dict):
            raise TypeError("interconnect frame must be a dict")
        session_id = str(frame.get("session_id") or "").strip()
        try:
            turn_id = int(frame.get("turn_id", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("interconnect frame requires turn_id") from exc
        receipt_hash = str(frame.get("receipt_hash") or "").strip()
        event_id = str(frame.get("event_id") or "").strip()
        frame_id = str(frame.get("frame_id") or "").strip()
        body_epoch_id = str(frame.get("body_epoch_id") or "").strip()
        if not all([session_id, receipt_hash, event_id, frame_id, body_epoch_id]):
            raise ValueError("interconnect frame missing required identity fields")
        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "")
            existing = conn.execute(
                """SELECT * FROM interconnect_frames
                   WHERE repository_id=? AND session_id=? AND turn_id=?""",
                (repository_id, session_id, turn_id),
            ).fetchone()
            receipt_json = self._symbiotic_canonical_json(frame)
            created_at = float(frame.get("captured_at") or time.time())
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError(
                        "interconnect frame turn already has different content"
                    )
                return {**frame, "inserted": False, "duplicate": True}
            overall = str(
                (frame.get("validity") or {}).get("overall_state") or "unknown"
            )
            conn.execute(
                """INSERT INTO interconnect_frames(
                       receipt_hash, repository_id, repo, session_id, turn_id,
                       body_epoch_id, frame_id, event_id, overall_state,
                       receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    session_id,
                    turn_id,
                    body_epoch_id,
                    frame_id,
                    event_id,
                    overall,
                    receipt_json,
                    created_at,
                ),
            )
            tip = conn.execute(
                """SELECT * FROM interconnect_trajectory_tips
                   WHERE repository_id=? AND session_id=?""",
                (repository_id, session_id),
            ).fetchone()
            if tip is None:
                conn.execute(
                    """INSERT INTO interconnect_trajectory_tips(
                           repository_id, repo, session_id, tip_frame_hash,
                           tip_transition_hash, frame_count, transition_count,
                           updated_at
                       ) VALUES(?, ?, ?, ?, NULL, 1, 0, ?)""",
                    (repository_id, repo, session_id, receipt_hash, created_at),
                )
            else:
                conn.execute(
                    """UPDATE interconnect_trajectory_tips
                       SET tip_frame_hash=?, frame_count=frame_count+1, updated_at=?
                       WHERE repository_id=? AND session_id=?""",
                    (receipt_hash, created_at, repository_id, session_id),
                )
            return {**frame, "inserted": True, "duplicate": False}

    def append_interconnect_transition(
        self, repo: str, transition: dict[str, Any]
    ) -> dict[str, Any]:
        """Append one immutable frame transition (exactly-once prior→next)."""
        if not isinstance(transition, dict):
            raise TypeError("interconnect transition must be a dict")
        prior_h = str(transition.get("prior_frame_hash") or "").strip()
        next_h = str(transition.get("next_frame_hash") or "").strip()
        receipt_hash = str(transition.get("receipt_hash") or "").strip()
        event_id = str(transition.get("event_id") or "").strip()
        session_id = str(transition.get("session_id") or "").strip()
        if not all([prior_h, next_h, receipt_hash, event_id, session_id]):
            raise ValueError("interconnect transition missing required fields")
        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "")
            existing = conn.execute(
                """SELECT * FROM interconnect_transitions
                   WHERE prior_frame_hash=? AND next_frame_hash=?""",
                (prior_h, next_h),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError(
                        "interconnect transition already has different content"
                    )
                return {**transition, "inserted": False, "duplicate": True}
            created_at = float(transition.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO interconnect_transitions(
                       receipt_hash, repository_id, repo, session_id, turn_id,
                       prior_frame_hash, next_frame_hash, outcome_hash,
                       transition_class, causal_status, event_id, receipt_json,
                       created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    session_id,
                    int(transition.get("turn_id") or 0),
                    prior_h,
                    next_h,
                    transition.get("outcome_hash"),
                    str(transition.get("transition_class") or "unknown_transition"),
                    str(transition.get("causal_status") or "unmeasured"),
                    event_id,
                    self._symbiotic_canonical_json(transition),
                    created_at,
                ),
            )
            conn.execute(
                """UPDATE interconnect_trajectory_tips
                   SET tip_transition_hash=?, transition_count=transition_count+1,
                       updated_at=?
                   WHERE repository_id=? AND session_id=?""",
                (receipt_hash, created_at, repository_id, session_id),
            )
            return {**transition, "inserted": True, "duplicate": False}

    def interconnect_session_frames(
        self, repo: str, session_id: str
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        rows = self.db.execute(
            """SELECT receipt_json FROM interconnect_frames
               WHERE repository_id=? AND repo=? AND session_id=?
               ORDER BY turn_id ASC""",
            (str(repository["repository_id"]), repo, session_id),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                out.append(json.loads(row["receipt_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return out

    def interconnect_session_transitions(
        self, repo: str, session_id: str
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        rows = self.db.execute(
            """SELECT receipt_json FROM interconnect_transitions
               WHERE repository_id=? AND repo=? AND session_id=?
               ORDER BY turn_id ASC""",
            (str(repository["repository_id"]), repo, session_id),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                out.append(json.loads(row["receipt_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return out

    def append_distillation_candidate_batch(
        self, repo: str, batch: dict[str, Any]
    ) -> dict[str, Any]:
        """Append one immutable distillation candidate batch (exactly-once per turn)."""
        if not isinstance(batch, dict):
            raise TypeError("distillation candidate batch must be a dict")
        session_id = str(batch.get("session_id") or "").strip()
        try:
            turn_id = int(batch.get("turn_id", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("distillation candidate batch requires turn_id") from exc
        receipt_hash = str(batch.get("receipt_hash") or "").strip()
        event_id = str(batch.get("event_id") or "").strip()
        if not all([session_id, receipt_hash, event_id]):
            raise ValueError("distillation candidate batch missing required fields")
        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "")
            existing = conn.execute(
                """SELECT * FROM distillation_candidate_batches
                   WHERE repository_id=? AND session_id=? AND turn_id=?""",
                (repository_id, session_id, turn_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError(
                        "distillation candidate turn already has different content"
                    )
                return {**batch, "inserted": False, "duplicate": True}
            source = dict(batch.get("source") or {})
            created_at = float(batch.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO distillation_candidate_batches(
                       receipt_hash, repository_id, repo, session_id, turn_id,
                       transition_hash, prior_frame_hash, next_frame_hash,
                       extraction_status, candidate_count, event_id,
                       receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    session_id,
                    turn_id,
                    source.get("transition_hash"),
                    source.get("prior_frame_hash"),
                    source.get("next_frame_hash"),
                    str(batch.get("extraction_status") or "empty"),
                    int(batch.get("candidate_count") or 0),
                    event_id,
                    self._symbiotic_canonical_json(batch),
                    created_at,
                ),
            )
            return {**batch, "inserted": True, "duplicate": False}

    def distillation_session_candidates(
        self, repo: str, session_id: str
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        rows = self.db.execute(
            """SELECT receipt_json FROM distillation_candidate_batches
               WHERE repository_id=? AND repo=? AND session_id=?
               ORDER BY turn_id ASC""",
            (str(repository["repository_id"]), repo, session_id),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                out.append(json.loads(row["receipt_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return out

    def get_distillation_candidate_batch_by_hash(
        self, repo: str, receipt_hash: str
    ) -> dict[str, Any] | None:
        """Resolve one candidate batch without crossing repository identity."""
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return None
        row = self.db.execute(
            """SELECT receipt_json FROM distillation_candidate_batches
               WHERE repository_id=? AND repo=? AND receipt_hash=?""",
            (str(repository["repository_id"] or ""), repo, str(receipt_hash)),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["receipt_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    # v9.1 transferable competence is deliberately separate from admitted
    # memory.  These wrappers keep the canonical ledger behind Store while the
    # architecture-native verifier remains in cortex.competence.
    def append_competence_candidate(
        self, repo: str, candidate: Mapping[str, Any]
    ) -> dict[str, Any]:
        from .competence import append_competence_candidate

        return append_competence_candidate(self, repo, candidate)

    def get_competence_candidate(
        self, repo: str, competence_id: str
    ) -> dict[str, Any] | None:
        from .competence import get_competence_candidate

        return get_competence_candidate(self, repo, competence_id)

    def list_competence_candidates(self, repo: str) -> list[dict[str, Any]]:
        from .competence import list_competence_candidates

        return list_competence_candidates(self, repo)

    def append_transfer_trial(
        self, repo: str, trial: Mapping[str, Any]
    ) -> dict[str, Any]:
        from .competence_transfer import append_transfer_trial

        return append_transfer_trial(self, repo, trial)

    def get_transfer_trial(self, repo: str, trial_id: str) -> dict[str, Any] | None:
        from .competence_transfer import get_transfer_trial

        return get_transfer_trial(self, repo, trial_id)

    def list_transfer_trials(self, repo: str) -> list[dict[str, Any]]:
        from .competence_transfer import list_transfer_trials

        return list_transfer_trials(self, repo)

    # v9.3 governed competence distribution remains a consumer projection over
    # the immutable competence/transfer ledgers.  Store exposes the fabric
    # without making consumers a second authority surface.
    def register_target_profile(
        self, repo: str, profile: Mapping[str, Any]
    ) -> dict[str, Any]:
        from .competence_distribution import register_target_profile

        return register_target_profile(self, repo, profile)

    def get_target_profile(self, repo: str, profile_id: str) -> dict[str, Any] | None:
        from .competence_distribution import get_target_profile

        return get_target_profile(self, repo, profile_id)

    def list_target_profiles(
        self, repo: str, target_id: str | None = None
    ) -> list[dict[str, Any]]:
        from .competence_distribution import list_target_profiles

        return list_target_profiles(self, repo, target_id)

    def project_competence(
        self,
        repo: str,
        *,
        competence_id: str,
        profile_id: str,
        previous_package_id: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        from .competence_distribution import project_competence

        return project_competence(
            self,
            repo,
            competence_id=competence_id,
            profile_id=profile_id,
            previous_package_id=previous_package_id,
            persist=persist,
        )

    def verify_distribution_package(
        self, repo: str, package_id: str
    ) -> dict[str, Any]:
        from .competence_distribution import verify_distribution_package

        return verify_distribution_package(self, repo, package_id)

    def list_distribution_packages(
        self, repo: str, target_id: str | None = None
    ) -> list[dict[str, Any]]:
        from .competence_distribution import list_distribution_packages

        return list_distribution_packages(self, repo, target_id)

    def append_distribution_event(
        self,
        repo: str,
        *,
        package_id: str,
        event_type: str,
        reason: str,
        replacement_package_id: str | None = None,
        scope: str = "target",
    ) -> dict[str, Any]:
        from .competence_distribution import append_distribution_event

        return append_distribution_event(
            self,
            repo,
            package_id=package_id,
            event_type=event_type,
            reason=reason,
            replacement_package_id=replacement_package_id,
            scope=scope,
        )

    def submit_distribution_feedback(
        self,
        repo: str,
        *,
        package_id: str,
        kind: str,
        context: Mapping[str, Any] | None = None,
        result: Mapping[str, Any] | None = None,
        outcome: Mapping[str, Any] | None = None,
        evidence: Mapping[str, Any] | None = None,
        package_use_receipt_hash: str | None = None,
        circulation_session_id: str | None = None,
        turn_id: int = 1,
    ) -> dict[str, Any]:
        from .competence_distribution import submit_distribution_feedback

        return submit_distribution_feedback(
            self,
            repo,
            package_id=package_id,
            kind=kind,
            context=context,
            result=result,
            outcome=outcome,
            evidence=evidence,
            package_use_receipt_hash=package_use_receipt_hash,
            circulation_session_id=circulation_session_id,
            turn_id=turn_id,
        )

    def list_distribution_feedback(
        self, repo: str, package_id: str | None = None
    ) -> list[dict[str, Any]]:
        from .competence_distribution import list_distribution_feedback

        return list_distribution_feedback(self, repo, package_id)

    def verify_package_use(
        self,
        repo: str,
        package_use_receipt_hash: str,
        *,
        expected_package_id: str | None = None,
    ) -> dict[str, Any]:
        from .competence_distribution import verify_package_use

        return verify_package_use(
            self,
            repo,
            package_use_receipt_hash,
            expected_package_id=expected_package_id,
        )

    def verify_distribution_feedback(
        self, repo: str, feedback_id: str
    ) -> dict[str, Any]:
        from .competence_distribution import verify_distribution_feedback

        return verify_distribution_feedback(self, repo, feedback_id)

    # v9.5 freezes exact v9.4 package-use observations before interpretation.
    # Analysis and verification are observational by default; only explicit
    # ``persist=True`` calls append cohort, analysis, or verification evidence.
    def freeze_evidence_cohort(
        self,
        repo: str,
        *,
        competence_id: str,
        feedback_ids: Sequence[str] | None = None,
        selection_policy: Mapping[str, Any] | None = None,
        analysis_policy: Mapping[str, Any] | None = None,
        evidence_cutoff: float | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        from .competence_assimilation import freeze_evidence_cohort

        return freeze_evidence_cohort(
            self,
            repo,
            competence_id=competence_id,
            feedback_ids=feedback_ids,
            selection_policy=selection_policy,
            analysis_policy=analysis_policy,
            evidence_cutoff=evidence_cutoff,
            persist=persist,
        )

    def get_evidence_cohort(
        self, repo: str, cohort_id: str
    ) -> dict[str, Any] | None:
        from .competence_assimilation import get_evidence_cohort

        return get_evidence_cohort(self, repo, cohort_id)

    def verify_evidence_cohort(
        self, repo: str, cohort_id: str
    ) -> dict[str, Any]:
        from .competence_assimilation import verify_evidence_cohort

        return verify_evidence_cohort(self, repo, cohort_id)

    def analyze_evidence_cohort(
        self, repo: str, cohort_id: str, *, persist: bool = False
    ) -> dict[str, Any]:
        from .competence_assimilation import analyze_evidence_cohort

        return analyze_evidence_cohort(self, repo, cohort_id, persist=persist)

    def get_assimilation_analysis(
        self, repo: str, analysis_id: str
    ) -> dict[str, Any] | None:
        from .competence_assimilation import get_assimilation_analysis

        return get_assimilation_analysis(self, repo, analysis_id)

    def verify_assimilation_analysis(
        self, repo: str, analysis_id: str
    ) -> dict[str, Any]:
        from .competence_assimilation import verify_assimilation_analysis

        return verify_assimilation_analysis(self, repo, analysis_id)

    def build_revision_candidate(
        self,
        repo: str,
        *,
        analysis_id: str,
        public_rationale: str = "",
        persist: bool = False,
    ) -> dict[str, Any]:
        from .competence_revision import build_revision_candidate

        return build_revision_candidate(
            self,
            repo,
            analysis_id=analysis_id,
            public_rationale=public_rationale,
            persist=persist,
        )

    def get_revision_candidate(
        self, repo: str, revision_candidate_id: str
    ) -> dict[str, Any] | None:
        from .competence_revision import get_revision_candidate

        return get_revision_candidate(self, repo, revision_candidate_id)

    def verify_revision_candidate(
        self,
        repo: str,
        revision_candidate_id: str,
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        from .competence_revision import verify_revision_candidate

        return verify_revision_candidate(
            self,
            repo,
            revision_candidate_id,
            persist=persist,
        )

    def get_revision_verification(
        self, repo: str, verification_receipt_hash: str
    ) -> dict[str, Any] | None:
        from .competence_revision import get_revision_verification

        return get_revision_verification(self, repo, verification_receipt_hash)

    def promote_revision_candidate(
        self,
        repo: str,
        revision_candidate_id: str,
        *,
        verification_receipt_hash: str,
        promotion_reason: str,
        persist: bool = False,
    ) -> dict[str, Any]:
        from .competence_revision import promote_revision_candidate

        return promote_revision_candidate(
            self,
            repo,
            revision_candidate_id,
            verification_receipt_hash=verification_receipt_hash,
            promotion_reason=promotion_reason,
            persist=persist,
        )

    def get_revision_promotion(
        self, repo: str, promotion_receipt_hash: str
    ) -> dict[str, Any] | None:
        from .competence_revision import get_revision_promotion

        return get_revision_promotion(self, repo, promotion_receipt_hash)

    def verify_revision_promotion(
        self, repo: str, promotion_receipt_hash: str
    ) -> dict[str, Any]:
        from .competence_revision import verify_revision_promotion

        return verify_revision_promotion(self, repo, promotion_receipt_hash)

    def list_revision_promotions(
        self, repo: str, source_competence_id: str | None = None
    ) -> list[dict[str, Any]]:
        from .competence_revision import list_revision_promotions

        return list_revision_promotions(self, repo, source_competence_id)

    def competence_successor_state(
        self, repo: str, competence_id: str
    ) -> dict[str, Any]:
        from .competence_revision import competence_successor_state

        return competence_successor_state(self, repo, competence_id)

    def verify_successor_lineage(
        self, repo: str, competence_id: str
    ) -> dict[str, Any]:
        from .competence_revision import verify_successor_lineage

        return verify_successor_lineage(self, repo, competence_id)

    def register_adapter_provenance(
        self,
        repo: str,
        adapter: Any,
        *,
        boundary_kind: str,
        principal_id: str,
        principal_secret: str,
        endpoint_descriptor: Mapping[str, Any] | None = None,
        model_family: str | None = None,
        capability_class: str | None = None,
    ) -> dict[str, Any]:
        from .adapter_provenance import register_adapter_provenance

        return register_adapter_provenance(
            self,
            repo,
            adapter,
            boundary_kind=boundary_kind,
            principal_id=principal_id,
            principal_secret=principal_secret,
            endpoint_descriptor=endpoint_descriptor,
            model_family=model_family,
            capability_class=capability_class,
        )

    def append_will_receipt(
        self, repo: str, will: dict[str, Any]
    ) -> dict[str, Any]:
        """Append one immutable will receipt (exactly-once per will_id)."""
        if not isinstance(will, dict):
            raise TypeError("will receipt must be a dict")
        receipt_hash = str(will.get("receipt_hash") or "").strip()
        will_id = str(will.get("will_id") or "").strip()
        event_id = str(will.get("event_id") or "").strip()
        principal_id = str(will.get("principal_id") or "").strip()
        if not all([receipt_hash, will_id, event_id, principal_id]):
            raise ValueError("will receipt missing required identity fields")
        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "")
            existing = conn.execute(
                """SELECT * FROM will_receipts
                   WHERE repository_id=? AND will_id=?""",
                (repository_id, will_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError("will_id already has different content")
                return {**will, "inserted": False, "duplicate": True}
            created_at = float(will.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO will_receipts(
                       receipt_hash, repository_id, repo, principal_id, will_id,
                       session_id, body_epoch_id, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    principal_id,
                    will_id,
                    will.get("session_id"),
                    will.get("body_epoch_id"),
                    event_id,
                    self._symbiotic_canonical_json(will),
                    created_at,
                ),
            )
            return {**will, "inserted": True, "duplicate": False}

    def append_membrane_admission(
        self, repo: str, admission: dict[str, Any]
    ) -> dict[str, Any]:
        """Append one immutable membrane admission receipt."""
        if not isinstance(admission, dict):
            raise TypeError("membrane admission must be a dict")
        receipt_hash = str(admission.get("receipt_hash") or "").strip()
        event_id = str(admission.get("event_id") or "").strip()
        if not receipt_hash or not event_id:
            raise ValueError("membrane admission missing receipt_hash/event_id")
        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "")
            existing = conn.execute(
                """SELECT * FROM membrane_admissions
                   WHERE receipt_hash=?""",
                (receipt_hash,),
            ).fetchone()
            if existing is not None:
                return {**admission, "inserted": False, "duplicate": True}
            created_at = float(admission.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO membrane_admissions(
                       receipt_hash, repository_id, repo, session_id, will_id,
                       will_receipt_hash, admitted_count, rejected_count,
                       deferred_count, durable_write_authorized, event_id,
                       receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    admission.get("session_id"),
                    admission.get("will_id"),
                    admission.get("will_receipt_hash"),
                    int(admission.get("admitted_count") or 0),
                    int(admission.get("rejected_count") or 0),
                    int(admission.get("deferred_count") or 0),
                    1 if admission.get("durable_write_authorized") else 0,
                    event_id,
                    self._symbiotic_canonical_json(admission),
                    created_at,
                ),
            )
            return {**admission, "inserted": True, "duplicate": False}

    def append_admitted_memory(
        self, repo: str, memory: dict[str, Any]
    ) -> dict[str, Any]:
        """Append one immutable admitted memory (exactly-once per candidate_id)."""
        if not isinstance(memory, dict):
            raise TypeError("admitted memory must be a dict")
        receipt_hash = str(memory.get("receipt_hash") or "").strip()
        memory_id = str(memory.get("memory_id") or "").strip()
        candidate_id = str(memory.get("candidate_id") or "").strip()
        event_id = str(memory.get("event_id") or "").strip()
        session_id = str(memory.get("session_id") or "").strip()
        body_epoch_id = str(memory.get("body_epoch_id") or "").strip()
        if not all(
            [receipt_hash, memory_id, candidate_id, event_id, session_id, body_epoch_id]
        ):
            raise ValueError("admitted memory missing required identity fields")
        with self.transaction() as conn:
            repository = conn.execute(
                "SELECT repository_id FROM repositories WHERE name=?", (repo,)
            ).fetchone()
            if repository is None:
                raise ValueError(f"Unknown repository: {repo}")
            repository_id = str(repository["repository_id"] or "")
            existing = conn.execute(
                """SELECT * FROM admitted_memories
                   WHERE repository_id=? AND candidate_id=?""",
                (repository_id, candidate_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError(
                        "candidate_id already has different admitted memory"
                    )
                return {**memory, "inserted": False, "duplicate": True}
            created_at = float(memory.get("created_at") or time.time())
            source = dict(memory.get("source") or {})
            conn.execute(
                """INSERT INTO admitted_memories(
                       receipt_hash, memory_id, repository_id, repo, session_id,
                       turn_id, body_epoch_id, candidate_id, candidate_type,
                       will_receipt_hash, membrane_receipt_hash, transition_hash,
                       outcome_hash, support_level, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    memory_id,
                    repository_id,
                    repo,
                    session_id,
                    int(memory.get("turn_id") or 0),
                    body_epoch_id,
                    candidate_id,
                    str(memory.get("candidate_type") or "unresolved_ambiguity"),
                    memory.get("will_receipt_hash"),
                    memory.get("membrane_receipt_hash"),
                    source.get("transition_hash"),
                    source.get("outcome_hash"),
                    str(memory.get("support_level") or "none"),
                    event_id,
                    self._symbiotic_canonical_json(memory),
                    created_at,
                ),
            )
            return {**memory, "inserted": True, "duplicate": False}

    def list_admitted_memories(
        self,
        repo: str,
        *,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        repository_id = str(repository["repository_id"] or "")
        limit = max(1, min(int(limit or 100), 10_000))
        if session_id:
            rows = self.db.execute(
                """SELECT receipt_json FROM admitted_memories
                   WHERE repository_id=? AND repo=? AND session_id=?
                   ORDER BY created_at ASC LIMIT ?""",
                (repository_id, repo, str(session_id), limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                """SELECT receipt_json FROM admitted_memories
                   WHERE repository_id=? AND repo=?
                   ORDER BY created_at ASC LIMIT ?""",
                (repository_id, repo, limit),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                out.append(json.loads(row["receipt_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return out

    def _repo_id(self, conn: sqlite3.Connection, repo: str) -> str:
        repository = conn.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            raise ValueError(f"Unknown repository: {repo}")
        return str(repository["repository_id"] or "")

    def _append_json_receipt(
        self,
        repo: str,
        table: str,
        receipt: dict[str, Any],
        *,
        columns: list[str],
        values: list[Any],
        duplicate_query: str,
        duplicate_params: tuple[Any, ...],
    ) -> dict[str, Any]:
        if not isinstance(receipt, dict):
            raise TypeError(f"{table} receipt must be a dict")
        receipt_hash = str(receipt.get("receipt_hash") or "").strip()
        event_id = str(receipt.get("event_id") or "").strip()
        if not receipt_hash or not event_id:
            raise ValueError(f"{table} missing receipt_hash/event_id")
        with self.transaction() as conn:
            self._repo_id(conn, repo)
            existing = conn.execute(duplicate_query, duplicate_params).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError(f"{table} identity already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            placeholders = ", ".join("?" for _ in columns)
            col_sql = ", ".join(columns)
            conn.execute(
                f"INSERT INTO {table}({col_sql}) VALUES({placeholders})",
                values,
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def append_memory_state_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        memory_id = str(receipt.get("memory_id") or "")
        seq = int(receipt.get("state_sequence") or 0)
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            existing = conn.execute(
                """SELECT * FROM memory_state_receipts
                   WHERE repository_id=? AND memory_id=? AND state_sequence=?""",
                (repository_id, memory_id, seq),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != str(receipt.get("receipt_hash")):
                    raise ValueError("memory state sequence already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_state_receipts(
                       receipt_hash, repository_id, repo, memory_id, state,
                       state_sequence, prior_state_receipt_hash, will_receipt_hash,
                       effective_epoch_id, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_hash"],
                    repository_id,
                    repo,
                    memory_id,
                    str(receipt.get("state") or "active"),
                    seq,
                    receipt.get("prior_state_receipt_hash"),
                    receipt.get("will_receipt_hash"),
                    receipt.get("effective_epoch_id"),
                    receipt["event_id"],
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def list_memory_state_receipts(
        self, repo: str, memory_id: str
    ) -> list[dict[str, Any]]:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return []
        rows = self.db.execute(
            """SELECT receipt_json FROM memory_state_receipts
               WHERE repository_id=? AND memory_id=?
               ORDER BY state_sequence ASC""",
            (str(repository["repository_id"]), str(memory_id)),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                out.append(json.loads(row["receipt_json"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return out

    def append_memory_projection_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            session_id = str(receipt.get("session_id") or "")
            turn_id = int(receipt.get("turn_id") or 0)
            projection_id = str(receipt.get("projection_id") or "")
            existing = conn.execute(
                """SELECT * FROM memory_projection_receipts
                   WHERE repository_id=? AND session_id=? AND turn_id=?
                     AND projection_id=?""",
                (repository_id, session_id, turn_id, projection_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != str(receipt.get("receipt_hash")):
                    raise ValueError("projection identity already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_projection_receipts(
                       receipt_hash, repository_id, repo, session_id, turn_id,
                       projection_id, task_hash, body_epoch_id, current_will_hash,
                       event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_hash"],
                    repository_id,
                    repo,
                    session_id,
                    turn_id,
                    projection_id,
                    str(receipt.get("task_hash") or ""),
                    receipt.get("body_epoch_id"),
                    receipt.get("current_will_hash"),
                    receipt["event_id"],
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def append_memory_use_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            projection_id = str(receipt.get("projection_id") or "")
            outcome_hash = receipt.get("outcome_hash")
            existing = conn.execute(
                """SELECT * FROM memory_use_receipts
                   WHERE repository_id=? AND projection_id=?
                     AND ((outcome_hash IS NULL AND ? IS NULL) OR outcome_hash=?)""",
                (repository_id, projection_id, outcome_hash, outcome_hash),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != str(receipt.get("receipt_hash")):
                    raise ValueError("memory use identity already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_use_receipts(
                       receipt_hash, repository_id, repo, projection_id,
                       outcome_hash, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_hash"],
                    repository_id,
                    repo,
                    projection_id,
                    outcome_hash,
                    receipt["event_id"],
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def append_memory_credit_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            existing = conn.execute(
                "SELECT * FROM memory_credit_receipts WHERE event_id=? AND repository_id=?",
                (str(receipt.get("event_id")), repository_id),
            ).fetchone()
            if existing is not None:
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_credit_receipts(
                       receipt_hash, repository_id, repo, memory_id,
                       use_receipt_hash, credit_status, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_hash"],
                    repository_id,
                    repo,
                    str(receipt.get("memory_id") or ""),
                    receipt.get("use_receipt_hash"),
                    str(receipt.get("credit_status") or "unmeasured"),
                    receipt["event_id"],
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def append_memory_challenge_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            challenged = str(receipt.get("challenged_memory_id") or "")
            challenger = str(receipt.get("challenger_candidate_id") or "")
            existing = conn.execute(
                """SELECT * FROM memory_challenge_receipts
                   WHERE repository_id=? AND challenged_memory_id=?
                     AND challenger_candidate_id=?""",
                (repository_id, challenged, challenger),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != str(receipt.get("receipt_hash")):
                    raise ValueError("challenge identity already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_challenge_receipts(
                       receipt_hash, repository_id, repo, challenged_memory_id,
                       challenger_candidate_id, contradiction_kind, event_id,
                       receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_hash"],
                    repository_id,
                    repo,
                    challenged,
                    challenger,
                    str(receipt.get("contradiction_kind") or "unresolved_conflict"),
                    receipt["event_id"],
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def append_memory_supersession_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            old_id = str(receipt.get("superseded_memory_id") or "")
            new_id = str(receipt.get("replacement_memory_id") or "")
            existing = conn.execute(
                """SELECT * FROM memory_supersession_receipts
                   WHERE repository_id=? AND superseded_memory_id=?
                     AND replacement_memory_id=?""",
                (repository_id, old_id, new_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != str(receipt.get("receipt_hash")):
                    raise ValueError("supersession identity already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_supersession_receipts(
                       receipt_hash, repository_id, repo, superseded_memory_id,
                       replacement_memory_id, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_hash"],
                    repository_id,
                    repo,
                    old_id,
                    new_id,
                    receipt["event_id"],
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def get_membrane_admission_by_hash(
        self, repo: str, receipt_hash: str
    ) -> dict[str, Any] | None:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return None
        row = self.db.execute(
            """SELECT receipt_json FROM membrane_admissions
               WHERE repository_id=? AND receipt_hash=?""",
            (str(repository["repository_id"]), str(receipt_hash)),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["receipt_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def get_will_receipt_by_hash(
        self, repo: str, receipt_hash: str
    ) -> dict[str, Any] | None:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return None
        row = self.db.execute(
            """SELECT receipt_json FROM will_receipts
               WHERE repository_id=? AND receipt_hash=?""",
            (str(repository["repository_id"]), str(receipt_hash)),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["receipt_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def get_witness_result_by_hash(
        self, repo: str, witness_result_hash: str
    ) -> dict[str, Any] | None:
        """Resolve the immutable witness-result ledger in repository scope."""
        try:
            from .witness import get_witness_result

            return get_witness_result(self, repo, witness_result_hash)
        except Exception:
            return None

    def get_interconnect_frame_by_hash(
        self, repo: str, receipt_hash: str
    ) -> dict[str, Any] | None:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return None
        row = self.db.execute(
            """SELECT receipt_json FROM interconnect_frames
               WHERE repository_id=? AND repo=? AND receipt_hash=?""",
            (str(repository["repository_id"] or ""), repo, str(receipt_hash)),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["receipt_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def get_interconnect_transition_by_hash(
        self, repo: str, receipt_hash: str
    ) -> dict[str, Any] | None:
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return None
        row = self.db.execute(
            """SELECT receipt_json FROM interconnect_transitions
               WHERE repository_id=? AND repo=? AND receipt_hash=?""",
            (str(repository["repository_id"] or ""), repo, str(receipt_hash)),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["receipt_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def append_memory_trial_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(receipt, dict):
            raise TypeError("memory trial receipt must be a dict")
        receipt_hash = str(receipt.get("receipt_hash") or "").strip()
        event_id = str(receipt.get("event_id") or "").strip()
        if not receipt_hash or not event_id:
            raise ValueError("memory trial missing receipt_hash/event_id")
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            existing = conn.execute(
                """SELECT * FROM memory_trial_receipts
                   WHERE repository_id=? AND event_id=?""",
                (repository_id, event_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError("memory trial event already has different content")
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO memory_trial_receipts(
                       receipt_hash, repository_id, repo, task_hash,
                       g_rehydration, g_credit, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    str(receipt.get("task_hash") or ""),
                    receipt.get("G_rehydration"),
                    receipt.get("G_credit"),
                    event_id,
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def append_projection_budget_receipt(
        self, repo: str, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(receipt, dict):
            raise TypeError("projection budget receipt must be a dict")
        receipt_hash = str(receipt.get("receipt_hash") or "").strip()
        event_id = str(receipt.get("event_id") or "").strip()
        if not receipt_hash or not event_id:
            raise ValueError("projection budget missing receipt_hash/event_id")
        with self.transaction() as conn:
            repository_id = self._repo_id(conn, repo)
            existing = conn.execute(
                """SELECT * FROM projection_budget_receipts
                   WHERE repository_id=? AND event_id=?""",
                (repository_id, event_id),
            ).fetchone()
            if existing is not None:
                if str(existing["receipt_hash"]) != receipt_hash:
                    raise ValueError(
                        "projection budget event already has different content"
                    )
                return {**receipt, "inserted": False, "duplicate": True}
            created_at = float(receipt.get("created_at") or time.time())
            conn.execute(
                """INSERT INTO projection_budget_receipts(
                       receipt_hash, repository_id, repo, budget_policy_hash,
                       mode, event_id, receipt_json, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_hash,
                    repository_id,
                    repo,
                    str(receipt.get("budget_policy_hash") or ""),
                    str(receipt.get("mode") or ""),
                    event_id,
                    self._symbiotic_canonical_json(receipt),
                    created_at,
                ),
            )
            return {**receipt, "inserted": True, "duplicate": False}

    def _verify_symbiotic_session_conn(
        self,
        conn: sqlite3.Connection,
        repository_id: str,
        repo: str,
        session_id: str,
    ) -> dict[str, Any]:
        rows = conn.execute(
            """SELECT * FROM symbiotic_circulation_receipts
               WHERE repository_id=? AND repo=? AND session_id=?
               ORDER BY chain_sequence ASC""",
            (repository_id, repo, session_id),
        ).fetchall()
        tip = conn.execute(
            """SELECT * FROM symbiotic_circulation_chain_tips
               WHERE repository_id=? AND session_id=?""",
            (repository_id, session_id),
        ).fetchone()
        errors: list[str] = []
        invalid: list[str] = []
        previous = self.SYMBIOTIC_ZERO_HASH
        for index, row in enumerate(rows, start=1):
            if int(row["chain_sequence"]) != index:
                errors.append(f"sequence_gap:{row['chain_sequence']}")
            if str(row["previous_receipt_hash"]) != previous:
                errors.append(f"previous_hash_mismatch:{row['receipt_hash']}")
                invalid.append(str(row["receipt_hash"]))
            try:
                body = json.loads(row["receipt_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                body = None
            if not isinstance(body, dict):
                errors.append(f"receipt_json_invalid:{row['receipt_hash']}")
                invalid.append(str(row["receipt_hash"]))
                previous = str(row["receipt_hash"])
                continue
            # Subject hash is the scientific body without created_at / ledger linkage.
            subject_only = {
                key: value
                for key, value in body.items()
                if key
                not in {
                    "created_at",
                    "previous_receipt_hash",
                    "chain_sequence",
                    "ledger_schema_version",
                    "receipt_hash",
                    "subject_receipt_hash",
                    "inserted",
                    "duplicate",
                    "chain_valid",
                }
            }
            expected_subject = sha256(
                self._symbiotic_canonical_json(subject_only).encode("utf-8")
            ).hexdigest()
            if expected_subject != str(row["subject_receipt_hash"]):
                errors.append(f"subject_hash_invalid:{row['receipt_hash']}")
                invalid.append(str(row["receipt_hash"]))
            final_material = {
                "subject_receipt_hash": row["subject_receipt_hash"],
                "previous_receipt_hash": row["previous_receipt_hash"],
                "chain_sequence": int(row["chain_sequence"]),
                "repository_id": row["repository_id"],
                "repo": row["repo"],
                "session_id": row["session_id"],
                "body_epoch_id": row["body_epoch_id"],
                "kind": row["kind"],
                "status": row["status"],
                "receipt_json": row["receipt_json"],
                "created_at": float(row["created_at"]),
            }
            expected_hash = sha256(
                self._symbiotic_canonical_json(final_material).encode("utf-8")
            ).hexdigest()
            if expected_hash != str(row["receipt_hash"]):
                errors.append(f"receipt_hash_invalid:{row['receipt_hash']}")
                invalid.append(str(row["receipt_hash"]))
            previous = str(row["receipt_hash"])
        if tip is None and rows:
            errors.append("chain_tip_missing")
        if tip is not None:
            if int(tip["receipt_count"]) != len(rows):
                errors.append("tip_count_mismatch")
            if rows and str(tip["tip_receipt_hash"]) != str(rows[-1]["receipt_hash"]):
                errors.append("tip_hash_mismatch")
        return {
            "valid": not errors,
            "chain_valid": not errors,
            "repository_id": repository_id,
            "repo": repo,
            "session_id": session_id,
            "receipt_count": len(rows),
            "tip_receipt_hash": (
                str(tip["tip_receipt_hash"]) if tip is not None else None
            ),
            "invalid_receipt_hashes": sorted(set(invalid)),
            "errors": errors,
            "advisory_only": True,
            "policy_effect": False,
            "update_authorized": False,
        }

    def verify_symbiotic_session(
        self, repo: str, session_id: str
    ) -> dict[str, Any]:
        # Verification is observational.  Starting a nested ``BEGIN
        # IMMEDIATE`` here used to roll back a caller-owned transaction when
        # this verifier was reached through competence/provenance inspection.
        # Read through the existing connection/snapshot without committing or
        # ending any ambient transaction.
        repository = self.db.execute(
            "SELECT repository_id FROM repositories WHERE name=?", (repo,)
        ).fetchone()
        if repository is None:
            return {
                "valid": False,
                "chain_valid": False,
                "repo": repo,
                "session_id": session_id,
                "receipt_count": 0,
                "errors": ["repository_missing"],
                "advisory_only": True,
                "policy_effect": False,
                "update_authorized": False,
            }
        return self._verify_symbiotic_session_conn(
            self.db,
            str(repository["repository_id"]),
            str(repo),
            str(session_id),
        )

    def verify_symbiotic_receipt(
        self, repo: str, receipt_hash: str
    ) -> dict[str, Any]:
        receipt = self.symbiotic_receipt(receipt_hash, repo=repo)
        if not receipt:
            return {
                "verification_status": "not_found",
                "receipt_hash": receipt_hash,
                "valid": False,
                "advisory_only": True,
                "policy_effect": False,
                "update_authorized": False,
            }
        chain = self.verify_symbiotic_session(
            repo, str(receipt.get("session_id") or "")
        )
        row_valid = bool(chain.get("valid")) and receipt_hash not in set(
            chain.get("invalid_receipt_hashes") or []
        )
        return {
            "verification_status": "verified" if row_valid else "failed",
            "receipt_hash": receipt_hash,
            "kind": receipt.get("kind"),
            "session_id": receipt.get("session_id"),
            "valid": row_valid,
            "chain_valid": bool(chain.get("valid")),
            "chain": chain,
            "receipt": receipt,
            "advisory_only": True,
            "policy_effect": False,
            "update_authorized": False,
        }

    def save_continuation_packet(
        self, repo: str, packet_id: str, origin_version: str, state_hash: str,
        payload: dict[str, Any], expires_at: float | None,
    ) -> None:
        self.db.execute(
            """INSERT OR REPLACE INTO continuation_packets(
                 packet_id, repo, origin_version, state_hash, payload_json, created_at, expires_at
               ) VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (
                packet_id, repo, origin_version, state_hash,
                json.dumps(payload, sort_keys=True), time.time(), expires_at,
            ),
        )
        self.db.commit()

    def continuation_packet(self, repo: str, packet_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload_json FROM continuation_packets WHERE repo=? AND packet_id=?",
            (repo, packet_id),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def continuation_packets(self, repo: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """SELECT payload_json FROM continuation_packets
               WHERE repo=? ORDER BY created_at DESC LIMIT ?""",
            (repo, limit),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def canonical_state(self, repo: str, state_key: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM canonical_states WHERE repo=? AND state_key=?",
            (repo, state_key),
        ).fetchone()

    def canonical_states(self, repo: str) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM canonical_states WHERE repo=? ORDER BY state_key", (repo,)
        ).fetchall()

    @staticmethod
    def _receipt_hash(record: dict[str, Any]) -> str:
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def continuation_receipt_tail(self, repo: str) -> str:
        row = self.db.execute(
            """SELECT parent.receipt_hash
               FROM continuation_receipts parent
               LEFT JOIN continuation_receipts child
                 ON child.repo=parent.repo AND child.previous_hash=parent.receipt_hash
               WHERE parent.repo=? AND child.receipt_id IS NULL
               LIMIT 1""",
            (repo,),
        ).fetchone()
        return row["receipt_hash"] if row else "0" * 64

    def promote_canonical_state(
        self, repo: str, *, receipt_id: str, state_key: str, candidate: Any,
        evidence: list[dict[str, Any]], verification: dict[str, Any],
        authority: dict[str, Any],
    ) -> dict[str, Any]:
        now = time.time()
        existing = self.canonical_state(repo, state_key)
        previous = json.loads(existing["value_json"]) if existing else None
        candidate_json = json.dumps(candidate, sort_keys=True)
        state_hash = sha256(candidate_json.encode("utf-8")).hexdigest()
        previous_hash = self.continuation_receipt_tail(repo)
        record = {
            "receipt_id": receipt_id,
            "repo": repo,
            "action": "promote",
            "state_key": state_key,
            "previous": previous,
            "candidate": candidate,
            "evidence": evidence,
            "verification": verification,
            "authority": authority,
            "rollback_of": None,
            "previous_hash": previous_hash,
            "created_at": now,
        }
        receipt_hash = self._receipt_hash(record)
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO continuation_receipts(
                     receipt_id, repo, action, state_key, previous_json, candidate_json,
                     evidence_json, verification_json, authority_json, rollback_of,
                     previous_hash, receipt_hash, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt_id, repo, "promote", state_key,
                    json.dumps(previous, sort_keys=True) if existing else None,
                    candidate_json, json.dumps(evidence, sort_keys=True),
                    json.dumps(verification, sort_keys=True),
                    json.dumps(authority, sort_keys=True), None,
                    previous_hash, receipt_hash, now,
                ),
            )
            conn.execute(
                """INSERT INTO canonical_states(
                     repo, state_key, value_json, state_hash, receipt_id, updated_at
                   ) VALUES(?, ?, ?, ?, ?, ?)
                   ON CONFLICT(repo, state_key) DO UPDATE SET
                     value_json=excluded.value_json, state_hash=excluded.state_hash,
                     receipt_id=excluded.receipt_id, updated_at=excluded.updated_at""",
                (repo, state_key, candidate_json, state_hash, receipt_id, now),
            )
        return {
            "receipt_id": receipt_id,
            "receipt_hash": receipt_hash,
            "state_key": state_key,
            "state_hash": state_hash,
            "previous": previous,
            "candidate": candidate,
        }

    def rollback_canonical_state(
        self, repo: str, receipt_id: str, *, authority: dict[str, Any],
        recovery_verification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        original = self.db.execute(
            """SELECT * FROM continuation_receipts
               WHERE repo=? AND receipt_id=? AND action='promote'""",
            (repo, receipt_id),
        ).fetchone()
        if not original:
            raise ValueError("Promotion receipt does not exist")
        state_key = original["state_key"]
        current = self.canonical_state(repo, state_key)
        if not current or current["receipt_id"] != receipt_id:
            raise ValueError("Receipt is not the current canonical origin for this key")
        previous = json.loads(original["previous_json"]) if original["previous_json"] else None
        current_value = json.loads(current["value_json"])
        now = time.time()
        rollback_id = "rbk_" + sha256(
            f"{repo}|{receipt_id}|{state_key}".encode("utf-8")
        ).hexdigest()[:24]
        previous_hash = self.continuation_receipt_tail(repo)
        record = {
            "receipt_id": rollback_id,
            "repo": repo,
            "action": "rollback",
            "state_key": state_key,
            "previous": current_value,
            "candidate": previous,
            "evidence": [],
            "verification": {
                "receipt_integrity": True,
                "recovery_candidate": recovery_verification or {},
            },
            "authority": authority,
            "rollback_of": receipt_id,
            "previous_hash": previous_hash,
            "created_at": now,
        }
        receipt_hash = self._receipt_hash(record)
        with self.transaction() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO continuation_receipts(
                     receipt_id, repo, action, state_key, previous_json, candidate_json,
                     evidence_json, verification_json, authority_json, rollback_of,
                     previous_hash, receipt_hash, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?, ?, ?)""",
                (
                    rollback_id, repo, "rollback", state_key,
                    json.dumps(current_value, sort_keys=True),
                    json.dumps(previous, sort_keys=True) if previous is not None else None,
                    json.dumps(
                        {
                            "receipt_integrity": True,
                            "recovery_candidate": recovery_verification or {},
                        },
                        sort_keys=True,
                    ),
                    json.dumps(authority, sort_keys=True), receipt_id,
                    previous_hash, receipt_hash, now,
                ),
            )
            if previous is None:
                conn.execute(
                    "DELETE FROM canonical_states WHERE repo=? AND state_key=?",
                    (repo, state_key),
                )
            else:
                value_json = json.dumps(previous, sort_keys=True)
                state_hash = sha256(value_json.encode("utf-8")).hexdigest()
                conn.execute(
                    """UPDATE canonical_states
                       SET value_json=?, state_hash=?, receipt_id=?, updated_at=?
                       WHERE repo=? AND state_key=?""",
                    (value_json, state_hash, rollback_id, now, repo, state_key),
                )
        return {
            "rolled_back": True,
            "receipt_id": rollback_id,
            "rollback_of": receipt_id,
            "state_key": state_key,
            "restored": previous,
            "receipt_hash": receipt_hash,
        }

    def continuation_receipts(self, repo: str, limit: int = 100) -> list[sqlite3.Row]:
        return self.db.execute(
            """SELECT * FROM continuation_receipts
               WHERE repo=? ORDER BY created_at DESC LIMIT ?""",
            (repo, limit),
        ).fetchall()

    def verify_continuation_receipts(self, repo: str) -> bool:
        previous_hash = "0" * 64
        pending = {
            row["previous_hash"]: row
            for row in self.db.execute(
                "SELECT * FROM continuation_receipts WHERE repo=?", (repo,)
            ).fetchall()
        }
        visited = 0
        while previous_hash in pending:
            row = pending.pop(previous_hash)
            if row["previous_hash"] != previous_hash:
                return False
            record = {
                "receipt_id": row["receipt_id"],
                "repo": repo,
                "action": row["action"],
                "state_key": row["state_key"],
                "previous": json.loads(row["previous_json"]) if row["previous_json"] else None,
                "candidate": json.loads(row["candidate_json"]) if row["candidate_json"] else None,
                "evidence": json.loads(row["evidence_json"]),
                "verification": json.loads(row["verification_json"]),
                "authority": json.loads(row["authority_json"]),
                "rollback_of": row["rollback_of"],
                "previous_hash": row["previous_hash"],
                "created_at": float(row["created_at"]),
            }
            if self._receipt_hash(record) != row["receipt_hash"]:
                return False
            previous_hash = row["receipt_hash"]
            visited += 1
        return visited == len(self.continuation_receipts(repo, 1_000_000))

    def set_setting(self, key: str, value: Any) -> None:
        self.db.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, json.dumps(value, sort_keys=True)),
        )
        self.db.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default
