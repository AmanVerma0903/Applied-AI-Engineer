# Part 4 Fix Loop Bundle

This folder contains the complete reproduction bundle for **Part 4: The Fix Loop (25% of score)**.

## How to Reproduce
Run the single command:
```bash
python -m fix_loop.reproduce_fix
```

## Structure
- `reproduce_fix.py`: Reproduces the coarse-bin run and the refined-jamb run on the same west-wall door as the pipeline contract.
- `before_fix/metrics.json`: Coarse 5 cm bins, **70.0 cm** measured, **16.0 cm** error, FAIL.
- `after_fix/metrics.json`: Refined jambs, **82.9 cm** measured, **3.1 cm** error, FAIL. Same width as `outputs/audit_room/contract.json`.
- `../deliverables/fix_loop_declaration.md`: The official 1-page Fix Declaration specifying the worst-performing gate, root-cause hypothesis, prediction, and verified results.
