from ._anvil_designer import POSMeseroTemplate
import anvil.server

class POSMesero(POSMeseroTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
