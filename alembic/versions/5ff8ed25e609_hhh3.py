"""hhh3

Revision ID: 5ff8ed25e609
Revises: f35023ccf720
Create Date: 2022-01-19 17:03:38.597006

"""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.orm import Session
from models import User


# revision identifiers, used by Alembic.
revision = '5ff8ed25e609'
down_revision = 'f35023ccf720'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_available_status', sa.Boolean(), nullable=True))
    op.execute("UPDATE users SET is_available_status = false")
    
    conn = op.get_bind()
    session = Session(bind=conn)
    op.add_column('users', sa.Column('unique_id', sa.String(length=100), nullable=True))
    for item in session.query(User).filter_by(unique_id=None):
        item.unique_id = uuid.uuid4().hex
    session.commit()
    op.create_unique_constraint(None, 'users', ['unique_id'])
    op.alter_column(table_name='users',column_name='unique_id',nullable=False)
    
    
    
    op.create_table('agent_punch_record',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('is_available_status', sa.Boolean(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_punch_record_id'), 'agent_punch_record', ['id'], unique=False)
    
    
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_agent_punch_record_id'), table_name='agent_punch_record')
    
    op.drop_table('agent_punch_record')
    
    
    
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'unique_id')
    
    op.drop_column('users', 'is_available_status')
    
    
    # ### end Alembic commands ###
