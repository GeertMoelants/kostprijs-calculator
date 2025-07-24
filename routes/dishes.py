# routes/dishes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Dish, DishCategory, Product, Ingredient, Category as ProductCategory
from category_order_manager import load_category_order, save_category_order

dish_bp = Blueprint('dishes', __name__, template_folder='../templates')

def get_or_create(model, name):
    """Hulpfunctie om een object op te halen of aan te maken als het niet bestaat."""
    if not name:
        return None
    instance = model.query.filter_by(name=name).first()
    if not instance:
        instance = model(name=name)
        db.session.add(instance)
    return instance

@dish_bp.route('/manage_dishes')
def manage_dishes():
    dishes = Dish.query.order_by(Dish.name).all()
    return render_template('manage_dishes.html', composed_dishes=dishes)

@dish_bp.route('/dishes/create', methods=['GET', 'POST'])
def create_dish():
    if request.method == 'POST':
        name = request.form['dish_name'].strip()
        if not name or Dish.query.filter_by(name=name).first():
            flash(f"Gerechtnaam '{name}' is ongeldig of bestaat al.", "danger")
            return redirect(url_for('dishes.create_dish'))
        
        cat_name = request.form.get('new_dish_category_name', '').strip() if request.form['dish_category'] == 'new_dish_category' else DishCategory.query.get(request.form['dish_category']).name
        dish_category = get_or_create(DishCategory, cat_name)

        if not dish_category:
            flash("Gerechtcategorie mag niet leeg zijn.", "danger")
            return redirect(url_for('dishes.create_dish'))

        new_dish = Dish(
            name=name,
            dish_category=dish_category,
            profit_type=request.form['profit_type'],
            profit_value=request.form.get('profit_value', type=float)
        )
        
        product_ids = request.form.getlist('ingredient_product_id[]')
        quantities = request.form.getlist('quantity[]')
        for product_id, qty_str in zip(product_ids, quantities):
            if product_id and qty_str:
                quantity = float(qty_str.replace(',', '.'))
                if quantity > 0:
                    ingredient = Ingredient(product_id=int(product_id), quantity=quantity)
                    new_dish.ingredients.append(ingredient)

        db.session.add(new_dish)
        db.session.commit()
        flash(f"Gerecht '{new_dish.name}' succesvol aangemaakt!", "success")
        return redirect(url_for('dishes.manage_dishes'))

    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    
    # Converteer de categorieën naar een formaat dat JSON-vriendelijk is
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]

    return render_template(
        'create_dish.html',
        all_product_categories_json=product_categories_json,
        all_dish_categories=dish_categories
    )

@dish_bp.route('/dishes/edit/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    if request.method == 'POST':
        dish.name = request.form['dish_name'].strip()
        
        cat_name = request.form.get('new_dish_category_name', '').strip() if request.form['dish_category'] == 'new_dish_category' else DishCategory.query.get(request.form['dish_category']).name
        dish.dish_category = get_or_create(DishCategory, cat_name)

        dish.profit_type = request.form['profit_type']
        dish.profit_value = request.form.get('profit_value', type=float)

        Ingredient.query.filter_by(dish_id=dish.id).delete()
        
        product_ids = request.form.getlist('ingredient_product_id[]')
        quantities = request.form.getlist('quantity[]')
        for product_id, qty_str in zip(product_ids, quantities):
             if product_id and qty_str:
                quantity = float(qty_str.replace(',', '.'))
                if quantity > 0:
                    ingredient = Ingredient(dish_id=dish.id, product_id=int(product_id), quantity=quantity)
                    db.session.add(ingredient)
        
        db.session.commit()
        flash(f"Gerecht '{dish.name}' bijgewerkt.", "success")
        return redirect(url_for('dishes.manage_dishes'))

    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    
    # Data voorbereiden voor de template
    ingredients_data = []
    for ing in dish.ingredients:
        ingredients_data.append({
            'product_id': ing.product_id,
            'quantity': ing.quantity,
            'category_id': ing.product.category_id
        })
    
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]

    return render_template(
        'dish_form.html',
        dish=dish,
        ingredients_data=ingredients_data,
        form_action=url_for('dishes.edit_dish', dish_id=dish.id),
        all_product_categories_json=product_categories_json,
        all_dish_categories=dish_categories
    )

@dish_bp.route('/dishes/delete/<int:dish_id>', methods=['POST'])
def delete_dish(dish_id):
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
