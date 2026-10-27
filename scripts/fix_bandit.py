from pathlib import Path

p = Path(".venv/Lib/site-packages/bandit/core/node_visitor.py")
if p.exists():
    txt = p.read_text(encoding="utf-8")
    if "self.context[\"str\"] = node.s" in txt:
        txt = txt.replace("self.context[\"str\"] = node.s", "self.context[\"str\"] = getattr(node, 'value', getattr(node, 's', ''))")
        p.write_text(txt, encoding="utf-8")
        print("Bandit patched successfully for Python 3.14 AST.")
    else:
        print("Bandit already patched or pattern not found.")
