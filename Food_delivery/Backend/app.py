
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# MySQL database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://root:YOUR_PASSWORD@localhost/food_delivery"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# USER TABLE
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)


# RESTAURANT TABLE
class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200))


# FOOD TABLE
class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurant.id"), nullable=False
    )


# ORDER TABLE
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="Placed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ORDER ITEMS TABLE
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("order.id"), nullable=False
    )
    food_id = db.Column(
        db.Integer, db.ForeignKey("food.id"), nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


# HOME PAGE
@app.route("/")
def home():
    return jsonify({
        "message": "Welcome to Food Delivery Application!"
    })


# REGISTER USER
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not data.get("name") or not data.get("email"):
        return jsonify({"error": "Name and email are required"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    user = User(
        name=data["name"],
        email=data["email"]
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Registration successful",
        "user_id": user.id
    }), 201


# ADD RESTAURANT
@app.route("/restaurants", methods=["POST"])
def add_restaurant():
    data = request.get_json()

    if not data or not data.get("name"):
        return jsonify({"error": "Restaurant name required"}), 400

    restaurant = Restaurant(
        name=data["name"],
        location=data.get("location", "")
    )

    db.session.add(restaurant)
    db.session.commit()

    return jsonify({
        "message": "Restaurant added",
        "restaurant_id": restaurant.id
    }), 201


# GET ALL RESTAURANTS
@app.route("/restaurants", methods=["GET"])
def get_restaurants():
    restaurants = Restaurant.query.all()

    return jsonify([
        {
            "id": r.id,
            "name": r.name,
            "location": r.location
        }
        for r in restaurants
    ])


# ADD FOOD
@app.route("/foods", methods=["POST"])
def add_food():
    data = request.get_json()

    if not data or not data.get("name"):
        return jsonify({"error": "Food name required"}), 400

    try:
        price = float(data["price"])
        restaurant_id = int(data["restaurant_id"])

        if price <= 0:
            return jsonify({"error": "Price must be positive"}), 400
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Valid price and restaurant_id required"}), 400

    restaurant = db.session.get(Restaurant, restaurant_id)

    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    food = Food(
        name=data["name"],
        price=price,
        restaurant_id=restaurant_id
    )

    db.session.add(food)
    db.session.commit()

    return jsonify({
        "message": "Food added successfully",
        "food_id": food.id
    }), 201


# GET FOOD MENU
@app.route("/restaurants/<int:restaurant_id>/foods", methods=["GET"])
def get_foods(restaurant_id):
    restaurant = db.session.get(Restaurant, restaurant_id)

    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    foods = Food.query.filter_by(
        restaurant_id=restaurant_id
    ).all()

    return jsonify([
        {
            "id": f.id,
            "name": f.name,
            "price": f.price
        }
        for f in foods
    ])


# PLACE ORDER
@app.route("/orders", methods=["POST"])
def place_order():
    data = request.get_json()

    if not data or not isinstance(data.get("items"), list) or not data["items"]:
        return jsonify({"error": "Order items are required"}), 400

    user = db.session.get(User, data.get("user_id"))

    if not user:
        return jsonify({"error": "User not found"}), 404

    total = 0
    order_items = []

    try:
        for item in data["items"]:
            food = db.session.get(Food, int(item["food_id"]))
            quantity = int(item["quantity"])

            if not food:
                return jsonify({"error": "Food not found"}), 404

            if quantity <= 0:
                return jsonify({"error": "Invalid quantity"}), 400

            total += food.price * quantity

            order_items.append(
                OrderItem(
                    food_id=food.id,
                    quantity=quantity,
                    price=food.price
                )
            )

    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid order details"}), 400

    order = Order(
        user_id=user.id,
        total_amount=total
    )

    try:
        db.session.add(order)
        db.session.flush()

        for item in order_items:
            item.order_id = order.id
            db.session.add(item)

        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Could not place order"}), 500

    return jsonify({
        "message": "Order placed successfully",
        "order_id": order.id,
        "total_amount": round(total, 2),
        "status": order.status
    }), 201


# VIEW USER ORDERS
@app.route("/orders/<int:user_id>", methods=["GET"])
def get_orders(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    orders = Order.query.filter_by(user_id=user_id).all()

    return jsonify([
        {
            "order_id": o.id,
            "total_amount": o.total_amount,
            "status": o.status,
            "created_at": o.created_at.isoformat()
        }
        for o in orders
    ])


# UPDATE ORDER STATUS
@app.route("/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    data = request.get_json()

    order = db.session.get(Order, order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    allowed_statuses = [
        "Placed", "Preparing", "Out for Delivery", "Delivered", "Cancelled"
    ]

    status = data.get("status") if data else None

    if status not in allowed_statuses:
        return jsonify({"error": "Invalid order status"}), 400

    order.status = status
    db.session.commit()

    return jsonify({
        "message": "Order status updated",
        "status": order.status
    })


# CREATE DATABASE TABLES
with app.app_context():
    db.create_all()


# START APPLICATION
if __name__ == "__main__":
    app.run(debug=True)

