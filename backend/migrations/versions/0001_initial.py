"""initial schema"""
from alembic import op
from app.core.database import Base
from app.models import activity, config, duplicate, note, report, task, user  # noqa: F401
revision="0001"; down_revision=None; branch_labels=None; depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())
