from ._anvil_designer import MenuTemplate

class Menu(MenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def navegar_modulo(self, modulo_nombre):
    print(f"Navegando al módulo: {modulo_nombre}")

  def procesar_cobro_comanda(self, metodo_pago, items_carrito):
    print(f"Procesando cobro: {metodo_pago}")
