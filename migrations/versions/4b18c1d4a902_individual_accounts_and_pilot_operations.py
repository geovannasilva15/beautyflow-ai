"""individual accounts and pilot operations

Revision ID: 4b18c1d4a902
Revises: 91b31bc719f6
Create Date: 2026-11-18 15:39:52.829261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b18c1d4a902'
down_revision: Union[str, Sequence[str], None] = '91b31bc719f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('account',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=160), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('must_change_password', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_email'), 'account', ['email'], unique=True)
    op.create_table('loginlimit',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index(op.f('ix_loginlimit_expires_at'), 'loginlimit', ['expires_at'], unique=False)
    op.create_table('whatsappmessage',
        sa.Column('provider_id', sa.String(length=255), nullable=False),
        sa.Column('sender', sa.String(length=15), nullable=False),
        sa.Column('body', sa.String(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('intent', sa.String(length=24), nullable=False),
        sa.Column('reply_status', sa.String(length=16), nullable=False),
        sa.Column('reply_text', sa.String(), nullable=True),
        sa.Column('reply_provider_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('provider_id')
    )
    op.create_index(op.f('ix_whatsappmessage_received_at'), 'whatsappmessage', ['received_at'], unique=False)
    op.create_table('loginsession',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.PrimaryKeyConstraint('token_hash')
    )
    op.create_index(op.f('ix_loginsession_account_id'), 'loginsession', ['account_id'], unique=False)
    op.create_index(op.f('ix_loginsession_expires_at'), 'loginsession', ['expires_at'], unique=False)
    op.add_column('appointment', sa.Column('duration_minutes', sa.Integer(), nullable=True))
    # Legacy appointments used the linked service's current duration.
    op.execute(sa.text(
        "UPDATE appointment SET duration_minutes = "
        "(SELECT service.duration_minutes FROM service WHERE service.id = appointment.service_id) "
        "WHERE duration_minutes IS NULL"
    ))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('appointment', 'duration_minutes')
    op.drop_index(op.f('ix_loginsession_expires_at'), table_name='loginsession')
    op.drop_index(op.f('ix_loginsession_account_id'), table_name='loginsession')
    op.drop_table('loginsession')
    op.drop_index(op.f('ix_whatsappmessage_received_at'), table_name='whatsappmessage')
    op.drop_table('whatsappmessage')
    op.drop_index(op.f('ix_loginlimit_expires_at'), table_name='loginlimit')
    op.drop_table('loginlimit')
    op.drop_index(op.f('ix_account_email'), table_name='account')
    op.drop_table('account')
