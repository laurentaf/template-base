from abc import ABC, abstractmethod
from src.core.telemetry import setup_observability
from src.core.config import settings

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        setup_observability(project_name=name)
        
    @abstractmethod
    def run(self, task: str):
        pass

    def log_action(self, action: str):
        """Placeholder for Ledger/Harness logging."""
        print(f"[{self.name}] Action: {action}")
