from ._anvil_designer import MenuTemplate
import anvil.server
import anvil.open_form

class Menu(MenuTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

  def navegar_modulo(self, modulo_nombre):
    if modulo_nombre in ['pos_mesero', 'croquis']:
      anvil.open_form('POSMesero')
    elif modulo_nombre in ['monitor_cocina', 'kds']:
      anvil.open_form('MonitorCocina')
    elif modulo_nombre in ['monitor_fiscal', 'fiscal']:
      anvil.open_form('MonitorFiscal')
    elif modulo_nombre in ['clientes_lealtad', 'rewards']:
      anvil.open_form('ClientesLealtad')
    else:
      anvil.open_form('Menu')

  def procesar_cobro_comanda(self, metodo_pago, items_carrito):
    return anvil.server.call('procesar_cobro_terraza', metodo_pago, items_carrito)
