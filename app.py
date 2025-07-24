# app.py
from flask import Flask, render_template, jsonify, request
import pandas as pd
from collections import OrderedDict
from sqlalchemy import func
import os
import click

# Importeer de db instantie en de modellen
from models import db, Product, Dish, Category as ProductCategory, DishCategory, Ingredient
from category_order_manager import load_category_order
from db_seeder import seed_data # Importeer de seeder functie

# Importeer de blueprints
from routes.products import product_bp
from routes.dishes import dish_bp

app = Flask(__name__)

# --- Database Configuratie ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Corrigeer de URL voor SQLAlchemy 1.4+ en voeg sslmode toe
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if '?sslmode' not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"

# Lokale fallback
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'kostprijs.db')
LOCAL_DB_URI = f'sqlite:///{LOCAL_DB_PATH}'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or LOCAL_DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'een-simpele-maar-veilige-lokale-sleutel')

# Initialiseer de database met de app
db.init_app(app)

# Registreer de blueprints bij de applicatie
app.register_blueprint(product_bp)
app.register_blueprint(dish_bp)

# --- Custom Jinja2 Filters ---
@app.template_filter('format_currency')
def format_currency(value, decimals=2):
    if value is None or pd.isna(value): return 'N/A'
    try:
        return f"{float(value):.{decimals}f}".replace('.', ',')
    except (ValueError, TypeError):
        return 'N/A'

@app.template_filter('format_number_flexible')
def format_number_flexible(value):
    if value is None or pd.isna(value): return 'N/A'
    try:
        float_val = float(value)
        return str(int(float_val)) if float_val == int(float_val) else str(round(float_val, 2)).replace('.', ',')
    except (ValueError, TypeError):
        return 'N/A'

# --- API Route voor de Top Gerechten Grafiek ---
@app.route('/api/top_dishes')
def top_dishes_api():
    # ... (deze functie blijft ongewijzigd) ...
    sort_by = request.args.get('sort_by', 'cost_price')
    count = request.args.get('count', 5, type=int)
    all_dishes = Dish.query.all()
    if sort_by == 'profit':
        sorted_dishes = sorted(all_dishes, key=lambda d: d.selling_price_calculated - d.cost_price_calculated, reverse=True)
    else:
        sorted_dishes = sorted(all_dishes, key=lambda d: d.cost_price_calculated, reverse=True)
    top_dishes = sorted_dishes[:count]
    chart_data = {
        'labels': [d.name for d in top_dishes],
        'data': [d.selling_price_calculated - d.cost_price_calculated if sort_by == 'profit' else d.cost_price_calculated for d in top_dishes]
    }
    return jsonify(chart_data)

# --- Hoofdroute ---
@app.route('/')
def index():
    # ... (deze functie blijft ongewijzigd) ...
    cost_per_category_query = db.session.query(
        ProductCategory.name,
        func.sum(Ingredient.quantity * (Product.package_price / Product.package_weight))
    ).join(Product, ProductCategory.id == Product.category_id)\
     .join(Ingredient, Product.id == Ingredient.product_id)\
     .filter(Product.package_weight != None, Product.package_weight > 0, Product.package_price != None)\
     .group_by(ProductCategory.name)\
     .order_by(func.sum(Ingredient.quantity * (Product.package_price / Product.package_weight)).desc())\
     .all()
    
    cost_distribution_data = {
        'labels': [row[0] for row in cost_per_category_query],
        'data': [float(row[1]) if row[1] is not None else 0 for row in cost_per_category_query]
    }

    category_orders = load_category_order()
    all_dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    sorted_dish_category_names = [cat.name for cat in all_dish_categories]
    custom_sorted_dish_names = [name for name in category_orders.get('dishes', []) if name in sorted_dish_category_names]
    custom_sorted_dish_names += [name for name in sorted_dish_category_names if name not in custom_sorted_dish_names]
    composed_dishes_by_category = OrderedDict()
    for cat_name in custom_sorted_dish_names:
        category = next((cat for cat in all_dish_categories if cat.name == cat_name), None)
        if category:
            composed_dishes_by_category[cat_name] = category.dishes

    all_product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    sorted_product_category_names = [cat.name for cat in all_product_categories]
    custom_sorted_product_names = [name for name in category_orders.get('products', []) if name in sorted_product_category_names]
    custom_sorted_product_names += [name for name in sorted_product_category_names if name not in custom_sorted_product_names]
    products_by_category = OrderedDict()
    for cat_name in custom_sorted_product_names:
        category = next((cat for cat in all_product_categories if cat.name == cat_name), None)
        if category:
            products_by_category[cat_name] = category.products

    return render_template(
        'index.html',
        cost_distribution_json=jsonify(cost_distribution_data).get_data(as_text=True),
        composed_dishes_by_category=composed_dishes_by_category,
        products_by_category=products_by_category
    )

# --- Nieuwe CLI Commando's voor Database Beheer ---
@app.cli.command("init-db")
def init_db_command():
    """Maakt de databasetabellen aan."""
    db.create_all()
    print("Database tabellen aangemaakt.")

@app.cli.command("seed-db")
def seed_db_command():
    """Vult de database met initiële data uit CSV-bestanden."""
    seed_data()
    print("Database gevuld met initiële data.")

if __name__ == '__main__':
    app.run(debug=True, port=5001)
