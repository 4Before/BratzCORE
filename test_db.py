from app import db, create_app
from models.user import User

app = create_app()

with app.app_context():
    result = db.session.execute(db.select(User)).scalars().all()
    print(result)