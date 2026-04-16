from flask import Flask, render_template, request, jsonify, session, redirect, url_for # <--- Agregados session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy import func
import os
import pytz
from datetime import datetime
from functools import wraps
import time

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)

# CONFIGURACIÓN CRÍTICA PARA EL LOGIN
app.secret_key = 'llave_maestra_betty_123' # <--- ESTO ES OBLIGATORIO para usar session

# CONFIGURACIÓN DE BASE DE DATOS (SUPABASE DIRECT)
# Fíjate que ahora cada instrucción tiene su propia línea
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.uqltqertxxqepqerusio:4SDy0OMBL0e3QDKD@aws-1-us-west-2.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}
db = SQLAlchemy(app)
# ==========================================
# SEGURIDAD Y LOGIN
# ==========================================

# Este es el "candado". Si no están logueados, los manda al login.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login_admin'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    error = None
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')

        # Aquí verificamos tus credenciales exactas
        if usuario == 'admin' and password == 'betty':
            session['admin_logged_in'] = True
            return redirect(url_for('view_jefa')) # Los mandamos al dashboard
        else:
            error = "Usuario o contraseña incorrectos."

    return render_template('login.html', error=error)

@app.route('/logout_admin')
def logout_admin():
    session.pop('admin_logged_in', None) # Borramos la sesión
    return redirect(url_for('index'))
def hora_colombia():
    return datetime.now(pytz.timezone('America/Bogota'))

# ==========================================
# MODELOS DE BASE DE DATOS
# ==========================================

class Pedido(db.Model): #CON POSTGRE
    __tablename__ = 'pedido'
    id = db.Column(db.Integer, primary_key=True)
    
    # Punto 4 y 5: Cambiado a String(100) para permitir "Mesa 1" o "Cliente: Carlos (Vitrina)"
    mesa = db.Column(db.String(100), nullable=False) 
    
    # Nombre del mesero que abrió el pedido originalmente
    meser_nombre = db.Column(db.String(100))
    
    # Estados: Pendiente, Listo, Entregado, Pagado
    estado = db.Column(db.String(50), default='Pendiente') 
    
    # MÉTRICAS DE TIEMPO
    creado_en = db.Column(db.DateTime, default=hora_colombia)
    preparado_en = db.Column(db.DateTime)
    entregado_en = db.Column(db.DateTime)

    # Relación con los items
    items = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade="all, delete-orphan")
class ItemPedido(db.Model):
    __tablename__ = 'item_pedido'
    id = db.Column(db.Integer, primary_key=True)
    nombre_producto = db.Column(db.String(100), nullable=False)
    
    # Usamos Float para precios por si acaso, aunque en CO sea entero
    precio_unitario = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    
    # Punto 1: Notas de texto más largas para evitar errores
    nota = db.Column(db.Text, default="")
    
    # Control de cocina
    despachado = db.Column(db.Boolean, default=False)
    
    # Punto 2: Quién pidió este producto específicamente (Auditoría)
    quien_pide = db.Column(db.String(100)) 
    
    # Clave foránea
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
with app.app_context():
    db.create_all()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ==========================================
# DICCIONARIO DE LA CARTA
# ==========================================

