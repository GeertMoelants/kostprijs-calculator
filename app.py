# app.py
from flask import Flask, render_template
import pandas as pd
from collections import OrderedDict

# Importeer de db instantie en de modellen
from models import db, Product, Dish, Category as ProductCategory, DishCategory
from category_order_manager import load_category_order

# Importeer de blueprints
from routes.products import product_bp
from routes.dishes import dish_bp

app = Flask(__name__)

# --- Database Configuratie ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kostprijs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'verander_dit_naar_een_echte_geheime_sleutel'

# Initialiseer de database met de app
db.init_app(app)

# Registreer de blueprints bij de applicatie
app.register_blueprint(product_bp)
app.register_blueprint(dish_bp)

# --- Custom Jinja2 Filters ---
@app.template_filter('format_currency')
def format_currency(value, decimals=2):
    if value is None or pd.isna(value):
        return 'N/A'
    try:
        formatted_value = f"{float(value):.{decimals}f}"
        return formatted_value.replace('.', ',')
    except (ValueError, TypeError):
        return 'N/A'

@app.template_filter('format_number_flexible')
def format_number_flexible(value):
    if value is None or pd.isna(value):
        return 'N/A'
    try:
        float_val = float(value)
        if float_val == int(float_val):
            return str(int(float_val))
        return str(round(float_val, 2)).replace('.', ',')
    except (ValueError, TypeError):
        return 'N/A'

# --- Hoofdroute ---
@app.route('/')
def index():
    category_orders = load_category_order()

    # Sorteer en groepeer gerechten per categorie
    all_dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    sorted_dish_category_names = [cat.name for cat in all_dish_categories]
    
    # Pas de custom sorteervolgorde toe
    custom_sorted_dish_names = [name for name in category_orders.get('dishes', []) if name in sorted_dish_category_names]
    custom_sorted_dish_names += [name for name in sorted_dish_category_names if name not in custom_sorted_dish_names]

    composed_dishes_by_category = OrderedDict()
    for cat_name in custom_sorted_dish_names:
        category = next((cat for cat in all_dish_categories if cat.name == cat_name), None)
        if category:
            composed_dishes_by_category[cat_name] = category.dishes

    # Sorteer en groepeer producten per categorie
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
        composed_dishes_by_category=composed_dishes_by_category,
        products_by_category=products_by_category
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Maakt de database en tabellen aan als ze niet bestaan
    app.run(debug=True, port=5001)
