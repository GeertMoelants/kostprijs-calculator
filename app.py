# app.py
import os
import click
from flask import Flask, render_template, jsonify, request
from flask.cli import with_appcontext
from collections import OrderedDict
from sqlalchemy import func

# --- Importeer extensies, modellen en functies ---
from models import db, Product, Dish, Category as ProductCategory, DishCategory, Ingredient
from extensions import migrate # Aanname: je hebt een extensions.py voor Migrate
from category_order_manager import load_category_order
from db_seeder import seed_data

# --- Importeer de blueprints (routes) ---
from routes.products import product_bp
from routes.dishes import dish_bp
from routes.preparations import preparation_bp
# Het is een goede praktijk om ook de hoofdroutes in een blueprint te plaatsen,
# maar voor nu laten we ze hier voor de eenvoud.

def create_app():
    """
    Factory-functie om de Flask-applicatie aan te maken.
    Dit is een best practice voor schaalbare en testbare applicaties.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Database Configuratie & Geheime Sleutel ---
    # Zorgt ervoor dat de 'instance' map bestaat
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Gebruik de DATABASE_URL van Render, of een lokale SQLite database als fallback
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    LOCAL_DB_URI = f"sqlite:///{os.path.join(app.instance_path, 'kostprijs.db')}"

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or LOCAL_DB_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'een-sterke-lokale-geheime-sleutel')

    # --- DE FIX: Voeg deze twee regels toe voor stabiele databaseverbindingen ---
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 299
    app.config['SQLALCHEMY_POOL_PRE_PING'] = True

    # --- Koppel extensies aan de app ---
    db.init_app(app)
    migrate.init_app(app, db) # Je had migrate correct geïnitialiseerd

    # --- DE FIX: Registreer alle blueprints met de correcte URL-prefix ---
    # Dit lost het probleem op waarbij URLs voor gerechten en bereidingen incorrect waren.
    app.register_blueprint(product_bp, url_prefix='/products')
    app.register_blueprint(dish_bp, url_prefix='/dishes')
    app.register_blueprint(preparation_bp, url_prefix='/preparations')
    
    with app.app_context():
        # --- Custom Jinja2 Filters ---
        @app.template_filter('format_currency')
        def format_currency(value, decimals=2):
            if value is None: return 'N/A'
            try:
                return f"{float(value):.{decimals}f}".replace('.', ',')
            except (ValueError, TypeError):
                return 'N/A'

        @app.template_filter('format_number_flexible')
        def format_number_flexible(value):
            if value is None: return 'N/A'
            try:
                float_val = float(value)
                return str(int(float_val)) if float_val.is_integer() else str(round(float_val, 2)).replace('.', ',')
            except (ValueError, TypeError):
                return 'N/A'

        # --- API en Hoofdroutes ---
        @app.route('/api/top_dishes')
        def top_dishes_api():
            # ... (jouw bestaande API-logica is prima) ...
            sort_by = request.args.get('sort_by', 'cost_price')
            count = request.args.get('count', 5, type=int)
            all_dishes = Dish.query.filter_by(is_preparation=False).all()
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

        @app.route('/')
        def index():
            # ... (jouw bestaande index-logica is complex en blijft ongewijzigd) ...
            all_dish_categories = DishCategory.query.join(Dish).filter(Dish.is_preparation == False).distinct().order_by(DishCategory.name).all()
            cost_per_category_query = db.session.query(ProductCategory.name, func.sum(Ingredient.quantity * (Product.package_price / Product.package_weight))).join(Product, ProductCategory.id == Product.category_id).join(Ingredient, Product.id == Ingredient.product_id).filter(Product.package_weight != None, Product.package_weight > 0, Product.package_price != None).group_by(ProductCategory.name).order_by(func.sum(Ingredient.quantity * (Product.package_price / Product.package_weight)).desc()).all()
            cost_distribution_data = {'labels': [row[0] for row in cost_per_category_query],'data': [float(row[1]) if row[1] is not None else 0 for row in cost_per_category_query]}
            category_orders = load_category_order()
            sorted_dish_category_names = [cat.name for cat in all_dish_categories]
            custom_sorted_dish_names = [name for name in category_orders.get('dishes', []) if name in sorted_dish_category_names]
            custom_sorted_dish_names += [name for name in sorted_dish_category_names if name not in custom_sorted_dish_names]
            composed_dishes_by_category = OrderedDict()
            for cat_name in custom_sorted_dish_names:
                category = next((cat for cat in all_dish_categories if cat.name == cat_name), None)
                if category:
                    dishes_in_cat = [d for d in category.dishes if not d.is_preparation]
                    if dishes_in_cat:
                        composed_dishes_by_category[cat_name] = dishes_in_cat
            all_product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
            sorted_product_category_names = [cat.name for cat in all_product_categories]
            custom_sorted_product_names = [name for name in category_orders.get('products', []) if name in sorted_product_category_names]
            custom_sorted_product_names += [name for name in sorted_product_category_names if name not in custom_sorted_product_names]
            products_by_category = OrderedDict()
            for cat_name in custom_sorted_product_names:
                category = next((cat for cat in all_product_categories if cat.name == cat_name), None)
                if category:
                    products_by_category[cat_name] = category.products
            return render_template('index.html', cost_distribution_json=jsonify(cost_distribution_data).get_data(as_text=True), composed_dishes_by_category=composed_dishes_by_category, products_by_category=products_by_category)

        # --- CLI Commando voor de seeder ---
        @app.cli.command("seed-db")
        def seed_db_command():
            """Vult de database met initiële data als deze leeg is."""
            seed_data()

    return app
app = create_app()
# Deze code wordt uitgevoerd als je het script direct start
if __name__ == '__main__':
    app.run(debug=True, port=5001)