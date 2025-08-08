# routes/dishes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Dish, DishCategory, Product, Ingredient, Category as ProductCategory
from category_order_manager import load_category_order, save_category_order

dish_bp = Blueprint('dishes', __name__, template_folder='../templates')

def get_or_create_dish_category(name):
    """Hulpfunctie om een gerecht-categorie op te halen of aan te maken als deze niet bestaat."""
    if not name: return None
    instance = DishCategory.query.filter_by(name=name).first()
    if not instance:
        instance = DishCategory(name=name)
        db.session.add(instance)
    return instance

@dish_bp.route('/manage_dishes')
def manage_dishes():
    """Toont een overzicht van alle eindgerechten (geen bereidingen)."""
    dishes = Dish.query.filter_by(is_preparation=False).order_by(Dish.name).all()
    return render_template('manage_dishes.html', composed_dishes=dishes)

def process_dish_form(dish):
    """Hulpfunctie om de formulierdata voor een gerecht te verwerken."""
    dish.name = request.form.get('dish_name', '').strip()
    dish.profit_type = request.form['profit_type']
    try:
        dish.profit_value = float(request.form.get('profit_value', '0').replace(',', '.'))
    except (ValueError, TypeError):
        dish.profit_value = 0

    # Verwerk de categorie
    cat_id = request.form.get('dish_category')
    cat_name = ''
    if cat_id == 'new_dish_category':
        cat_name = request.form.get('new_category_name', '').strip()
    elif cat_id:
        category_obj = DishCategory.query.get(cat_id)
        if category_obj:
            cat_name = category_obj.name
    dish.dish_category = get_or_create_dish_category(cat_name)

    # Verwijder de oude ingrediënten en voeg de nieuwe toe
    Ingredient.query.filter_by(parent_dish_id=dish.id).delete(synchronize_session=False)
    
    ingredient_types = request.form.getlist('ingredient_type[]')
    ingredient_ids = request.form.getlist('ingredient_id[]')
    quantities = request.form.getlist('quantity[]')

    for type, id_str, qty_str in zip(ingredient_types, ingredient_ids, quantities):
        if id_str and qty_str:
            try:
                quantity = float(qty_str.replace(',', '.'))
            except (ValueError, TypeError):
                quantity = 0
            
            if quantity > 0:
                ingredient_id = int(id_str)
                new_ingredient = Ingredient(
                    parent_dish_id=dish.id,
                    product_id=ingredient_id if type == 'product' else None,
                    preparation_id=ingredient_id if type == 'preparation' else None,
                    quantity=quantity
                )
                db.session.add(new_ingredient)
@dish_bp.route('/create', methods=['GET', 'POST'])
def create_dish():
    """Pagina voor het aanmaken van een nieuw gerecht."""
    if request.method == 'POST':
        name = request.form.get('dish_name', '').strip()
        if not name or Dish.query.filter_by(name=name).first():
            flash(f"Gerechtnaam '{name}' is ongeldig of bestaat al.", "danger")
            return redirect(url_for('dishes.create_dish'))
        
        # Maak eerst het gerecht aan en commit om een ID te krijgen
        new_dish = Dish(is_preparation=False)
        
        # Vul nu de rest van de data in en verwerk de ingrediënten
        process_dish_form(new_dish)
        db.session.add(new_dish)
        db.session.commit()

        flash(f"Gerecht '{new_dish.name}' succesvol aangemaakt!", "success")
        return redirect(url_for('dishes.manage_dishes'))

    # Data voorbereiden voor een leeg formulier
    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]
    dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()
    preparations_json = [{'id': p.id, 'name': p.name, 'unit': p.yield_unit, 'unit_price_calculated': p.cost_price_calculated} for p in preparations]

    return render_template(
        'dish_form.html', # FIX: Render de juiste template
        form_action=url_for('dishes.create_dish'),
        all_product_categories_json=product_categories_json,
        all_dish_categories=dish_categories,
        all_preparations_json=preparations_json
    )

@dish_bp.route('/edit/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(dish_id):
    """Pagina voor het bewerken van een bestaand gerecht."""
    dish = Dish.query.get_or_404(dish_id)
    if request.method == 'POST':
        process_dish_form(dish)
        db.session.commit()
        flash(f"Gerecht '{dish.name}' succesvol bijgewerkt!", "success")
        return redirect(url_for('dishes.manage_dishes'))

    # Data voorbereiden voor een ingevuld formulier
    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]
    dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()
    preparations_json = [{'id': p.id, 'name': p.name, 'unit': p.yield_unit, 'unit_price_calculated': p.cost_price_calculated} for p in preparations]
    
    ingredients_data = []
    for ing in dish.ingredients:
        item = { 'quantity': ing.quantity, 'product_id': ing.product_id, 'preparation_id': ing.preparation_id }
        if ing.product:
            item['category_id'] = ing.product.category_id
        ingredients_data.append(item)

    return render_template(
        'dish_form.html', # FIX: Render de juiste template
        dish=dish,
        ingredients_data=ingredients_data,
        form_action=url_for('dishes.edit_dish', dish_id=dish_id),
        all_product_categories_json=product_categories_json,
        all_dish_categories=dish_categories,
        all_preparations_json=preparations_json
    )

@dish_bp.route('/delete/<int:dish_id>', methods=['POST'])
def delete_dish(dish_id):
    """Verwijdert een gerecht."""
    dish = Dish.query.get_or_404(dish_id)
    db.session.delete(dish)
    db.session.commit()
    flash(f"Gerecht '{dish.name}' succesvol verwijderd.", "success")
    return redirect(url_for('dishes.manage_dishes'))

@dish_bp.route('/save_order', methods=['POST'])
def save_order():
    data = request.get_json()
    order_type = data.get('type')
    new_order = data.get('order')
    if order_type and new_order is not None:
        category_orders = load_category_order()
        category_orders[order_type] = new_order
        save_category_order(category_orders)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400