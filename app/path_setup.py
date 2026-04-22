import sys
from pathlib import Path

# Agrega la raíz del proyecto al path para que 'config' sea encontrado
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
