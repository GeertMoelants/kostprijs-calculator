# routes/dishes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Dish, DishCategory, Product, Ingredient, Category, Category as ProductCategory, PreparationCategory
from category_order_manager import load_category_order, save_category_order

dish_bp = Blueprint('dishes', __name__, template_folder='../templates')

def get_or_create(model, name):
    """Hulpfunctie om een gerecht-categorie op te halen of aan te maken als deze niet bestaat."""
    if not name: 
        return None
    instance = model.query.filter_by(name=name).first()
    if not instance:
        instance = model(name=name)
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
    dish.dish_category = get_or_create(cat_name)

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

# routes/dishes.py

@dish_bp.route('/create', methods=['GET', 'POST'])
def create_dish():
    # Deze queries zijn nodig om het formulier op te bouwen
    dish_categories = DishCategory.query.order_by(DishCategory.name).all()
    product_categories = Category.query.order_by(Category.name).all()
    products = Product.query.order_by(Product.name).all()
    preparations = Dish.query.filter_by(is_preparation=True).order_by(Dish.name).all()

    if request.method == 'POST':
        try:
            # --- STAP 1: Maak het gerecht aan en sla het op ---
            new_dish = Dish(
                name=request.form['name'],
                dish_category_id=request.form['dish_category_id'],
                profit_type=request.form['profit_type'],
                profit_value=float(request.form['profit_value'].replace(',', '.')) if request.form['profit_value'] else 0.0,
                is_preparation=False # Een gerecht is geen bereiding
            )
            # Voeg toe en commit onmiddellijk om een ID te genereren
            db.session.add(new_dish)
            db.session.commit()

            # --- STAP 2: Maak de ingrediënten aan en koppel ze aan het nieuwe gerecht ---
            ingredient_types = request.form.getlist('ingredient_type[]')
            ingredient_ids = request.form.getlist('ingredient_id[]')
            quantities = request.form.getlist('quantity[]')

            for i in range(len(ingredient_types)):
                if quantities[i] and ingredient_ids[i]:
                    quantity = float(quantities[i].replace(',', '.'))
                    if quantity > 0:
                        ingredient_id = int(ingredient_ids[i])
                        ingredient_type = ingredient_types[i]

                        # Maak een Ingredient-object en link het via het ID
                        new_ingredient = Ingredient(
                            parent_dish_id=new_dish.id, # Gebruik het ID van het zojuist gemaakte gerecht
                            product_id=ingredient_id if ingredient_type == 'product' else None,
                            preparation_id=ingredient_id if ingredient_type == 'preparation' else None,
                            quantity=quantity
                        )
                        db.session.add(new_ingredient)
            
            # --- STAP 3: Commit de nieuwe ingrediënten ---
            db.session.commit()
            
            flash(f"Gerecht '{new_dish.name}' succesvol aangemaakt!", 'success')
            return redirect(url_for('dishes.manage_dishes'))

        except Exception as e:
            db.session.rollback()
            flash(f"Fout bij het aanmaken van het gerecht: {e}", 'danger')
            return redirect(url_for('dishes.create_dish'))

    # Voor de GET request, render de template
    return render_template(
        'manage_dishes.html',
        dish_to_edit=None, # Geen gerecht om te bewerken, we maken een nieuwe aan
        dishes=Dish.query.order_by(Dish.name).all(),
        categories=dish_categories,
        product_categories=product_categories,
        products=products,
        preparations=preparations,
        is_create_page=True # Een vlag om de template te vertellen dat dit de "create" pagina is
    )

@dish_bp.route('/dishes/edit/<int:dish_id>', methods=['GET', 'POST'])
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
        'dishes_form.html',
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
