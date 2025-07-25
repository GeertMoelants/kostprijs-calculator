# routes/dishes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Dish, DishCategory, Product, Ingredient, Category, Category as ProductCategory, PreparationCategory
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
    # Werk de basisgegevens van het gerecht bij
    dish.name = request.form.get('dish_name', '').strip()
    dish.profit_type = request.form['profit_type']
    dish.profit_value = request.form.get('profit_value', type=float)

    # Verwerk de categorie van het gerecht
    cat_id = request.form.get('dish_category')
    cat_name = ''
    if cat_id == 'new_dish_category':
        cat_name = request.form.get('new_category_name', '').strip()
    elif cat_id:
        category_obj = DishCategory.query.get(cat_id)
        if category_obj:
            cat_name = category_obj.name
    dish.dish_category = get_or_create_dish_category(cat_name)

    # --- GECORRIGEERDE LOGICA VOOR INGREDIËNTEN ---
    
    # Stap 1: Verwijder de oude ingrediënten die bij dit gerecht horen.
    # De 'synchronize_session=False' optie is een best practice voor bulk deletes.
    Ingredient.query.filter_by(parent_dish_id=dish.id).delete(synchronize_session=False)

    # Stap 2: Voeg de ingrediënten uit het formulier toe als nieuwe objecten.
    ingredient_types = request.form.getlist('ingredient_type[]')
    ingredient_ids = request.form.getlist('ingredient_id[]')
    quantities = request.form.getlist('quantity[]')

    for type, id_str, qty_str in zip(ingredient_types, ingredient_ids, quantities):
        if id_str and qty_str:
            try:
                quantity = float(qty_str.replace(',', '.'))
                if quantity > 0:
                    ingredient_id = int(id_str)
                    
                    # Maak een volledig nieuw Ingredient object aan.
                    # Geef geen 'id' mee; de database wijst deze zelf toe.
                    new_ingredient = Ingredient(
                        parent_dish_id=dish.id, # Link het aan het huidige gerecht
                        product_id=ingredient_id if type == 'product' else None,
                        preparation_id=ingredient_id if type == 'preparation' else None,
                        quantity=quantity
                    )
                    # Voeg het nieuwe object toe aan de sessie.
                    db.session.add(new_ingredient)
            except (ValueError, TypeError) as e:
                # Negeer ongeldige rijen, of voeg logging toe indien gewenst
                print(f"Skipping invalid ingredient row: {e}")

@dish_bp.route('/dishes/create', methods=['GET', 'POST'])
def create_dish():
    """Pagina voor het aanmaken van een nieuw gerecht."""
    if request.method == 'POST':
        name = request.form.get('dish_name', '').strip()
        if not name or Dish.query.filter_by(name=name).first():
            flash(f"Gerechtnaam '{name}' is ongeldig of bestaat al.", "danger")
            return redirect(url_for('dishes.create_dish'))
        
        new_dish = Dish(is_preparation=False)
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
        'dish_form.html',
        form_action=url_for('dishes.create_dish'),
        all_product_categories_json=product_categories_json,
        all_dish_categories=dish_categories,
        all_preparations_json=preparations_json
    )

@dish_bp.route('/edit/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(dish_id):
    dish = Dish.query.get_or_404(dish_id)
    # Query de juiste modellen voor het formulier
    dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    product_categories = ProductCategory.query.order_by(Category.name).all() # FIX: Was ProductCategory
    products = Product.query.order_by(Product.name).all()
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()

    if request.method == 'POST':
        try:
            # 1. Update de basisgegevens van het gerecht
            dish.name = request.form['name']
            dish.dish_category_id = request.form['dish_category_id']
            dish.profit_type = request.form['profit_type']
            dish.profit_value = float(request.form['profit_value'].replace(',', '.')) if request.form['profit_value'] else 0.0

            # 2. Verwijder alle oude ingrediënten die bij dit gerecht horen.
            # De 'synchronize_session=False' is de sleutel tot de oplossing.
            Ingredient.query.filter_by(parent_dish_id=dish_id).delete(synchronize_session=False)

            # 3. Voeg de nieuwe ingrediënten toe als nieuwe objecten (zonder ID)
            ingredient_types = request.form.getlist('ingredient_type[]')
            ingredient_ids = request.form.getlist('ingredient_id[]')
            quantities = request.form.getlist('quantity[]')

            for i in range(len(ingredient_types)):
                # Zorg ervoor dat de data valide is
                if quantities[i] and ingredient_ids[i]:
                    quantity = float(quantities[i].replace(',', '.'))
                    if quantity > 0:
                        ingredient_id = int(ingredient_ids[i])
                        ingredient_type = ingredient_types[i]

                        # Maak een volledig nieuw Ingredient-object
                        new_ingredient = Ingredient(
                            parent_dish_id=dish.id,
                            product_id=ingredient_id if ingredient_type == 'product' else None,
                            preparation_id=ingredient_id if ingredient_type == 'preparation' else None,
                            quantity=quantity
                        )
                        db.session.add(new_ingredient)
            
            # 4. Commit alle wijzigingen (deletes en adds) in één keer
            db.session.commit()
            
            flash(f"Gerecht '{dish.name}' succesvol bijgewerkt!", 'success')
            return redirect(url_for('dishes.manage_dishes'))

        except Exception as e:
            db.session.rollback()
            flash(f"Fout bij het bijwerken van het gerecht: {e}", 'danger')
            # Stuur terug naar de edit-pagina om de fout te tonen
            return redirect(url_for('dishes.edit_dish', dish_id=dish_id))

    # Voor de GET request, render de template met de juiste data
    return render_template(
        'manage_dishes.html',
        dish_to_edit=dish, 
        dishes=Dish.query.order_by(Dish.name).all(), 
        categories=dish_categories, 
        product_categories=product_categories,
        products=products,
        preparations=preparations
    )

@dish_bp.route('/dishes/delete/<int:dish_id>', methods=['POST'])
def delete_dish(dish_id):
    """Verwijdert een gerecht."""
    dish = Dish.query.filter_by(id=dish_id, is_preparation=False).first_or_404()
    db.session.delete(dish)
    db.session.commit()
    flash(f"Gerecht '{dish.name}' succesvol verwijderd.", "success")
    return redirect(url_for('dishes.manage_dishes'))

# De save_order route blijft ongewijzigd
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
