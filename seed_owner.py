from app import app, db
from models.user import User

with app.app_context():
    if not User.query.filter_by(email="owner@market.com").first():
        u = User(email="owner@market.com", account_type="OWNER", privileges={"ADMIN": True, "ALL": True})
        u.set_password("StrongPass123!")
        db.session.add(u)
        db.session.commit()
        print("Seeded OWNER: owner@market.com / StrongPass123!")
    else:
        print("OWNER already exists.")