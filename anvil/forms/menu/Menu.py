# ============================================================================
# LA TERRAZA DE VIDA & SABOR (V&S) - ANVIL CLIENT FORM
# Formulario: Menu.py
# Lógica del Cliente con Puente JS seguro (window.navMenu, window.cargarDatosMenu)
# ============================================================================

from ._anvil_designer import MenuTemplate
import anvil.server
import anvil.js

class Menu(MenuTemplate):
  def __init__(self, **properties):
    # Inicializar componentes del diseñador de Anvil
    self.init_components(**properties)
    self.inicializar_puente_javascript()
    self.cargar_datos_menu()

  def inicializar_puente_javascript(self):
    """Establece los callbacks de seguridad entre Anvil Python Client y JavaScript Window"""
    window = anvil.js.window
    window.anvilAppNav = self.navegar_modulo
    window.anvilProcesarCobro = self.procesar_cobro_comanda

  def cargar_datos_menu(self):
    """Llama al backend vía RPC (ServerModule1) para alimentar el menú y categorías de La Terraza V&S"""
    try:
      productos = anvil.server.call('get_productos_terraza')
      categorias = anvil.server.call('get_categorias_terraza')
      
      # Inyectar datos al puente JavaScript
      anvil.js.window.cargarDatosMenu(productos, categorias)
    except Exception as e:
      print(f"Error al cargar menú en Anvil Client: {e}")

  def navegar_modulo(self, modulo_nombre):
    """Maneja la navegación entre módulos (Cocina KDS, Monitor Fiscal, Lealtad)"""
    print(f"Navegando al módulo: {modulo_nombre}")
    if modulo_nombre == 'kds':
      # abrir formulario KDS si existe
      pass
    elif modulo_nombre == 'fiscal':
      # abrir formulario fiscal
      pass

  def procesar_cobro_comanda(self, metodo_pago, items_carrito):
    """Envía la transacción de cobro al backend de Anvil"""
    try:
      resultado = anvil.server.call('procesar_cobro_terraza', metodo_pago, items_carrito)
      if resultado.get('success'):
        anvil.js.window.alert(f"✅ Pago exitoso ({metodo_pago.upper()}). Folio Ticket: {resultado.get('folio')}")
        # Reiniciar carrito en JS
        anvil.js.window.vsCartItems = []
        anvil.js.window.renderCarrito()
      else:
        anvil.js.window.alert(f"❌ Error en el cobro: {resultado.get('error')}")
    except Exception as e:
      print(f"Error en procesar_cobro_comanda: {e}")
