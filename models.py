# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import numpy as np

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

    # Relatie met ingrediënten
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

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    
    dish_category_id = db.Column(db.Integer, db.ForeignKey('dish_category.id'), nullable=False)
    dish_category = relationship('DishCategory', back_populates='dishes')
    
    profit_type = db.Column(db.String(20), nullable=False, default='percentage') # 'percentage' or 'multiplier'
    profit_value = db.Column(db.Float, nullable=False, default=0)

    # Relatie met ingrediënten
    ingredients = relationship('Ingredient', back_populates='dish', cascade="all, delete-orphan")

    @property
    def cost_price_calculated(self):
        return sum(ingredient.cost for ingredient in self.ingredients)

    @property
    def selling_price_calculated(self):
        cost = self.cost_price_calculated
        if self.profit_type == 'percentage':
            return cost * (1 + self.profit_value / 100)
        elif self.profit_type == 'multiplier':
            return cost * self.profit_value
        return cost

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Float, nullable=False)
    
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)
    dish = relationship('Dish', back_populates='ingredients')
    
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = relationship('Product', back_populates='ingredients')

    @property
    def cost(self):
        return self.product.unit_price_calculated * self.quantity
