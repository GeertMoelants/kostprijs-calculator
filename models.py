# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = relationship('Product', back_populates='category')

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = relationship('Product', back_populates='supplier')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = relationship('Category', back_populates='products')

    package_weight = db.Column(db.Float, nullable=True)
    package_unit = db.Column(db.String(50), nullable=False, default='Stuks')
    package_price = db.Column(db.Float, nullable=True)
    
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier = relationship('Supplier', back_populates='products')
    
    article_number = db.Column(db.String(100), nullable=True)

    # Relatie met ingrediënten die dit product gebruiken
    ingredients = relationship('Ingredient', back_populates='product')

    @property
    def unit_price_calculated(self):
        if self.package_price is not None and self.package_weight is not None and self.package_weight != 0:
            return self.package_price / self.package_weight
        return 0

class DishCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    dishes = relationship('Dish', back_populates='dish_category')

# --- NIEUW MODEL VOOR BEREIDING-CATEGORIEËN ---
class PreparationCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    preparations = relationship('Dish', back_populates='preparation_category')

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    
    # Categorie voor als het een EINDGERECHT is
    dish_category_id = db.Column(db.Integer, db.ForeignKey('dish_category.id'), nullable=True)
    dish_category = relationship('DishCategory', back_populates='dishes')
    
    # --- NIEUW VELD ---
    # Categorie voor als het een BEREIDING is
    preparation_category_id = db.Column(db.Integer, db.ForeignKey('preparation_category.id'), nullable=True)
    preparation_category = relationship('PreparationCategory', back_populates='preparations')

    profit_type = db.Column(db.String(20), nullable=False, default='percentage')
    profit_value = db.Column(db.Float, nullable=False, default=0)

    is_preparation = db.Column(db.Boolean, default=False, nullable=False, index=True)
    yield_quantity = db.Column(db.Float, nullable=True) # Bv. 1.5 (voor 1.5 Liter saus)
    yield_unit = db.Column(db.String(50), nullable=True) # Bv. "L" of "Kg"

    # Relatie met de ingrediënten die in dit gerecht/deze bereiding zitten
    ingredients = relationship('Ingredient', foreign_keys='Ingredient.parent_dish_id', back_populates='parent_dish', cascade="all, delete-orphan")
    
    # Relatie met de ingrediënten die deze bereiding gebruiken
    used_in_ingredients = relationship('Ingredient', foreign_keys='Ingredient.preparation_id', back_populates='preparation')

    @property
    def cost_price_calculated(self):
        """Berekent de totale kostprijs voor een gerecht, of de kostprijs per eenheid voor een bereiding."""
        total_ingredient_cost = sum(ingredient.cost for ingredient in self.ingredients)
        
        if self.is_preparation:
            if self.yield_quantity and self.yield_quantity > 0:
                return total_ingredient_cost / self.yield_quantity  # Geeft kostprijs per yield_unit (bv. €/L)
            return 0 # Een bereiding zonder opbrengst heeft geen berekenbare eenheidsprijs
        
        return total_ingredient_cost # Geeft de totale kostprijs voor een eindgerecht

    @property
    def selling_price_calculated(self):
        """Berekent de verkoopprijs. Alleen relevant voor eindgerechten."""
        if self.is_preparation:
            return 0 # Een bereiding heeft geen verkoopprijs

        cost = self.cost_price_calculated
        if self.profit_type == 'percentage':
            return cost * (1 + self.profit_value / 100)
        elif self.profit_type == 'multiplier':
            return cost * self.profit_value
        return cost

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Float, nullable=False)
    
    # Het gerecht/de bereiding WAARIN dit ingrediënt wordt gebruikt
    parent_dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)
    parent_dish = relationship('Dish', foreign_keys=[parent_dish_id], back_populates='ingredients')
    
    # De BRON van het ingrediënt (ofwel een basisproduct, ofwel een bereiding)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    preparation_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=True)

    product = relationship('Product', back_populates='ingredients')
    preparation = relationship('Dish', foreign_keys=[preparation_id], back_populates='used_in_ingredients')

    # Zorgt ervoor dat een ingrediënt ofwel een product, ofwel een bereiding is, maar niet beide.
    __table_args__ = (
        db.CheckConstraint(
            '(product_id IS NOT NULL AND preparation_id IS NULL) OR (product_id IS NULL AND preparation_id IS NOT NULL)', 
            name='chk_ingredient_source'
        ),
    )

    @property
    def cost(self):
        """Berekent de totale kost van deze ingrediënt-regel."""
        cost_per_unit = 0
        if self.product:
            cost_per_unit = self.product.unit_price_calculated
        elif self.preparation:
            # De kostprijs van een bereiding is al per eenheid van zijn opbrengst (bv. €/L)
            cost_per_unit = self.preparation.cost_price_calculated
        
        return cost_per_unit * self.quantity
