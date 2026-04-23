import re
with open('backend/alembic/versions/0001_initial_schema.py', 'r') as f:
    text = f.read()

types_sql = '''    # ------------------------------------------------------------------
    # ENUM TYPES (EXPLICIT SQL)
    # ------------------------------------------------------------------
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'project_owner', 'viewer')")
    op.execute("CREATE TYPE project_domain AS ENUM ('hiring', 'lending', 'healthcare', 'other')")
    op.execute("CREATE TYPE audit_verdict AS ENUM ('pass', 'fail', 'pass_with_warnings')")
    op.execute("CREATE TYPE audit_trigger AS ENUM ('api', 'cli')")
    op.execute("CREATE TYPE window_type AS ENUM ('last_100', 'last_1000', 'last_1hr', 'last_24hr')")
    op.execute("CREATE TYPE snapshot_status AS ENUM ('healthy', 'warning', 'critical')")
    op.execute("CREATE TYPE notification_channel AS ENUM ('email', 'webhook')")
'''

text = re.sub(
    r'    # ------------------------------------------------------------------\n    # ENUM TYPES \(removed explicit creation as create_table does it\)\n    # ------------------------------------------------------------------',
    types_sql,
    text
)

text = text.replace('name="user_role")', 'name="user_role", create_type=False)')
text = text.replace('name="project_domain")', 'name="project_domain", create_type=False)')
text = text.replace('name="audit_verdict")', 'name="audit_verdict", create_type=False)')
text = text.replace('name="audit_trigger")', 'name="audit_trigger", create_type=False)')
text = text.replace('name="window_type",\n            )', 'name="window_type", create_type=False\n            )')
text = text.replace('name="snapshot_status")', 'name="snapshot_status", create_type=False)')
text = text.replace('name="notification_channel")', 'name="notification_channel", create_type=False)')

with open('backend/alembic/versions/0001_initial_schema.py', 'w') as f:
    f.write(text)
