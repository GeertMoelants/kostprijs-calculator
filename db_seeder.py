# db_seeder.py
import pandas as pd
import json
from models import db, Category, Supplier, Product, DishCategory, Dish, Ingredient

def safe_float(value):
    """Converteert een waarde veilig naar een float, met ondersteuning voor komma's en lege waarden."""
    s_value = str(value).strip()
    if not s_value or s_value.lower() == 'nan':
        return None
    try:
        return float(s_value.replace(',', '.'))
    except (ValueError, TypeError):
        return None

def seed_data():
    """Vult de database met de initiële data uit de CSV-bestanden."""
    print("Start seeding database...")
    
    # --- Migreer Basisproducten ---
    try:
        products_df = pd.read_csv('geparseerde_basisproducten.csv')
        
        categories = {name: Category(name=name) for name in products_df['category'].dropna().unique()}
        suppliers = {name: Supplier(name=name) for name in products_df['supplier'].dropna().unique()}
        
        db.session.add_all(categories.values())
        db.session.add_all(suppliers.values())
        db.session.commit()

        for _, row in products_df.iterrows():
            product = Product(
                name=row['name'],
                category=categories.get(row['category']),
                package_weight=safe_float(row.get('package_weight')),
                package_unit=row.get('package_unit', 'Stuks'),
                package_price=safe_float(row.get('package_price')),
                supplier=suppliers.get(row['supplier']),
                article_number=row.get('article_number')
            )
            db.session.add(product)
        db.session.commit()
        print("✅ Basisproducten succesvol geseed.")

    except FileNotFoundError:
        print("⚠️ Kon geparseerde_basisproducten.csv niet vinden. Stap overgeslagen.")

    # --- Migreer Samengestelde Gerechten ---
    try:
        dishes_df = pd.read_csv('geparseerde_samengestelde_gerechten.csv')
        
        dish_categories = {name: DishCategory(name=name) for name in dishes_df['dish_category'].dropna().unique()}
        db.session.add_all(dish_categories.values())
        db.session.commit()

        all_products = {p.name: p for p in Product.query.all()}

        for _, row in dishes_df.iterrows():
            dish = Dish(
                name=row['dish_name'],
                dish_category=dish_categories.get(row['dish_category']),
                profit_type=row.get('profit_type', 'percentage'),
                profit_value=safe_float(row.get('profit_value', 0))
            )
            db.session.add(dish)
            
            try:
                # Soms is de JSON dubbel-escaped, probeer dit te herstellen
                ingredients_str = row['ingredients_json'].replace('""', '"')
                ingredients_data = json.loads(ingredients_str)
                
                for ing_data in ingredients_data:
                    product_obj = all_products.get(ing_data['ingredient_name'])
                    if product_obj:
                        ingredient = Ingredient(
                            quantity=safe_float(ing_data['quantity']),
                            dish=dish,
                            product=product_obj
                        )
                        db.session.add(ingredient)
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"⚠️ Fout bij parsen van ingrediënten voor '{row['dish_name']}': {e}")

        db.session.commit()
        print("✅ Samengestelde gerechten succesvol geseed.")

    except FileNotFoundError:
        print("⚠️ Kon geparseerde_samengestelde_gerechten.csv niet vinden. Stap overgeslagen.")
