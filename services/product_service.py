from sqlalchemy.orm import Session
from models.product import Product
from models.batch import ProductBatch
from models.stock import Stock
from models.transaction import Transaction
from models.stock_location import StockLocation
from models.sale import Sale
from datetime import datetime
from typing import List, Dict
from sqlalchemy import func, asc
import uuid
from services.cash_service import add_cash_movement, get_or_create_cash_register

def get_or_create_product(db: Session, name: str, category: str, code: str = None, is_special: bool = False) -> Product:
    if code:
        product = db.query(Product).filter(Product.code == code).first()
    else:
        product = db.query(Product).filter(Product.name == name).first()
    if not product:
        if not code:
            code = f"PROD{uuid.uuid4().hex[:8].upper()}"
        icons = {
            "Calzado": "assets/icons/calzado.png",
            "Liquidos": "assets/icons/liquidos.png",
            "Carnicos": "assets/icons/carnicos.png",
            "Confituras": "assets/icons/confituras.png",
            "Granos": "assets/icons/granos.png",
            "Ropas": "assets/icons/ropas.png",
            "Productos Especiales": "assets/icons/especiales.png"
        }
        category_icon = icons.get(category, "")
        product = Product(
            code=code,
            name=name,
            category=category,
            category_icon=category_icon,
            is_special=is_special
        )
        db.add(product)
        db.flush()
    return product

def add_product_batch(db: Session, product_id: int, purchase_price_cup: float,
                      usd_rate: float, sale_price: float, expiration_date: datetime,
                      supplier: str, quantity: int, user_id: int, is_special: bool = False) -> ProductBatch:
    purchase_price_usd = round(purchase_price_cup / usd_rate, 2)
    batch = ProductBatch(
        product_id=product_id,
        purchase_price_cup=purchase_price_cup,
        purchase_price_usd=purchase_price_usd,
        usd_rate=usd_rate,
        sale_price=sale_price,
        expiration_date=expiration_date,
        supplier=supplier,
        quantity_received=quantity,
        quantity_remaining=quantity
    )
    db.add(batch)
    db.flush()

    location_name = "Especiales" if is_special else "Almacén"
    location = db.query(StockLocation).filter(StockLocation.name == location_name).first()
    if not location:
        location = StockLocation(name=location_name, description=f"Ubicación para {location_name}")
        db.add(location)
        db.flush()

    stock = Stock(batch_id=batch.id, location_id=location.id, quantity=quantity)
    db.add(stock)

    # Transacción CORREGIDA: sin to_location_id, notes. total = costo total de la entrada
    transaction = Transaction(
        type="entry",
        batch_id=batch.id,
        quantity=quantity,
        total=quantity * purchase_price_cup,   # costo total
        user_id=user_id
    )
    db.add(transaction)
    db.commit()
    db.refresh(batch)
    return batch

def add_multiple_batches(db: Session, products_data: List[Dict], user_id: int) -> List[ProductBatch]:
    batches = []
    for data in products_data:
        product = get_or_create_product(
            db,
            data["name"],
            data["category"],
            code=data.get("code"),
            is_special=data.get("is_special", False)
        )
        batch = add_product_batch(
            db=db,
            product_id=product.id,
            purchase_price_cup=data["purchase_price_cup"],
            usd_rate=data["usd_rate"],
            sale_price=data["sale_price"],
            expiration_date=data["expiration_date"],
            supplier=data["supplier"],
            quantity=data["quantity"],
            user_id=user_id,
            is_special=data.get("is_special", False)
        )
        batches.append(batch)
    return batches

def transfer_products(db: Session, items: List[tuple], user_id: int) -> List[dict]:
    warehouse = db.query(StockLocation).filter(StockLocation.name == "Almacén").first()
    sales_floor = db.query(StockLocation).filter(StockLocation.name == "Piso").first()
    if not warehouse or not sales_floor:
        raise Exception("Ubicaciones no encontradas")
    results = []
    for product_id, quantity, _ in items:
        batches = (
            db.query(ProductBatch)
            .join(Stock, Stock.batch_id == ProductBatch.id)
            .filter(Stock.location_id == warehouse.id)
            .filter(Stock.quantity > 0)
            .filter(ProductBatch.product_id == product_id)
            .order_by(asc(ProductBatch.created_at))
            .all()
        )
        remaining = quantity
        for batch in batches:
            stock_wh = db.query(Stock).filter(Stock.batch_id == batch.id, Stock.location_id == warehouse.id).first()
            if not stock_wh or stock_wh.quantity == 0:
                continue
            take = min(stock_wh.quantity, remaining)
            if take == 0:
                continue
            stock_wh.quantity -= take
            stock_floor = db.query(Stock).filter(Stock.batch_id == batch.id, Stock.location_id == sales_floor.id).first()
            if stock_floor:
                stock_floor.quantity += take
            else:
                stock_floor = Stock(batch_id=batch.id, location_id=sales_floor.id, quantity=take)
                db.add(stock_floor)
            # Transacción CORREGIDA: sin from_location_id, to_location_id, notes. total = 0 (transferencia)
            trans = Transaction(
                type="transfer",
                batch_id=batch.id,
                quantity=take,
                total=0.0,
                user_id=user_id
            )
            db.add(trans)
            remaining -= take
            if remaining == 0:
                break
        if remaining > 0:
            raise Exception(f"No hay suficiente stock para el producto ID {product_id}")
        results.append({"product_id": product_id, "quantity": quantity})
    db.commit()
    return results

