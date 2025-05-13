import os
from flask import Flask
from datetime import timedelta

from models import SubscriptionPlan, db
from subscription_routes import subscription_routes_bp
from user_routes import user_routes_bp


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///subscriptions.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30) 
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)

app.register_blueprint(user_routes_bp)
app.register_blueprint(subscription_routes_bp)

def init_db():
    with app.app_context():
        db.create_all()
        if not SubscriptionPlan.query.first():
            plans = [
                SubscriptionPlan(name='Free', price=0.00, interval='monthly', description='Free plan'),
                SubscriptionPlan(name='Basic', price=10.00, interval='monthly', description='Basic plan'),
                SubscriptionPlan(name='Pro', price=25.00, interval='monthly', description='Pro plan')
            ]
            db.session.add_all(plans)
            db.session.commit()
            print("Initialized database with subscription plans.")
        else:
            print("Database already initialized.")

if __name__ == '__main__':
    db.init_app(app)
    init_db()
    app.run(debug=True)
