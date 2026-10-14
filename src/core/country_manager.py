import os
import importlib
from src.core.tax_interface import BaseTaxEngine

class CountryManager:
    """Dynamically loads and manages country tax plugins."""
    
    def __init__(self):
        self.plugins = {}
        self.load_plugins()
        
    def load_plugins(self):
        """Scans the src/countries directory and loads available plugins."""
        countries_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "countries")
        
        if not os.path.exists(countries_dir):
            return
            
        for folder in os.listdir(countries_dir):
            folder_path = os.path.join(countries_dir, folder)
            if os.path.isdir(folder_path) and not folder.startswith("__"):
                # Look for a tax_engine.py inside the country folder
                engine_path = os.path.join(folder_path, "tax_engine.py")
                if os.path.exists(engine_path):
                    try:
                        # Dynamically import the module
                        module_name = f"src.countries.{folder}.tax_engine"
                        module = importlib.import_module(module_name)
                        
                        # Find classes that inherit from BaseTaxEngine
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, BaseTaxEngine) and attr is not BaseTaxEngine:
                                instance = attr()
                                # Register plugin using its defined country name
                                self.plugins[instance.country_name] = instance
                    except Exception as e:
                        print(f"Failed to load plugin from {folder}: {e}")

        # --- Dynamic Rules Registration ---
        from src.logger import logger
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dynamic_dir = os.path.join(root_dir, "data", "dynamic_rules")
        if os.path.exists(dynamic_dir):
            from src.core.universal_engine import UniversalTaxEngine
            for file in os.listdir(dynamic_dir):
                if file.endswith(".json"):
                    try:
                        country_name = file.replace(".json", "").replace("_", " ").title()
                        engine = UniversalTaxEngine(country_name, "¤", os.path.join(dynamic_dir, file))
                        self.plugins[country_name] = engine
                        logger.info(f"✨ Dynamically registered {country_name} Tax Engine.")
                    except Exception as e:
                        logger.error(f"Failed to load dynamic rule {file}: {e}")
                        
    def get_supported_countries(self) -> list[str]:
        """Returns a list of names of supported countries."""
        return sorted(list(self.plugins.keys()))
        
    def get_engine(self, country_name: str) -> BaseTaxEngine:
        """Returns the tax engine instance for the specified country."""
        return self.plugins.get(country_name)

# Singleton instance for global access
manager = CountryManager()