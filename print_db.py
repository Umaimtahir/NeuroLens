"""Print all database content"""
from database import SessionLocal
from models import User, EmotionLog, AnalysisSession, ContentSession, AuditLog
from sqlalchemy import func as sqla_func
from collections import defaultdict

db = SessionLocal()

print("=" * 80)
print("USERS")
print("=" * 80)
users = db.query(User).all()
if not users:
    print("  (no records)")
for u in users:
    print(f"  ID={u.id} | name={u.name} | email_hash={u.email_hash[:20]}... | verified={u.email_verified} | active={u.is_active} | current_emotion={u.current_emotion} | current_content={u.current_content} | is_recording={u.is_recording} | created={u.created_at}")

print()
print("=" * 80)
print("EMOTION LOGS")
print("=" * 80)
logs = db.query(EmotionLog).order_by(EmotionLog.created_at.desc()).limit(50).all()
if not logs:
    print("  (no records)")
for l in logs:
    print(f"  ID={l.id} | user_id={l.user_id} | username={l.username} | emotion={l.emotion} | intensity={l.intensity} | content_type={l.content_type} | is_guest={l.is_guest} | created={l.created_at}")

print()
print("=" * 80)
print("ANALYSIS SESSIONS")
print("=" * 80)
sessions = db.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).limit(50).all()
if not sessions:
    print("  (no records)")
for s in sessions:
    print(f"  ID={s.id} | user_id={s.user_id} | emotion={s.emotion} | intensity={s.intensity} | content_type={s.content_type} | duration={s.duration_seconds}s | is_guest={s.is_guest} | created={s.created_at}")

print()
print("=" * 80)
print("CONTENT SESSIONS")
print("=" * 80)
csessions = db.query(ContentSession).order_by(ContentSession.created_at.desc()).limit(50).all()
if not csessions:
    print("  (no records)")
for c in csessions:
    print(f"  ID={c.id} | user_id={c.user_id} | username={c.username} | content_type={c.content_type} | activity={c.activity} | productivity={c.productivity} | app={c.app_name} | duration={c.duration_seconds}s | active={c.is_active} | created={c.created_at}")

print()
print("=" * 80)
print("AUDIT LOGS")
print("=" * 80)
alogs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(50).all()
if not alogs:
    print("  (no records)")
for a in alogs:
    print(f"  ID={a.id} | user_id={a.user_id} | username={a.username} | action={a.action} | status={a.status} | details={str(a.details)[:80] if a.details else None} | created={a.created_at}")

print()
print("=" * 80)
print("TIME SPENT PER CONTENT TYPE (per user)")
print("=" * 80)

def format_duration(seconds):
    if not seconds or seconds <= 0:
        return "0s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

# Query total time per user per content type
time_summary = db.query(
    ContentSession.user_id,
    ContentSession.username,
    ContentSession.content_type,
    sqla_func.sum(ContentSession.duration_seconds).label('total_seconds'),
    sqla_func.count(ContentSession.id).label('session_count')
).filter(
    ContentSession.duration_seconds.isnot(None)
).group_by(
    ContentSession.user_id,
    ContentSession.username,
    ContentSession.content_type
).order_by(ContentSession.user_id).all()

if not time_summary:
    print("  (no records with duration)")
else:
    current_user = None
    user_total = 0
    for row in time_summary:
        if current_user != row.user_id:
            if current_user is not None:
                print(f"  {'':>40} TOTAL: {format_duration(user_total)}")
                print()
            current_user = row.user_id
            user_total = 0
            print(f"  User: {row.username} (ID={row.user_id})")
            print(f"  {'Content Type':<30} {'Time':>15} {'Sessions':>10}")
            print(f"  {'-'*30} {'-'*15} {'-'*10}")
        total = row.total_seconds or 0
        user_total += total
        print(f"  {row.content_type:<30} {format_duration(total):>15} {row.session_count:>10}")
    if current_user is not None:
        print(f"  {'':>40} TOTAL: {format_duration(user_total)}")

print()
print("=" * 80)
print("TIME SPENT PER ACTIVITY (per user)")
print("=" * 80)

activity_summary = db.query(
    ContentSession.user_id,
    ContentSession.username,
    ContentSession.activity,
    ContentSession.activity_emoji,
    ContentSession.productivity,
    sqla_func.sum(ContentSession.duration_seconds).label('total_seconds'),
    sqla_func.count(ContentSession.id).label('session_count')
).filter(
    ContentSession.duration_seconds.isnot(None)
).group_by(
    ContentSession.user_id,
    ContentSession.username,
    ContentSession.activity,
    ContentSession.activity_emoji,
    ContentSession.productivity
).order_by(ContentSession.user_id).all()

if not activity_summary:
    print("  (no records with duration)")
else:
    current_user = None
    for row in activity_summary:
        if current_user != row.user_id:
            if current_user is not None:
                print()
            current_user = row.user_id
            print(f"  User: {row.username} (ID={row.user_id})")
            print(f"  {'Activity':<20} {'Productivity':<15} {'Time':>15} {'Sessions':>10}")
            print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*10}")
        total = row.total_seconds or 0
        emoji = row.activity_emoji or ''
        prod = row.productivity or 'N/A'
        print(f"  {emoji} {row.activity:<18} {prod:<15} {format_duration(total):>15} {row.session_count:>10}")

db.close()
print("\nDone.")
