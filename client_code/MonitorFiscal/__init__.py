from ._anvil_designer import MonitorFiscalTemplate
import anvil.server

class MonitorFiscal(MonitorFiscalTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
