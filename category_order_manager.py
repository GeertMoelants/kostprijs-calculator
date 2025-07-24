# category_order_manager.py
import json

ORDER_FILE = 'category_order.json'

def load_category_order():
    """Laadt de sorteervolgorde van categorieën uit een JSON-bestand."""
    try:
        with open(ORDER_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Retourneer een standaardstructuur als het bestand niet bestaat of corrupt is
        return {'dishes': [], 'products': []}

def save_category_order(order_data):
    """Slaat de sorteervolgorde van categorieën op in een JSON-bestand."""
    with open(ORDER_FILE, 'w') as f:
        json.dump(order_data, f, indent=4)

