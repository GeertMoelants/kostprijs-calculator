# db_seeder.py
import pandas as pd
import numpy as np
import os
from models import db, Category, Supplier, Product, DishCategory, Dish, Ingredient
import sys

# Definieer de basisdirectory voor robuuste bestandspaden
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def seed_data():
    """
    Vult de database met initiële data, maar ENKEL als de database leeg is.
    Dit voorkomt het overschrijven van live data.
    """
    
    # --- DE BELANGRIJKE CONTROLE ---
    # Controleer of er al data bestaat (bv. in de Category tabel).
    # Als dat zo is, stop het script onmiddellijk.
    if Category.query.first():
        print("✅ Database bevat al data. Seeden wordt overgeslagen.")
        return

    print("Database is leeg. Start seeding database from exported CSVs...")

    try:
        # --- Seeding start hier (verwijder-statements zijn niet meer nodig) ---
        
        # 1. Tabellen zonder afhankelijkheden
        category_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'category.csv'))
        db.session.execute(Category.__table__.insert(), category_df.to_dict(orient='records'))
        print("✅ category.csv succesvol geseed.")
        
        dish_category_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'dish_category.csv'))
        db.session.execute(DishCategory.__table__.insert(), dish_category_df.to_dict(orient='records'))
        print("✅ dish_category.csv succesvol geseed.")
        
        supplier_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'supplier.csv'))
        db.session.execute(Supplier.__table__.insert(), supplier_df.to_dict(orient='records'))
        print("✅ supplier.csv succesvol geseed.")

        # 2. Producten
        product_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'product.csv'))
        product_df = product_df.replace({np.nan: None})
        db.session.execute(Product.__table__.insert(), product_df.to_dict(orient='records'))
        print("✅ Producten succesvol geseed.")

        # 3. Gerechten
        dish_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'dish.csv'))
        dish_df = dish_df.replace({np.nan: None})
        db.session.execute(Dish.__table__.insert(), dish_df.to_dict(orient='records'))
        print("✅ Gerechten succesvol geseed.")

        # 4. Ingrediënten
        ingredient_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'ingredient.csv'))
        ingredient_df.rename(columns={'dish_id': 'parent_dish_id'}, inplace=True)
        ingredient_df = ingredient_df.replace({np.nan: None})
        
        for col in ['id', 'parent_dish_id', 'product_id', 'preparation_id']:
            if col in ingredient_df.columns:
                ingredient_df[col] = ingredient_df[col].apply(lambda x: int(x) if pd.notna(x) else None)
        
        ingredient_df['quantity'] = ingredient_df['quantity'].astype(float)
        
        db.session.execute(Ingredient.__table__.insert(), ingredient_df.to_dict(orient='records'))
        print("✅ Ingrediënten succesvol geseed.")
        
        db.session.commit()
        print("\n🎉 Database succesvol gevuld met de initiële data!")

    except Exception as e:
        print(f"❌ Een onverwachte fout is opgetreden tijdens het seeden: {e}")
        db.session.rollback()
        sys.exit(1)