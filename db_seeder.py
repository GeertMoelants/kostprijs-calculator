# db_seeder.py
import pandas as pd
import numpy as np  # Belangrijk: importeer numpy
import os
from models import db, Category, Supplier, Product, DishCategory, Dish, Ingredient
import sys

# Definieer de basisdirectory voor robuuste bestandspaden
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def seed_data():
    """Vult de database met data uit de schone, geëxporteerde CSV-bestanden."""
    print("Start seeding database from exported CSVs...")

    try:
        # Verwijder data in de JUISTE VOLGORDE (één keer is genoeg)
        db.session.query(Ingredient).delete()
        db.session.query(Dish).delete()
        db.session.query(Product).delete()
        db.session.query(Category).delete()
        db.session.query(DishCategory).delete()
        db.session.query(Supplier).delete()
        db.session.commit()
        
        # --- Seeding start hier ---
        
        # 1. Tabellen zonder afhankelijkheden
        category_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'category.csv'), sep=';')
        db.engine.execute(Category.__table__.insert(), category_df.to_dict(orient='records'))
        print("✅ category.csv succesvol geseed.")
        
        dish_category_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'dish_category.csv'), sep=';')
        db.engine.execute(DishCategory.__table__.insert(), dish_category_df.to_dict(orient='records'))
        print("✅ dish_category.csv succesvol geseed.")
        
        supplier_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'supplier.csv'), sep=';')
        db.engine.execute(Supplier.__table__.insert(), supplier_df.to_dict(orient='records'))
        print("✅ supplier.csv succesvol geseed.")

        # 2. Producten
        product_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'product.csv'), sep=';')
        # Converteer numpy types naar Python types
        product_df = product_df.replace({np.nan: None})
        db.engine.execute(Product.__table__.insert(), product_df.to_dict(orient='records'))
        print("✅ Producten succesvol geseed.")

        # 3. Gerechten
        dish_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'dish.csv'), sep=';')
        # Converteer numpy types naar Python types
        dish_df = dish_df.replace({np.nan: None})
        db.engine.execute(Dish.__table__.insert(), dish_df.to_dict(orient='records'))
        print("✅ Gerechten succesvol geseed.")

        # 4. Ingrediënten (HIER ZAT DE FOUT)
        ingredient_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'ingredient.csv'), sep=';')
        
        # Hernoem kolom voor consistentie met model
        ingredient_df.rename(columns={'dish_id': 'parent_dish_id'}, inplace=True)
        
        # CONVERSIE STAP: Zet alle numpy-types om naar standaard Python-types
        ingredient_df = ingredient_df.replace({np.nan: None})
        
        # Converteer alle kolommen die getallen moeten zijn
        for col in ['id', 'parent_dish_id', 'product_id', 'preparation_id']:
            if col in ingredient_df.columns:
                ingredient_df[col] = ingredient_df[col].apply(lambda x: int(x) if pd.notna(x) else None)
        
        ingredient_df['quantity'] = ingredient_df['quantity'].astype(float)
        
        # Voeg de opgeschoonde data toe aan de database
        records = ingredient_df.to_dict(orient='records')
        db.engine.execute(Ingredient.__table__.insert(), records)
        print("✅ Ingrediënten succesvol geseed.")
        
        db.session.commit()
        print("\n🎉 Database succesvol gevuld met de nieuwe data!")

    except FileNotFoundError as e:
        print(f"❌ FOUT: Het bestand '{e.filename}' werd niet gevonden. Zorg ervoor dat alle CSV-bestanden in een 'data' map staan.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Een onverwachte fout is opgetreden: {e}")
        db.session.rollback()
        sys.exit(1)