CARTA = {
    "FRITOS": [
        {"nombre": "Empanada Papa-Carne", "precio": 2500},
        {"nombre": "Empanada Papa-Pollo", "precio": 2500},
        {"nombre": "Pastel de Yuca", "precio": 3000},
        {"nombre": "Torta de Carne", "precio": 3500},
        {"nombre": "Arepa de Huevo Mixta", "precio": 6500},
    ],
    "FLAUTAS": [
        {"nombre": "FLAUTA RANCHERA", "precio": 4000},
        {"nombre": "FLAUTA HAWAIANA", "precio": 4000},
        {"nombre": "FLAUTA DE POLLO", "precio": 6000},
        {"nombre": "FLAUTA DE CARNE", "precio": 6000},
        {"nombre": "FLAUTA MIXTA", "precio": 6000},
    ],
    "CONOS Y CANASTAS": [
        {"nombre": "CONO MIXTO", "precio": 12000},
        {"nombre": "CONO SOLO CARNE", "precio": 17000},
        {"nombre": "CONO SOLO POLLO", "precio": 12000},
        {"nombre": "CONO RANCHERO", "precio": 14500},
        {"nombre": "CANASTITAS DE PLATANO x3", "precio": 24000},
    ],
    "SANDWICH DE LA CASA": [
        {"nombre": "SANDWICH MIXTO", "precio": 19000},
        {"nombre": "SANDWICH SOLO CARNE", "precio": 24000},
    ],
    "PERROS": [
        {"nombre": "Perro Sencillo", "descripcion": "Salchicha, Cebolla Grille, Quesillo, Ripio, Huevo de Codorniz", "precio": 9500},
        {"nombre": "Perro Zenú", "descripcion": "Salchicha Zenú Long, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 12000},
        {"nombre": "Perro Americano", "descripcion": "Salchicha Americana, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 14500},
        {"nombre": "Perro Hawaiano", "descripcion": "Salchicha Americana, Piña, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 15500},
        {"nombre": "Chori Perro", "descripcion": "Chorizo de Cerdo, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 17000},
        {"nombre": "Perrada", "descripcion": "Tocineta Picada, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 18000},
        {"nombre": "Perro Con Jalapeños", "descripcion": "Salchicha Americana, Carne Desmechada, Jalapeños, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 19000},
        {"nombre": "Perro Americano Especial", "descripcion": "Salchicha Americana, Pollo Desmechado, Cebolla Grille, Quesillo, Ripio, Dos Huevos de Codorniz", "precio": 20500},
        {"nombre": "Perro Mexicano", "descripcion": "Salchicha Americana, Cebolla Morada, Pico de Gallo con Jalapeños, Nachos, Quesillo, Dos Huevos de Codorniz", "precio": 20500},
    ],
    "SALCHIPAPAS": [
        {"nombre": "Salchipapa Sencilla", "precio": 12000},
        {"nombre": "Salchipapa Doble", "precio": 20500},
        {"nombre": "Salchipapa Doble Gratinada", "precio": 24000},
        {"nombre": "Salchipapa Mexicana", "precio": 19000},
        {"nombre": "Choripapa", "precio": 19000},
        {"nombre": "Choripapa Gratinada", "precio": 25000},
        {"nombre": "Salchipapa Ranchera", "precio": 20500},
        {"nombre": "Salchipapa Ranchera Gratinada", "precio": 26500},
        {"nombre": "Salchichorimixta", "precio": 30000},
        {"nombre": "Salchichorimixta Gratinada", "precio": 36000},
        {"nombre": "Salchichoripollo", "precio": 30000},
        {"nombre": "Salchichoripollo Gratinada", "precio": 36000},
        {"nombre": "Salchichoricarne", "precio": 36000},
        {"nombre": "Salchichoricarne Gratinada", "precio": 42000},
    ],
    "AREPAS": [
        {"nombre": "Arepa Con Queso", "precio": 8500},
        {"nombre": "Arepa Jamon y Queso", "precio": 9500},
        {"nombre": "Arepa Mixta Sencilla", "precio": 12000},
        {"nombre": "Arepa Carne Zenú", "precio": 14500},
        {"nombre": "Choriarepa", "precio": 14500},
        {"nombre": "Salchiarepa", "precio": 14500},
        {"nombre": "Arepa Mixta Doble", "precio": 15500},
        {"nombre": "Arepa Solo Pollo", "precio": 15500},
        {"nombre": "Arepa Mixta Cebolla Grille", "precio": 17000},
        {"nombre": "Arepa Mixta Chicharron", "precio": 18000},
        {"nombre": "Arepa Mixta Maiz Tierno", "precio": 18000},
        {"nombre": "Arepa Solo Carne", "precio": 19000},
        {"nombre": "Arepa Mixta Chorizo", "precio": 19000},
        {"nombre": "Arepa Mixta Ranchera", "precio": 19000},
        {"nombre": "Arepa La Especial", "precio": 23000},
        {"nombre": "Arepa La Mexicana", "precio": 24000},
    ],
    "HAMBURGUESAS": [
        {"nombre": "Hamburguesa Sencilla", "descripcion": "Carne Saboré, Jamón, Quesillo, Vegetales y Ripio", "precio": 12000},
        {"nombre": "Arepa Burguer", "descripcion": "Carne Zenú, Arepa, Tocineta, Quesillo, Vegetales y Ripio", "precio": 20500},
        {"nombre": "Hamburguesa Ahumada de Res", "descripcion": "Carne de Res, Tocineta, Quesillo, Vegetales y Ripio", "precio": 21500},
        {"nombre": "Pata Burguer", "descripcion": "Carne Zenú, Patacón, Tocineta, Quesillo, Vegetales y Ripio", "precio": 21500},
        {"nombre": "Hamburguesa De Pollo", "descripcion": "Carne de Pollo, Tocineta, Quesillo, Vegetales y Ripio", "precio": 21500},
        {"nombre": "Hamburguesa Carne Zenú", "descripcion": "Carne Zenú, Tocineta, Quesillo, Vegetales y Ripio", "precio": 21500},
        {"nombre": "Hamburguesa De la Casa", "descripcion": "Carne Artesanal, Tocineta, Quesillo, Vegetales y Ripio", "precio": 21500},
        {"nombre": "Hamburguesa De Búfalo", "descripcion": "Carne de Búfalo, Tocineta, Quesillo, Vegetales y Ripio + Papas", "precio": 24000},
        {"nombre": "Hamburguesa Doble De Búfalo", "descripcion": "Doble Carne de Búfalo, Tocineta, Quesillo, Vegetales y Ripio + Papas", "precio": 32000},
        {"nombre": "Hamburguesa Mexicana", "descripcion": "Carne Artesanal, Tocineta, Quesillo, Vegetales, Jalapeños, Nachos y Ripio + Papas", "precio": 25000},
        {"nombre": "Hamburguesa Mixta o Doble", "descripcion": "Dos carnes a elegir (Pollo, Res Ahumada o Zenú), Tocineta, Quesillo, Vegetales y Ripio + Papas", "precio": 30000},
        {"nombre": "Hamburguesa Trifásica", "descripcion": "Carne de Búfalo, Res, Pollo, Tocineta, Quesillo, Vegetales y Ripio + Papas", "precio": 38500},
    ],
    "PATACONES": [
        {"nombre": "Patacon Mixto", "precio": 26500},
        {"nombre": "Patacon Solo Pollo", "precio": 26500},
        {"nombre": "Patacon Solo Carne", "precio": 32500},
    ],
    "DESGRANADOS": [
        {"nombre": "Mazorcada Mixta", "precio": 26500},
        {"nombre": "Burrito Mixto", "precio": 26500},
        {"nombre": "Mazorcada Solo Carne", "precio": 32500},
        {"nombre": "Burrito Solo Carne", "precio": 32500},
    ],
    "ALITAS DE POLLO": [
        {"nombre": "4 Piezas", "precio": 19000},
        {"nombre": "8 Piezas", "precio": 36000},
        {"nombre": "12 Piezas", "precio": 45500},
        {"nombre": "25 Piezas", "precio": 84000},
    ],
    "PINCHOS": [
        {"nombre": "Chorizo Antioqueño", "precio": 7000},
        {"nombre": "Chorizo de Cerdo", "precio": 12000},
        {"nombre": "Pincho de Pollo Apanado", "precio": 12000},
        {"nombre": "Pincho de Res", "precio": 18000},
        {"nombre": "Pincho de Cerdo", "precio": 18000},
        {"nombre": "Pincho de Pollo", "precio": 18000},
        {"nombre": "Pinchos Encebollados/Gratinados", "precio": 21500},
    ],
    "CARNES (PLATOS FUERTES)": [
        {"nombre": "Costillas Ahumadas (BBQ / Miel Mostaza)", "precio": 39500},
        {"nombre": "Pechuga a la Plancha", "precio": 39500},
        {"nombre": "Churrasco", "precio": 45500},
        {"nombre": "Punta de Anca", "precio": 45500},
        {"nombre": "Picada Mediana", "precio": 60000},
        {"nombre": "Picada Grande", "precio": 96000},
    ],
    "BEBIDAS": [
        {"nombre": "Jugo Natural en Agua", "precio": 8500},
        {"nombre": "Jugo Natural en Agua FRAPPE", "precio": 10500},
        {"nombre": "Jugo Natural en Leche", "precio": 9000},
        {"nombre": "Jugo Natural en Leche FRAPEE", "precio": 11000},
        {"nombre": "Citrico Mandarina ", "precio": 8500},
        {"nombre": "Citrico Mandarina FRAPEE", "precio": 10500},
        {"nombre": "Citrico Limon", "precio": 8500},
        {"nombre": "Citrico Limon FRAPEE", "precio": 10500},
        {"nombre": "Citrico Naranja", "precio": 8500},
        {"nombre": "Citrico Naranja FRAPEE", "precio": 10500},
        {"nombre": "Limonada de Coco", "precio": 9500},
        {"nombre": "Limonada de Cereza", "precio": 9500},
        {"nombre": "Limonada de Mango Biche", "precio": 9500},
        {"nombre": "Limonada de Hierbabuena", "precio": 9500},
        {"nombre": "Milo", "precio": 9500},
        {"nombre": "Masato Mediano", "precio": 2500},
        {"nombre": "Masato Grande", "precio": 4000},
        {"nombre": "Avena Mediana", "precio": 3000},
        {"nombre": "Avena Grande", "precio": 4000},
        {"nombre": "Tamarindo Preparado", "precio": 7000},
    ],  
    "ADICIONALES / ENSALADAS": [
        {"nombre": "Ensalada de Repollo", "precio": 3500},
        {"nombre": "Ensalada Verde", "precio": 6000},
        {"nombre": "Tocineta", "precio": 6000},
        {"nombre": "Yuca", "precio": 7000},
        {"nombre": "Maicitos", "precio": 7000},
        {"nombre": "Quesillo", "precio": 7000},
        {"nombre": "Salchicha Llanera", "precio": 7000},
        {"nombre": "Salchicha Americana", "precio": 7000},
        {"nombre": "Chorizo", "precio": 7000},
        {"nombre": "Huevos de Codorniz", "precio": 7000},
        {"nombre": "Chicharrón", "precio": 7000},
        {"nombre": "Papas Francesas", "precio": 8500},
        {"nombre": "Pollo Desmechado", "precio": 9500},
        {"nombre": "Carne Desmechada", "precio": 12000},
    ],

}
CATEGORIAS_SIN_COCINA = ["FRITOS", "BEBIDAS"]

# ==========================================
# RUTAS DE OPERACIÓN
# ==========================================

@app.route('/')
def index():
    # Antes decía: return "Servidor Funcionando..."
    return render_template('index.html')

@app.route('/mesero')
def view_mesero():
    return render_template('mesero.html', carta=CARTA)

@app.route('/cocina')
def view_cocina():
    return render_template('cocina.html')

@app.route('/caja')
def view_caja():
    return render_template('cajera.html')

@app.route('/jefa')
@login_required  # <--- CANDADO APLICADO
def view_jefa():
    return render_template('jefa.html')

@app.route('/estado_mesas')
def estado_mesas():
    pedidos_activos = Pedido.query.filter(Pedido.estado.in_(['Pendiente', 'Listo'])).all()
    resumen = {}
    
    # 1. Creamos listas de los nombres que NO deben ir a la pantalla de cocina
    # Usamos .get() por seguridad en caso de que alguna categoría esté vacía o no exista
    nombres_fritos = [p['nombre'] for p in CARTA.get('FRITOS', [])]
    nombres_bebidas = [p['nombre'] for p in CARTA.get('BEBIDAS', [])]
    
    # Unificamos ambas listas
    excluidos_cocina = nombres_fritos + nombres_bebidas

    for p in pedidos_activos:
        items_cocina = []
        items_completo = []
        tiene_pendientes = False
        
        for i in p.items:
            # Para la CAJA siempre va todo
            item_data = {
                "nombre": i.nombre_producto,
                "cantidad": i.cantidad,
                "precio": i.precio_unitario,
                "nota": i.nota,
                "despachado": i.despachado
            }
            items_completo.append(item_data)

            # FILTRO CRÍTICO: Si NO es frito y NO es bebida, va para la cocina
            if i.nombre_producto not in excluidos_cocina:
                items_cocina.append(item_data)
                if not i.despachado:
                    tiene_pendientes = True

        # SOLO enviamos la mesa a la vista de cocina si tiene items de plancha/carbón
        if items_cocina:
            resumen[p.mesa] = {
                "estado": p.estado,
                "mesero": p.meser_nombre,
                "items": items_cocina, # Solo plancha/carbón
                "items_completo": items_completo, # Todo para la caja
                "tiene_pendientes": tiene_pendientes 
            }
        else:
            # Si el pedido existe pero solo tiene fritos/bebidas, lo enviamos 
            # solo para la caja con la bandera correspondiente
            resumen[p.mesa] = {
                "estado": p.estado,
                "mesero": p.meser_nombre,
                "items": [], 
                "items_completo": items_completo,
                "tiene_pendientes": False,
                "solo_caja": True # Bandera extra
            }
            
    return jsonify(resumen)

@app.route('/enviar_pedido', methods=['POST'])
def enviar_pedido():
    inicio = time.time()
    data = request.json
    # El Punto 5: mesa_id ahora acepta texto ("Vitrina", "Mesa 1", etc.)
    mesa_id = str(data.get('mesa'))
    nombre_mesero = data.get('mesero')
    items_nuevos = data.get('items')

    pedido_actual = Pedido.query.filter(
        Pedido.mesa == mesa_id, 
        Pedido.estado.in_(['Pendiente', 'Listo'])
    ).first()

    if not pedido_actual:
        pedido_actual = Pedido(mesa=mesa_id, meser_nombre=nombre_mesero, estado='Pendiente')
        db.session.add(pedido_actual)
        db.session.flush()
    else:
        pedido_actual.estado = 'Pendiente'

    for item in items_nuevos:
        # LÓGICA PROFESIONAL (Puntos 1 y 2):
        # Buscamos un item que coincida en nombre, nota Y quien lo pidió.
        # Si la nota es diferente, creamos una línea nueva en lugar de sumar.
        item_en_db = ItemPedido.query.filter_by(
            pedido_id=pedido_actual.id, 
            nombre_producto=item['nombre'],
            nota=item.get('nota', ""), 
            quien_pide=nombre_mesero, # <--- Clave para auditoría
            despachado=False 
        ).first()

        if item_en_db:
            item_en_db.cantidad += item['cantidad']
        else:
            # Si algo cambió (nota o mesero), se crea una línea nueva
            nuevo_item = ItemPedido(
                nombre_producto=item['nombre'],
                precio_unitario=item['precio'],
                cantidad=item['cantidad'],
                nota=item.get('nota', ""), 
                pedido_id=pedido_actual.id,
                quien_pide=nombre_mesero, # Guardamos quién lo pidió
                despachado=False 
            )
            db.session.add(nuevo_item)
    
    db.session.commit()
    fin = time.time()
    print(f"DEBUG: Tiempo de respuesta DB: {fin - inicio} segundos")
    return "OK"
    socketio.emit('actualizar_mesas')
    return jsonify({"success": True})
@app.route('/completar_mesa/<num_mesa>', methods=['POST']) # <-- Quitamos el 'int:'
def completar_mesa(num_mesa):
    # Ya no necesitas str(num_mesa) porque al quitar 'int:' ya viene como texto
    pedido = Pedido.query.filter(Pedido.mesa == num_mesa, Pedido.estado != 'Pagado').first()
    
    if pedido:
        for i in pedido.items:
            i.despachado = True
        
        pedido.estado = 'Listo'
        pedido.preparado_en = hora_colombia()
        db.session.commit()

        # --- LÓGICA DE AUTO-LIMPIEZA ---
        # Si la mesa NO es de las fijas (1 a 12), podemos marcarla como pagada 
        # o eliminarla para que desaparezca de cocina y caja de una vez.
        # Si quieres que desaparezca de cocina pero siga en caja para cobrar,
        # déjala como está. Si quieres que se borre de todo lado:
        
        # if not (num_mesa.isdigit() and 1 <= int(num_mesa) <= 12):
        #     pedido.estado = 'Pagado' # Esto la sacaría de las listas activas
        #     db.session.commit()

        socketio.emit('pedido_listo_emergencia', {
            "mesa": pedido.mesa,
            "mesero": pedido.meser_nombre
        })
        
        socketio.emit('actualizar_mesas')
        return jsonify({"status": "ok"})
        
    return jsonify({"status": "error"}), 404
# 1. Quitamos el <int: > para que acepte cualquier texto
@app.route('/pagar_mesa/<mesa_id>', methods=['POST']) 
def pagar_mesa(mesa_id):
    # 2. Ya no convertimos a str() porque mesa_id ya es un String
    pedido = Pedido.query.filter(
        Pedido.mesa == mesa_id, 
        Pedido.estado.in_(['Pendiente', 'Listo'])
    ).first()
    
    if pedido:
        pedido.estado = 'Pagado'
        pedido.entregado_en = hora_colombia()
        db.session.commit()
        socketio.emit('actualizar_mesas') 
        return jsonify({"success": True})
    
    # 3. Si no encuentra el pedido, devolvemos un mensaje claro
    return jsonify({"success": False, "error": f"No se encontró pedido activo para {mesa_id}"}), 404

# ==========================================    
# REPORTES Y AUDITORÍA
# ==========================================
@app.route('/admin/reporte_hoy')
@login_required  # <--- CANDADO APLICADO
def reporte_hoy():
    hoy = hora_colombia().date()
    
    # 1. Total dinero
    total_diario = db.session.query(func.sum(ItemPedido.precio_unitario * ItemPedido.cantidad))\
        .join(Pedido)\
        .filter(Pedido.estado == 'Pagado')\
        .filter(func.date(Pedido.creado_en) == hoy).scalar() or 0

    # 2. Top Ventas
    productos_vendidos = db.session.query(
        ItemPedido.nombre_producto, 
        func.sum(ItemPedido.cantidad).label('total')
    ).join(Pedido)\
     .filter(Pedido.estado == 'Pagado')\
     .filter(func.date(Pedido.creado_en) == hoy)\
     .group_by(ItemPedido.nombre_producto)\
     .order_by(func.sum(ItemPedido.cantidad).desc()).all()

    # 3. Ventas por Mesa
    ventas_por_mesa = db.session.query(
        Pedido.mesa, 
        func.sum(ItemPedido.precio_unitario * ItemPedido.cantidad)
    ).join(ItemPedido)\
     .filter(Pedido.estado == 'Pagado')\
     .filter(func.date(Pedido.creado_en) == hoy)\
     .group_by(Pedido.mesa).all()

    # 4. LISTA PARA LA TABLA DE AUDITORÍA (ESTRUCTURADA PARA EL VALE)
    pedidos_auditoria = Pedido.query.filter(
        Pedido.estado == 'Pagado',
        func.date(Pedido.creado_en) == hoy
    ).all()
    
    lista_auditoria = []
    for p in pedidos_auditoria:
        total_p = sum(i.precio_unitario * i.cantidad for i in p.items)
        
        # Guardamos los nombres para la tabla (lo que ya tenías)
        nombres_p = ", ".join([f"{i.cantidad} {i.nombre_producto}" for i in p.items])
        
        # NUEVO: Creamos el detalle técnico para el Modal del Vale
        detalle_para_vale = []
        for i in p.items:
            detalle_para_vale.append({
                "nombre": i.nombre_producto,
                "cantidad": i.cantidad,
                "precio": i.precio_unitario,
                "nota": i.nota,
                "quien_pide": i.quien_pide # <--- Esto ahora aparecerá en el vale de auditoría
            })

        tiempo = "0 min"
        if p.creado_en and p.entregado_en:
            diff = p.entregado_en - p.creado_en
            minutos = int(diff.total_seconds() / 60)
            tiempo = f"{minutos} min"

        lista_auditoria.append({
            "mesa": p.mesa,
            "mesero": p.meser_nombre or "Sin nombre",
            "hora_pedido": p.creado_en.strftime('%H:%M') if p.creado_en else "--:--",
            "hora_pago": p.entregado_en.strftime('%H:%M') if p.entregado_en else "--:--",
            "productos": nombres_p, # Seguimos mandando esto para no dañar la tabla actual
            "total": total_p,
            "tiempo_atencion": tiempo,
            "lista_items": detalle_para_vale  # <--- ESTO ES LO NUEVO PARA EL BOTÓN
        })

    return jsonify({
        "total_dinero": total_diario,
        "productos": [{"nombre": p[0], "cantidad": p[1]} for p in productos_vendidos],
        "mesas": [{"id": m[0], "total": m[1]} for m in ventas_por_mesa],
        "auditoria": lista_auditoria 
    })

@app.route('/admin/auditoria_diaria')
@login_required  # <--- CANDADO APLICADO
def auditoria_diaria():
    hoy = hora_colombia().date()
    auditoria = Pedido.query.filter(
        Pedido.estado == 'Pagado',
        func.date(Pedido.creado_en) == hoy
    ).all()
    
    reporte = []
    for p in auditoria:
        total_pedido = sum(i.precio_unitario * i.cantidad for i in p.items)
        reporte.append({
            "mesa": p.mesa,
            "mesero": p.meser_nombre,
            "hora_pedido": p.creado_en.strftime('%H:%M') if p.creado_en else "--",
            "hora_pago": p.entregado_en.strftime('%H:%M') if p.entregado_en else "--",
            "productos": [f"{i.cantidad}x {i.nombre_producto}" for i in p.items],
            "total": total_pedido
        })
    return jsonify(reporte)

# ==========================================
# MÓDULO HAPPY (JEFA -> CHICA)
# ==========================================

despacho_happy_db = {}

@app.route('/happy')
def view_happy():
    return render_template('happy.html')

@app.route('/api/despacho_happy', methods=['POST', 'GET'])
def api_despacho_happy():
    global despacho_happy_db
    if request.method == 'POST':
        despacho_happy_db = request.json
        return jsonify({"status": "success"})
    return jsonify(despacho_happy_db)

# ==========================================
# EVENTOS SOCKET.IO
# ==========================================

@socketio.on('notificar_digitacion')
def handle_digitacion(data):
    socketio.emit('usuario_anotando', data, include_self=False)

@socketio.on('notificar_libre')
def handle_libre(data):
    socketio.emit('usuario_libre', data, include_self=False)

if __name__ == '__main__':
    # Render nos pasa el puerto en una variable de entorno
    port = int(os.environ.get("PORT", 5000))
    
    # Usamos socketio.run para que el tiempo real funcione bien
    # Quitamos debug=True para producción (es más seguro y rápido)
    socketio.run(app, host='0.0.0.0', port=port)