from ._anvil_designer import MonitorCocinaTemplate
import anvil.server

class MonitorCocina(MonitorCocinaTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
