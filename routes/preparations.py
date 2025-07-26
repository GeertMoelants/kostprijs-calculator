# routes/preparations.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Dish, Ingredient, Category as ProductCategory, PreparationCategory

preparation_bp = Blueprint('preparations', __name__, template_folder='../templates')

def get_or_create_prep_category(name):
    """Hulpfunctie om een bereiding-categorie op te halen of aan te maken."""
    if not name: return None
    instance = PreparationCategory.query.filter_by(name=name).first()
    if not instance:
        instance = PreparationCategory(name=name)
        db.session.add(instance)
    return instance

def process_preparation_form(dish):
    """Hulpfunctie om de formulierdata voor een bereiding te verwerken."""
    dish.name = request.form.get('preparation_name', '').strip()
    dish.yield_quantity = float(request.form.get('yield_quantity', '1.0').replace(',', '.'))
    dish.yield_unit = request.form.get('yield_unit', '').strip()
    
    cat_id = request.form.get('preparation_category')
    cat_name = ''
    if cat_id == 'new_prep_category':
        cat_name = request.form.get('new_category_name', '').strip()
    elif cat_id:
        category_obj = PreparationCategory.query.get(cat_id)
        if category_obj:
            cat_name = category_obj.name
    dish.preparation_category = get_or_create_prep_category(cat_name)

    # Verwijder de oude ingrediënten en voeg de nieuwe toe
    Ingredient.query.filter_by(parent_dish_id=dish.id).delete(synchronize_session=False)

    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    for id_str, qty_str in zip(product_ids, quantities):
        if id_str and qty_str:
            quantity = float(qty_str.replace(',', '.'))
            if quantity > 0:
                new_ingredient = Ingredient(
                    parent_dish_id=dish.id,
                    product_id=int(id_str),
                    quantity=quantity
                )
                db.session.add(new_ingredient)

@preparation_bp.route('/manage_preparations')
def manage_preparations():
    """Toont een overzicht van alle bereidingen."""
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()
    return render_template('manage_preparations.html', preparations=preparations)

@preparation_bp.route('/create', methods=['GET', 'POST'])
def create_preparation():
    """Pagina voor het aanmaken van een nieuwe bereiding."""
    if request.method == 'POST':
        name = request.form.get('preparation_name', '').strip()
        if not name or Dish.query.filter_by(name=name).first():
            flash(f"Naam '{name}' is ongeldig of bestaat al.", "danger")
            return redirect(url_for('preparations.create_preparation'))
        
        # Maak eerst de bereiding aan en commit om een ID te krijgen
        new_preparation = Dish(is_preparation=True)
        db.session.add(new_preparation)
        db.session.commit()
        
        # Vul nu de rest van de data in en verwerk de ingrediënten
        process_preparation_form(new_preparation)
        db.session.commit()

        flash(f"Bereiding '{new_preparation.name}' succesvol aangemaakt!", "success")
        return redirect(url_for('preparations.manage_preparations'))

    # Data voorbereiden voor een leeg formulier
    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]
    prep_categories = PreparationCategory.query.order_by(PreparationCategory.name).all()

    return render_template(
        'preparation_form.html',
        form_action=url_for('preparations.create_preparation'),
        all_product_categories_json=product_categories_json,
        all_prep_categories=prep_categories
    )

@preparation_bp.route('/edit/<int:dish_id>', methods=['GET', 'POST'])
def edit_preparation(dish_id):
    """Pagina voor het bewerken van een bestaande bereiding."""
    preparation = Dish.query.filter_by(id=dish_id, is_preparation=True).first_or_404()
    if request.method == 'POST':
        process_preparation_form(preparation)
        db.session.commit()
        flash(f"Bereiding '{preparation.name}' succesvol bijgewerkt!", "success")
        return redirect(url_for('preparations.manage_preparations'))

    # Data voorbereiden voor een ingevuld formulier
    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]
    prep_categories = PreparationCategory.query.order_by(PreparationCategory.name).all()
    
    ingredients_data = []
    for ing in preparation.ingredients:
        item = { 'quantity': ing.quantity, 'product_id': ing.product_id }
        if ing.product:
            item['category_id'] = ing.product.category_id
        ingredients_data.append(item)

    return render_template(
        'preparation_form.html',
        preparation=preparation,
        ingredients_data=ingredients_data,
        form_action=url_for('preparations.edit_preparation', dish_id=dish_id),
        all_product_categories_json=product_categories_json,
        all_prep_categories=prep_categories
    )

@preparation_bp.route('/delete/<int:dish_id>', methods=['POST'])
def delete_preparation(dish_id):
    """Verwijdert een bereiding."""
    preparation = Dish.query.filter_by(id=dish_id, is_preparation=True).first_or_404()
    db.session.delete(preparation)
    db.session.commit()
    flash(f"Bereiding '{preparation.name}' succesvol verwijderd.", "success")
    return redirect(url_for('preparations.manage_preparations'))