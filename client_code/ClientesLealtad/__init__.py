from ._anvil_designer import ClientesLealtadTemplate
import anvil.server

class ClientesLealtad(ClientesLealtadTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
