# Part 4 Fix Loop Bundle

This folder contains the complete reproduction bundle for **Part 4: The Fix Loop (25% of score)**.

## How to Reproduce
Run the single command:
```bash
python -m fix_loop.reproduce_fix
```

## Structure
- `reproduce_fix.py`: Reproduces both the pre-fix failing run and post-fix passing run deterministically.
- `before_fix/metrics.json`: Output metrics of the pre-fix run showing the failing number ($11.6\text{ cm}$ error, $0\%$ pass rate).
- `after_fix/metrics.json`: Output metrics of the post-fix run showing the passing number ($1.9\text{ cm}$ error $\le 2.0\text{ cm}$, $100\%$ pass rate).
- `../deliverables/fix_loop_declaration.md`: The official 1-page Fix Declaration specifying the worst-performing gate, root-cause hypothesis, prediction, and verified results.
