from ._anvil_designer import MenuTemplate
import anvil.server

class Menu(MenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def navegar_modulo(self, modulo_nombre):
    print(f"Navegando al módulo: {modulo_nombre}")

  def procesar_cobro_comanda(self, metodo_pago, items_carrito):
    try:
      return anvil.server.call("procesar_cobro_terraza", metodo_pago, items_carrito)
    except Exception as e:
      print(f"Error en procesar_cobro_comanda: {e}")