def register_sale(db: Session, items: List[Dict], payment_method: str,
                  total: float, change_given: float, user_id: int) -> int:
    sales_floor = db.query(StockLocation).filter(StockLocation.name == "Piso").first()
    if not sales_floor:
        raise Exception("Ubicación 'Piso' no encontrada")
    transaction_ids = []
    for item in items:
        batch_id = item["batch_id"]
        quantity = item["quantity"]
        price = item["price"]           # precio unitario de venta
        stock = db.query(Stock).filter(
            Stock.batch_id == batch_id,
            Stock.location_id == sales_floor.id
        ).first()
        if not stock or stock.quantity < quantity:
            raise Exception(f"Stock insuficiente para el lote {batch_id}")
        stock.quantity -= quantity
        # Transacción CORREGIDA: total = quantity * price, sin price, from_location_id, notes
        trans = Transaction(
            type="sale",
            batch_id=batch_id,
            quantity=quantity,
            total=quantity * price,
            user_id=user_id
        )
        db.add(trans)
        db.flush()
        transaction_ids.append(trans.id)
    # Registrar la venta global (en tabla Sale)
    sale = Sale(
        transaction_id=transaction_ids[0] if transaction_ids else 0,
        payment_method=payment_method,
        total=total,
        change_given=change_given,
        receipt_printed=0
    )
    db.add(sale)
    db.flush()  # Para obtener el ID de la venta sin hacer commit aún

    # Obtener o crear la caja principal (sin argumentos adicionales)
    cash_reg = get_or_create_cash_register(db)   # <--- corregido

    # Registrar el movimiento de caja (ingreso por venta)
    add_cash_movement(
        db=db,
        register_id=cash_reg.id,
        movement_type="sale",
        amount=total,
        currency="CUP",
        description=f"Venta #{sale.id} - {payment_method}",
        reference_id=sale.id,
        user_id=user_id   
    )
def process_return(db: Session, sale_id: int, items: List[Dict], admin_user_id: int) -> int:
    """
    Procesa la devolución de productos de una venta.
    items: lista de {"batch_id": int, "quantity": int}
    """
    sales_floor = db.query(StockLocation).filter(StockLocation.name == "Piso").first()
    if not sales_floor:
        raise Exception("Ubicación 'Piso' no encontrada")
    
    # Obtener la venta original
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise Exception("Venta no encontrada")
    
    for item in items:
        batch_id = item["batch_id"]
        quantity = item["quantity"]
        # Verificar que el lote existe y tiene stock suficiente en piso (opcional, podría devolverse aunque no haya stock físico)
        stock = db.query(Stock).filter(
            Stock.batch_id == batch_id,
            Stock.location_id == sales_floor.id
        ).first()
        if stock:
            stock.quantity += quantity   # Devolver stock al piso
        else:
            # Si no existía, crearlo
            stock = Stock(batch_id=batch_id, location_id=sales_floor.id, quantity=quantity)
            db.add(stock)
        
        # Registrar transacción de devolución (tipo 'return')
        trans = Transaction(
            type="return",
            to_location_id=sales_floor.id,   # se devuelve al piso
            batch_id=batch_id,
            quantity=quantity,
            user_id=admin_user_id,
            notes=f"Devolución de venta #{sale_id}"
        )
        db.add(trans)
    
    # Opcional: ajustar el total de la venta original o crear un registro de devolución
    # Por simplicidad, solo actualizamos stock y transacciones
    # Después de db.add(sale) y antes de db.commit()
    for item in items_for_sale:
        sale_item = SaleItem(
            sale_id=sale.id,
            batch_id=item["batch_id"],
            quantity=item["quantity"],
            price=item["price"]
        )
    db.add(sale_item)
   
    db.commit()
    db.refresh(sale)
    return sale.id