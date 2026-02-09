"""Print time spent per content type summary"""
from database import SessionLocal
from models import ContentSession
from sqlalchemy import func as sqla_func

db = SessionLocal()

def fmt(s):
    if not s or s <= 0: return "0s"
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}h {m}m {sec}s" if h else f"{m}m {sec}s" if m else f"{sec}s"

print("=" * 70)
print("TIME SPENT PER CONTENT TYPE (per user)")
print("=" * 70)
rows = db.query(
    ContentSession.user_id, ContentSession.username, ContentSession.content_type,
    sqla_func.sum(ContentSession.duration_seconds).label("total_secs"),
    sqla_func.count(ContentSession.id).label("sess_count")
).filter(ContentSession.duration_seconds.isnot(None)
).group_by(ContentSession.user_id, ContentSession.username, ContentSession.content_type
).order_by(ContentSession.user_id).all()

header1 = "Content Type"
header2 = "Time"
header3 = "Sessions"
cur = None
tot = 0
for r in rows:
    if cur != r.user_id:
        if cur is not None:
            print(f"  {'':>42} TOTAL: {fmt(tot)}")
            print()
        cur = r.user_id
        tot = 0
        print(f"  User: {r.username} (ID={r.user_id})")
        print(f"  {header1:<30} {header2:>12} {header3:>10}")
        print(f"  {'-'*30} {'-'*12} {'-'*10}")
    s = r.total_secs or 0
    tot += s
    print(f"  {r.content_type:<30} {fmt(s):>12} {r.sess_count:>10}")
if cur is not None:
    print(f"  {'':>42} TOTAL: {fmt(tot)}")

print()
print("=" * 70)
print("TIME SPENT PER ACTIVITY (per user)")
print("=" * 70)
rows2 = db.query(
    ContentSession.user_id, ContentSession.username, ContentSession.activity,
    ContentSession.activity_emoji, ContentSession.productivity,
    sqla_func.sum(ContentSession.duration_seconds).label("total_secs"),
    sqla_func.count(ContentSession.id).label("sess_count")
).filter(ContentSession.duration_seconds.isnot(None)
).group_by(ContentSession.user_id, ContentSession.username, ContentSession.activity,
    ContentSession.activity_emoji, ContentSession.productivity
).order_by(ContentSession.user_id).all()

cur = None
for r in rows2:
    if cur != r.user_id:
        if cur is not None:
            print()
        cur = r.user_id
        print(f"  User: {r.username} (ID={r.user_id})")
        print(f"  {'Activity':<20} {'Productivity':<15} {'Time':>12} {'Sessions':>10}")
        print(f"  {'-'*20} {'-'*15} {'-'*12} {'-'*10}")
    s = r.total_secs or 0
    e = r.activity_emoji or ""
    p = r.productivity or "N/A"
    print(f"  {e} {r.activity:<18} {p:<15} {fmt(s):>12} {r.sess_count:>10}")

db.close()
print("\nDone.")
