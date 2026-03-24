"""
Dashboard UI reference.

The live `cl def:pub app` component is defined in `main.jac` at the project root.
`jac start` loads the entry module only; JSX components in other `.jac` files do
not produce a Python-exportable `app` symbol, so importing `{ app }` from this
module fails at runtime.

Edit the dashboard in `main.jac` (search for `cl def:pub app`).
"""
