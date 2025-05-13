from flask import Blueprint, jsonify, request, g
from models import SubscriptionPlan, User, UserSubscription, db
from datetime import datetime
from functools import wraps

subscription_routes_bp = Blueprint('subscription_routes', __name__)

def token_required(f):
    """
    Decorator to protect routes that require a valid JWT token.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Authorization token is required'}), 401
        try:
            from user_routes import verify_token
            token = token.split(' ')[-1]
            payload = verify_token(token)
            user_id = payload['sub']
            user = User.query.get(user_id)
            if not user:
                return jsonify({'message': 'User not found'}), 404
            g.current_user = user
        except Exception as e:
            return jsonify({'message': str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

@subscription_routes_bp.route('/plans', methods=['GET'])
def get_plans():
    """
    Lists all subscription plans.
    """
    plans = SubscriptionPlan.query.all()
    plan_list = [{
        'id': plan.id,
        'name': plan.name,
        'price': float(plan.price),
        'interval': plan.interval,
        'description': plan.description
    } for plan in plans]
    return jsonify(plan_list), 200

@subscription_routes_bp.route('/subscribe/<int:plan_id>', methods=['POST'])
@token_required
def subscribe(plan_id):
    """
    Subscribes the current user to a subscription plan.
    """
    user = g.current_user
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return jsonify({'message': 'Subscription plan not found'}), 404

    active_subscription = UserSubscription.query.filter_by(user_id=user.id, status='active').first()
    if active_subscription:
        return jsonify({'message': 'User already has an active subscription'}), 400

    new_subscription = UserSubscription(user_id=user.id, plan_id=plan.id, status='active')
    db.session.add(new_subscription)
    db.session.commit()
    return jsonify({'message': f'Subscribed to {plan.name} plan successfully'}), 201

@subscription_routes_bp.route('/upgrade/<int:subscription_id>/<int:new_plan_id>', methods=['POST'])
@token_required
def upgrade(subscription_id, new_plan_id):
    """
    Upgrades a user's subscription to a new plan.
    """
    user = g.current_user
    new_plan = SubscriptionPlan.query.get(new_plan_id)
    if not new_plan:
        return jsonify({'message': 'New subscription plan not found'}), 404

    subscription = UserSubscription.query.filter_by(id=subscription_id, user_id=user.id).first()
    if not subscription:
        return jsonify({'message': 'Subscription not found or does not belong to the user'}), 404

    if subscription.status != 'active':
        return jsonify({'message': 'Cannot upgrade an inactive subscription'}), 400

    old_plan = subscription.plan
    days_in_month = 30
    days_left = (subscription.end_date - datetime.utcnow()).days if subscription.end_date else days_in_month
    if days_left < 0:
        days_left = 0
    prorated_amount = (days_left / days_in_month) * float(old_plan.price) if old_plan.interval == 'monthly' else (days_left / 365) * float(old_plan.price)

    subscription.status = 'cancelled'
    subscription.end_date = datetime.utcnow()

    new_subscription = UserSubscription(user_id=user.id, plan_id=new_plan_id, status='active')
    db.session.add(new_subscription)
    db.session.commit()

    return jsonify({
        'message': f'Upgraded to {new_plan.name} plan successfully',
        'prorated_amount': prorated_amount
    }), 200

@subscription_routes_bp.route('/cancel/<int:subscription_id>', methods=['POST'])
@token_required
def cancel(subscription_id):
    """
    Cancels a user's subscription.
    """
    user = g.current_user
    subscription = UserSubscription.query.filter_by(id=subscription_id, user_id=user.id).first()
    if not subscription:
        return jsonify({'message': 'Subscription not found or does not belong to the user'}), 404

    if subscription.status != 'active':
        return jsonify({'message': 'Cannot cancel an inactive subscription'}), 400

    subscription.status = 'cancelled'
    subscription.end_date = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Subscription cancelled successfully'}), 200

@subscription_routes_bp.route('/subscriptions/active', methods=['GET'])
@token_required
def get_active_subscriptions():
    """
    Retrieves the active subscriptions for the current user.
    This uses a JOIN and WHERE clause, optimized with indexes.
    """
    user_id = g.current_user.id
    active_subscriptions = db.session.execute(db.text("""
        SELECT us.id, sp.name, sp.price, sp.interval, us.start_date, us.end_date
        FROM user_subscriptions us
        JOIN subscription_plans sp ON us.plan_id = sp.id
        WHERE us.user_id = :user_id AND us.status = 'active'
    """), {"user_id": user_id}).fetchall()

    subscriptions_data = [{
        'id': sub.id,
        'plan_name': sub.name,
        'price': float(sub.price),
        'interval': sub.interval,
        'start_date': sub.start_date.isoformat(),
        'end_date': sub.end_date.isoformat() if sub.end_date else None
    } for sub in active_subscriptions]

    return jsonify(subscriptions_data), 200

@subscription_routes_bp.route('/users/<int:user_id>/subscriptions', methods=['GET'])
@token_required
def get_user_subscriptions(user_id):
    """
    Retrieves all subscriptions for a specific user.  Added for completeness.
    """
    if g.current_user.id != user_id:
        return jsonify({'message': 'Unauthorized to view these subscriptions'}), 403

    subscriptions = UserSubscription.query.filter_by(user_id=user_id).order_by(
        UserSubscription.start_date.desc()).all()
    subscriptions_data = [{
        'id': sub.id,
        'plan_name': sub.plan.name,
        'price': float(sub.plan.price),
        'interval': sub.plan.interval,
        'start_date': sub.start_date.isoformat(),
        'end_date': sub.end_date.isoformat() if sub.end_date else None,
        'status': sub.status
    } for sub in subscriptions]
    return jsonify(subscriptions_data), 200
