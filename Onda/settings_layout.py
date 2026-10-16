"""Category order shared with Android; persisted preference identifiers remain unchanged."""
import json
from pathlib import Path
LAYOUT=json.loads((Path(__file__).parent/'settings_schema/layout.json').read_text(encoding='utf-8'))
CATEGORIES=tuple(LAYOUT['categories'])
