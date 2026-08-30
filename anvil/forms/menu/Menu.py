from ._anvil_designer import MenuTemplate
import anvil.server
import anvil.js

class Menu(MenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.inicializar_puente_javascript()
    self.cargar_datos_menu()

  def inicializar_puente_javascript(self):
    try:
      setattr(anvil.js.window, "anvilAppNav", self.navegar_modulo)
      setattr(anvil.js.window, "anvilProcesarCobro", self.procesar_cobro_comanda)
    except Exception as e:
      print(f"Error en inicializar_puente_javascript: {e}")

  def cargar_datos_menu(self):
    try:
      productos = anvil.server.call("get_productos_terraza")
      categorias = anvil.server.call("get_categorias_terraza")
      
      try:
        anvil.js.call_js("cargarDatosMenu", productos, categorias)
      except Exception as ex1:
        print(f"call_js retry fallback: {ex1}")
        func = getattr(anvil.js.window, "cargarDatosMenu", None)
        if func:
          func(productos, categorias)
    except Exception as e:
      print(f"Error al cargar menú en Anvil Client: {e}")

  def navegar_modulo(self, modulo_nombre):
    print(f"Navegando al módulo: {modulo_nombre}")

  def procesar_cobro_comanda(self, metodo_pago, items_carrito):
    try:
      resultado = anvil.server.call("procesar_cobro_terraza", metodo_pago, items_carrito)
      if resultado.get("success"):
        try:
          anvil.js.call_js("alert", f"✅ Pago exitoso ({metodo_pago.upper()}). Folio Ticket: {resultado.get('folio')}")
        except Exception:
          pass
    except Exception as e:
      print(f"Error en procesar_cobro_comanda: {e}")
