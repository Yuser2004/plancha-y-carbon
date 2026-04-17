from app import app, db, Pedido, ItemPedido  # Importamos todo desde tu archivo principal

def limpiar_tablas():
    with app.app_context():
        try:
            # 1. Eliminamos los hijos primero para no romper las llaves foráneas
            num_items = db.session.query(ItemPedido).delete()
            # 2. Eliminamos los padres
            num_pedidos = db.session.query(Pedido).delete()
            
            db.session.commit()
            print(f"✅ Limpieza exitosa.")
            print(f"🗑️ Se borraron {num_items} productos de pedidos.")
            print(f"🗑️ Se borraron {num_pedidos} pedidos totales.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al limpiar la base de datos: {e}")

if __name__ == "__main__":
    confirmacion = input("⚠️ ¿Estás seguro de borrar TODOS los pedidos? (s/n): ")
    if confirmacion.lower() == 's':
        limpiar_tablas()
    else:
        print("Operación cancelada.")