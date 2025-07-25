# routes/preparations.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Dish, Product, Ingredient, Category as ProductCategory, PreparationCategory

preparation_bp = Blueprint('preparations', __name__, template_folder='../templates')

def get_or_create_prep_category(name):
    """Hulpfunctie om een bereiding-categorie op te halen of aan te maken als deze niet bestaat."""
    if not name: return None
    instance = PreparationCategory.query.filter_by(name=name).first()
    if not instance:
        instance = PreparationCategory(name=name)
        db.session.add(instance)
    return instance

@preparation_bp.route('/manage_preparations')
def manage_preparations():
    """Toont een overzicht van alle bereidingen."""
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()
    return render_template('manage_preparations.html', preparations=preparations)

@preparation_bp.route('/preparations/create', methods=['GET', 'POST'])
def create_preparation():
    """Pagina voor het aanmaken van een nieuwe bereiding."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name or Dish.query.filter_by(name=name).first():
            flash(f"Naam '{name}' is ongeldig of bestaat al.", "danger")
            return redirect(url_for('preparations.create_preparation'))

        # Verwerk de categorie voor de bereiding
        cat_id = request.form.get('preparation_category')
        cat_name = ''
        if cat_id == 'new_category':
            cat_name = request.form.get('new_category_name', '').strip()
        elif cat_id:
            category_obj = PreparationCategory.query.get(cat_id)
            if category_obj:
                cat_name = category_obj.name
        
        category = get_or_create_prep_category(cat_name)

        new_preparation = Dish(
            name=name,
            is_preparation=True,
            preparation_category=category,
            yield_quantity=request.form.get('yield_quantity', type=float),
            yield_unit=request.form.get('yield_unit')
        )

        # Ingrediënten kunnen alleen basisproducten zijn
        product_ids = request.form.getlist('ingredient_product_id[]')
        quantities = request.form.getlist('quantity[]')
        for product_id, qty_str in zip(product_ids, quantities):
            if product_id and qty_str:
                quantity = float(qty_str.replace(',', '.'))
                if quantity > 0:
                    new_preparation.ingredients.append(Ingredient(product_id=int(product_id), quantity=quantity))

        db.session.add(new_preparation)
        db.session.commit()
        flash(f"Bereiding '{name}' succesvol aangemaakt!", "success")
        return redirect(url_for('preparations.manage_preparations'))

    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]
    prep_categories = PreparationCategory.query.order_by(PreparationCategory.name).all()

    return render_template(
        'preparation_form.html',
        form_action=url_for('preparations.create_preparation'),
        all_product_categories_json=product_categories_json,
        all_prep_categories=prep_categories
    )

@preparation_bp.route('/preparations/edit/<int:prep_id>', methods=['GET', 'POST'])
def edit_preparation(prep_id):
    """Pagina voor het bewerken van een bestaande bereiding."""
    preparation = Dish.query.filter_by(id=prep_id, is_preparation=True).first_or_404()
    if request.method == 'POST':
        preparation.name = request.form.get('name', '').strip()
        preparation.yield_quantity = request.form.get('yield_quantity', type=float)
        preparation.yield_unit = request.form.get('yield_unit')

        # Verwerk de categorie voor de bereiding
        cat_id = request.form.get('preparation_category')
        cat_name = ''
        if cat_id == 'new_category':
            cat_name = request.form.get('new_category_name', '').strip()
        elif cat_id:
            category_obj = PreparationCategory.query.get(cat_id)
            if category_obj:
                cat_name = category_obj.name
        preparation.preparation_category = get_or_create_prep_category(cat_name)

        # Verwijder oude ingrediënten en voeg de nieuwe toe
        Ingredient.query.filter_by(parent_dish_id=prep_id).delete()
        product_ids = request.form.getlist('ingredient_product_id[]')
        quantities = request.form.getlist('quantity[]')
        for product_id, qty_str in zip(product_ids, quantities):
            if product_id and qty_str:
                quantity = float(qty_str.replace(',', '.'))
                if quantity > 0:
                    db.session.add(Ingredient(parent_dish_id=prep_id, product_id=int(product_id), quantity=quantity))
        
        db.session.commit()
        flash(f"Bereiding '{preparation.name}' succesvol bijgewerkt!", "success")
        return redirect(url_for('preparations.manage_preparations'))

    product_categories = ProductCategory.query.order_by(ProductCategory.name).all()
    product_categories_json = [{'id': cat.id, 'name': cat.name} for cat in product_categories]
    ingredients_data = [{'product_id': ing.product_id, 'quantity': ing.quantity, 'category_id': ing.product.category_id} for ing in preparation.ingredients]
    prep_categories = PreparationCategory.query.order_by(PreparationCategory.name).all()

    return render_template(
        'preparation_form.html',
        preparation=preparation,
        ingredients_data=ingredients_data,
        form_action=url_for('preparations.edit_preparation', prep_id=prep_id),
        all_product_categories_json=product_categories_json,
        all_prep_categories=prep_categories
    )

@preparation_bp.route('/preparations/delete/<int:prep_id>', methods=['POST'])
def delete_preparation(prep_id):
    """Verwijdert een bereiding."""
    preparation = Dish.query.filter_by(id=prep_id, is_preparation=True).first_or_404()

    if preparation.used_in_ingredients:
        flash(f"Kan '{preparation.name}' niet verwijderen, de bereiding is nog in gebruik in andere gerechten.", "danger")
        return redirect(url_for('preparations.manage_preparations'))

    db.session.delete(preparation)
    db.session.commit()
    flash(f"Bereiding '{preparation.name}' succesvol verwijderd.", "success")
    return redirect(url_for('preparations.manage_preparations'))

@preparation_bp.route('/api/get_preparations_json')
def get_preparations_json():
    """API endpoint om alle bereidingen als JSON terug te geven."""
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()
    preparations_data = [{
        'id': prep.id,
        'name': f"{prep.name} ({prep.yield_unit})", # Toon de eenheid in de naam
        'unit_price_calculated': prep.cost_price_calculated,
        'unit': prep.yield_unit
    } for prep in preparations]
    return jsonify(preparations_data)
