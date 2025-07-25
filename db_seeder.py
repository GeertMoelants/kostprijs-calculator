# db_seeder.py
import pandas as pd
from models import db, Category, Supplier, Product, DishCategory, Dish, Ingredient
import sys

def seed_data():
    """Vult de database met data uit de schone, geëxporteerde CSV-bestanden."""
    print("Start seeding database from exported CSVs...")

    try:
        # Belangrijk: lees de bestanden in de juiste volgorde om relatieproblemen te voorkomen
        
        # 1. Tabellen zonder afhankelijkheden
        Category.query.delete()
        category_df = pd.read_csv('category.csv')
        for _, row in category_df.iterrows():
            db.session.add(Category(id=row['id'], name=row['name']))
        
        db.session.commit()
        print("✅ category.csv succesvol geseed.")
        
        DishCategory.query.delete()
        dish_category_df = pd.read_csv('dish_category.csv')
        for _, row in dish_category_df.iterrows():
            db.session.add(DishCategory(id=row['id'], name=row['name']))
            
        db.session.commit()
        print("✅ dish_category.csv succesvol geseed.")    
            
        Supplier.query.delete()
        supplier_df = pd.read_csv('supplier.csv')
        for _, row in supplier_df.iterrows():
            db.session.add(Supplier(id=row['id'], name=row['name']))
        
        db.session.commit()
        print("✅ supplier.csv succesvol geseed.")

        # 2. Producten (afhankelijk van Category en Supplier)
        Product.query.delete()
        product_df = pd.read_csv('product.csv')
        for _, row in product_df.iterrows():
            db.session.add(Product(
                id=row['id'],
                name=row['name'],
                category_id=row['category_id'],
                package_weight=row.get('package_weight'),
                package_unit=row.get('package_unit'),
                package_price=row.get('package_price'),
                supplier_id=row['supplier_id'],
                article_number=row.get('article_number')
            ))
        db.session.commit()
        print("✅ Producten succesvol geseed.")

        # 3. Gerechten (afhankelijk van DishCategory)
        Dish.query.delete()
        dish_df = pd.read_csv('dish.csv')
        for _, row in dish_df.iterrows():
            db.session.add(Dish(
                id=row['id'],
                name=row['name'],
                dish_category_id=row['dish_category_id'],
                profit_type=row['profit_type'],
                profit_value=row['profit_value'],
                is_preparation=row.get('is_preparation', False) # Fallback voor oudere exports
            ))
        db.session.commit()
        print("✅ Gerechten succesvol geseed.")

        # 4. Ingrediënten (afhankelijk van Dish en Product)
        Ingredient.query.delete()
        ingredient_df = pd.read_csv('ingredient.csv')
        for _, row in ingredient_df.iterrows():
            db.session.add(Ingredient(
                id=row['id'],
                quantity=row['quantity'],
                parent_dish_id=row['dish_id'], # Hernoemd in de code, maar dish_id in CSV
                product_id=row.get('product_id'),
                preparation_id=row.get('preparation_id')
            ))
        db.session.commit()
        print("✅ Ingrediënten succesvol geseed.")
        
        print("\n🎉 Database succesvol gevuld met de nieuwe data!")

    except FileNotFoundError as e:
        print(f"❌ FOUT: Het bestand '{e.filename}' werd niet gevonden. Zorg ervoor dat alle 6 de CSV-bestanden in de hoofdmap staan.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Een onverwachte fout is opgetreden: {e}")
        db.session.rollback() # Maak de transactie ongedaan bij een fout
        sys.exit(1)

