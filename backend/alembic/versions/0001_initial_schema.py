"""Initial schema – creates all FairGuard tables.

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUM TYPES (EXPLICIT SQL)
    # ------------------------------------------------------------------
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'project_owner', 'viewer')")
    op.execute("CREATE TYPE project_domain AS ENUM ('hiring', 'lending', 'healthcare', 'other')")
    op.execute("CREATE TYPE audit_verdict AS ENUM ('pass', 'fail', 'pass_with_warnings')")
    op.execute("CREATE TYPE audit_trigger AS ENUM ('api', 'cli')")
    op.execute("CREATE TYPE window_type AS ENUM ('last_100', 'last_1000', 'last_1hr', 'last_24hr')")
    op.execute("CREATE TYPE snapshot_status AS ENUM ('healthy', 'warning', 'critical')")
    op.execute("CREATE TYPE notification_channel AS ENUM ('email', 'webhook')")


    # ------------------------------------------------------------------
    # TABLE: users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "project_owner", "viewer", name="user_role", create_type=False),
            server_default="project_owner",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # TABLE: projects
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "domain",
            sa.Enum("hiring", "lending", "healthcare", "other", name="project_domain", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    # ------------------------------------------------------------------
    # TABLE: fairness_contracts
    # ------------------------------------------------------------------
    op.create_table(
        "fairness_contracts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("contracts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version", name="uq_contract_project_version"),
    )
    op.create_index("ix_fairness_contracts_project_id", "fairness_contracts", ["project_id"])
    op.create_index("ix_fairness_contracts_is_current", "fairness_contracts", ["is_current"])

    # ------------------------------------------------------------------
    # TABLE: offline_audits
    # ------------------------------------------------------------------
    op.create_table(
        "offline_audits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_filename", sa.String(500), nullable=True),
        sa.Column("dataset_hash", sa.String(64), nullable=True),
        sa.Column("target_column", sa.String(255), nullable=True),
        sa.Column("prediction_column", sa.String(255), nullable=True),
        sa.Column(
            "sensitive_columns",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "metrics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "verdict",
            sa.Enum("pass", "fail", "pass_with_warnings", name="audit_verdict", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "triggered_by",
            sa.Enum("api", "cli", name="audit_trigger", create_type=False),
            nullable=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["contract_version_id"], ["fairness_contracts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offline_audits_project_id", "offline_audits", ["project_id"])
    op.create_index("ix_offline_audits_created_at", "offline_audits", ["created_at"])

    # ------------------------------------------------------------------
    # TABLE: fairness_receipts
    # ------------------------------------------------------------------
    op.create_table(
        "fairness_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_endpoint_id", sa.Text(), nullable=True),
        sa.Column("dataset_hash", sa.String(64), nullable=True),
        sa.Column("contract_version", sa.Integer(), nullable=True),
        sa.Column(
            "contracts_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "metrics_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("verdict", sa.String(50), nullable=True),
        sa.Column("signed_payload", sa.Text(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("onchain_tx_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["audit_id"], ["offline_audits.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_id", name="uq_receipt_audit_id"),
    )
    op.create_index("ix_fairness_receipts_project_id", "fairness_receipts", ["project_id"])

    # ------------------------------------------------------------------
    # TABLE: runtime_decisions
    # ------------------------------------------------------------------
    op.create_table(
        "runtime_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_endpoint_id", sa.Text(), nullable=False),
        sa.Column("aggregation_key", sa.Text(), nullable=True),
        sa.Column("decision_id", sa.Text(), nullable=False),
        sa.Column(
            "sensitive_attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("ground_truth", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runtime_decisions_project_id", "runtime_decisions", ["project_id"])
    op.create_index("ix_runtime_decisions_timestamp", "runtime_decisions", ["timestamp"])
    op.create_index(
        "ix_runtime_decisions_aggregation_key",
        "runtime_decisions",
        ["aggregation_key"],
    )

    # ------------------------------------------------------------------
    # TABLE: runtime_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "runtime_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregation_key", sa.Text(), nullable=True),
        sa.Column(
            "window_type",
            sa.Enum(
                "last_100", "last_1000", "last_1hr", "last_24hr",
                name="window_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "metrics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("healthy", "warning", "critical", name="snapshot_status", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "aggregation_key",
            "window_type",
            name="uq_snapshot_project_key_window",
        ),
    )
    op.create_index("ix_runtime_snapshots_project_id", "runtime_snapshots", ["project_id"])

    # ------------------------------------------------------------------
    # TABLE: notification_configs
    # ------------------------------------------------------------------
    op.create_table(
        "notification_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("email", "webhook", name="notification_channel", create_type=False),
            nullable=False,
        ),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_configs_project_id", "notification_configs", ["project_id"]
    )

    # ------------------------------------------------------------------
    # TABLE: notification_logs
    # ------------------------------------------------------------------
    op.create_table(
        "notification_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_event", sa.Text(), nullable=True),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_logs_project_id", "notification_logs", ["project_id"]
    )

    # ------------------------------------------------------------------
    # TABLE: api_keys
    # ------------------------------------------------------------------
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])


def downgrade() -> None:
    # Drop tables in reverse FK dependency order
    op.drop_table("api_keys")
    op.drop_table("notification_logs")
    op.drop_table("notification_configs")
    op.drop_table("runtime_snapshots")
    op.drop_table("runtime_decisions")
    op.drop_table("fairness_receipts")
    op.drop_table("offline_audits")
    op.drop_table("fairness_contracts")
    op.drop_table("projects")
    op.drop_table("users")

    # Drop ENUM types
    for name in (
        "notification_channel",
        "snapshot_status",
        "window_type",
        "audit_trigger",
        "audit_verdict",
        "project_domain",
        "user_role",
    ):
        postgresql.ENUM(name=name, create_type=False).drop(
            op.get_bind(), checkfirst=True
        )
