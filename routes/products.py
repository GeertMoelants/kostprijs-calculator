# routes/products.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Product, Category, Supplier

product_bp = Blueprint('products', __name__, template_folder='../templates')

def get_or_create(model, name):
    """Hulpfunctie om een object op te halen of aan te maken als het niet bestaat."""
    if not name:
        return None
    instance = model.query.filter_by(name=name).first()
    if not instance:
        instance = model(name=name)
        db.session.add(instance)
    return instance

@product_bp.route('/manage_products')
def manage_products():
    query = Product.query
    
    selected_category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '').strip().lower()

    if selected_category_id and selected_category_id != 0:
        query = query.filter(Product.category_id == selected_category_id)
    
    if search_query:
        query = query.join(Product.supplier).filter(
            Product.name.ilike(f'%{search_query}%') |
            Supplier.name.ilike(f'%{search_query}%')
        )

    products = query.order_by(Product.name).all()
    all_categories = Category.query.order_by(Category.name).all()

    return render_template(
        'manage_products.html',
        base_products=products,
        all_categories=all_categories,
        selected_category_id=selected_category_id,
        search_query=request.args.get('search', '')
    )

@product_bp.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name or Product.query.filter_by(name=name).first():
            flash(f"Productnaam '{name}' is ongeldig of bestaat al.", "danger")
            return redirect(url_for('products.add_product'))

        cat_name = request.form.get('new_category_name', '').strip() if request.form['category'] == 'new_category' else Category.query.get(request.form['category']).name
        sup_name = request.form.get('new_supplier_name', '').strip() if request.form['supplier'] == 'new_supplier' else Supplier.query.get(request.form['supplier']).name

        category = get_or_create(Category, cat_name)
        supplier = get_or_create(Supplier, sup_name)

        if not category or not supplier:
            flash("Categorie en Leverancier mogen niet leeg zijn.", "danger")
            return redirect(url_for('products.add_product'))

        new_product = Product(
            name=name,
            category=category,
            package_weight=request.form.get('package_weight', type=float),
            package_unit=request.form.get('package_unit'),
            package_price=request.form.get('package_price', type=float),
            supplier=supplier,
            article_number=request.form.get('article_number')
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f"Product '{name}' succesvol toegevoegd!", "success")
        return redirect(url_for('products.manage_products'))

    all_categories = Category.query.order_by(Category.name).all()
    all_suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('product_form.html', form_action=url_for('products.add_product'), all_categories=all_categories, all_suppliers=all_suppliers)

@product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name'].strip()
        
        cat_name = request.form.get('new_category_name', '').strip() if request.form['category'] == 'new_category' else Category.query.get(request.form['category']).name
        sup_name = request.form.get('new_supplier_name', '').strip() if request.form['supplier'] == 'new_supplier' else Supplier.query.get(request.form['supplier']).name
        
        product.category = get_or_create(Category, cat_name)
        product.supplier = get_or_create(Supplier, sup_name)

        product.package_weight = request.form.get('package_weight', type=float)
        product.package_unit = request.form.get('package_unit')
        product.package_price = request.form.get('package_price', type=float)
        product.article_number = request.form.get('article_number')
        
        db.session.commit()
        flash(f"Product '{product.name}' succesvol bijgewerkt!", "success")
        return redirect(url_for('products.manage_products'))

    all_categories = Category.query.order_by(Category.name).all()
    all_suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template(
        'product_form.html', 
        product=product,
        product_name=product.name,
        form_action=url_for('products.edit_product', product_id=product.id),
        all_categories=all_categories,
        all_suppliers=all_suppliers
    )

@product_bp.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.ingredients:
        flash(f"Kan '{product.name}' niet verwijderen, het is in gebruik in {len(product.ingredients)} gerecht(en).", "danger")
        return redirect(url_for('products.manage_products'))
    
    db.session.delete(product)
    db.session.commit()
    flash(f"Product '{product.name}' succesvol verwijderd.", "success")
    return redirect(url_for('products.manage_products'))

@product_bp.route('/get_products_by_category_json')
def get_products_by_category_json():
    category_id = request.args.get('category_id', type=int)
    if category_id:
        category = Category.query.get(category_id)
        if category:
            products_data = [{
                'id': p.id,
                'name': p.name,
                'unit_price_calculated': p.unit_price_calculated,
                'package_unit': p.package_unit
            } for p in category.products]
            return jsonify(products_data)
    return jsonify([])
