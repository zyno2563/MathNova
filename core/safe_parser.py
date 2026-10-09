"""Parse the public math language without evaluating Python source.

Only numbers, symbols, arithmetic, named mathematical functions, and
Piecewise conditions are accepted. The AST is converted directly into
SymPy objects; neither eval nor SymPy's string parsers are involved.
Resource limits on the subsequent calculation remain necessary.
"""

import ast
import math
import numbers
import re

import sympy as sp
from sympy.logic.boolalg import Boolean


MAX_CHARS = 4000
MAX_NODES = 512
MAX_DEPTH = 48
MAX_POWER = 1000
MAX_INTEGER_BITS = 16384
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")

# Explicitly callable mathematical operations, never the SymPy namespace.
_FUNCTIONS = {name: getattr(sp, name) for name in (
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "atan2", "acot", "asec", "acsc",
    "sinh", "cosh", "tanh", "coth", "sech", "csch",
    "asinh", "acosh", "atanh", "acoth", "asech", "acsch",
    "exp", "log", "sqrt", "Abs", "sign", "floor", "ceiling",
    "factorial", "binomial", "gamma", "erf", "erfc",
    "Heaviside", "DiracDelta", "Min", "Max", "re", "im", "arg",
    "conjugate", "sinc", "Eq", "Ne", "Lt", "Le", "Gt", "Ge",
    "And", "Or", "Not",
)}
_FUNCTIONS.update(abs=sp.Abs, ln=sp.log)
_CONSTANTS = {"pi": sp.pi, "e": sp.E, "E": sp.E, "I": sp.I,
              "oo": sp.oo, "EulerGamma": sp.EulerGamma}
_RELATIONS = {ast.Eq: sp.Eq, ast.NotEq: sp.Ne, ast.Lt: sp.Lt,
              ast.LtE: sp.Le, ast.Gt: sp.Gt, ast.GtE: sp.Ge}


def _expression(value):
    if not isinstance(value, sp.Expr):
        raise ValueError("Expected a mathematical expression, not a collection or condition.")
    if isinstance(value, sp.Rational):
        if max(int(value.p).bit_length(), int(value.q).bit_length()) > MAX_INTEGER_BITS:
            raise ValueError("The number is too large. Use a smaller exponent or coefficient.")
    return value


def _condition(value):
    if not isinstance(value, Boolean) or isinstance(value, sp.Expr):
        raise ValueError("Piecewise conditions must be comparisons or True/False.")
    return value


class _MathTree:
    def __init__(self, bindings, source):
        self.bindings = dict(bindings or {})
        self.source = source

    def read(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return sp.true if node.value else sp.false
            if isinstance(node.value, int):
                return _expression(sp.Integer(node.value))
            if isinstance(node.value, float) and math.isfinite(node.value):
                return sp.Float(ast.get_source_segment(self.source, node).replace("_", ""))
            raise ValueError("Only finite numeric literals are allowed; strings are not math inputs.")

        if isinstance(node, ast.Name):
            name = node.id
            if not _NAME.fullmatch(name) or "__" in name:
                raise ValueError("Use ordinary mathematical symbol names.")
            if name in self.bindings:
                return _expression(self.bindings[name])
            if name in _CONSTANTS:
                return _CONSTANTS[name]
            if name in _FUNCTIONS or name == "Piecewise":
                raise ValueError(f"Use {name}(...) to call a mathematical function.")
            return sp.Symbol(name)

        if isinstance(node, ast.UnaryOp):
            value = self.read(node.operand)
            if isinstance(node.op, (ast.Not, ast.Invert)):
                return sp.Not(_condition(value))
            value = _expression(value)
            if isinstance(node.op, ast.UAdd):
                return value
            if isinstance(node.op, ast.USub):
                return -value

        if isinstance(node, ast.BinOp):
            left, right = self.read(node.left), self.read(node.right)
            if isinstance(node.op, (ast.BitAnd, ast.BitOr)):
                function = sp.And if isinstance(node.op, ast.BitAnd) else sp.Or
                return function(_condition(left), _condition(right))
            left, right = _expression(left), _expression(right)
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            elif isinstance(node.op, ast.Div):
                result = left / right
            elif isinstance(node.op, ast.Pow):
                if right.is_number and (right.is_finite is False or
                        (right.is_real and abs(right) > MAX_POWER)):
                    raise ValueError(f"Numeric exponents must be between -{MAX_POWER} and {MAX_POWER}.")
                # Estimate integer output size before allocating a large power.
                if isinstance(left, sp.Rational) and isinstance(right, sp.Integer):
                    bits = max(int(left.p).bit_length(), int(left.q).bit_length())
                    if bits * abs(int(right)) > MAX_INTEGER_BITS:
                        raise ValueError("The numeric power is too large.")
                result = left ** right
            else:
                raise ValueError("Use +, -, *, / and ** (or ^) for arithmetic.")
            return _expression(result)

        if isinstance(node, ast.Compare):
            values = [self.read(node.left)] + [self.read(item) for item in node.comparators]
            conditions = []
            for index, operator in enumerate(node.ops):
                function = _RELATIONS.get(type(operator))
                if function is None:
                    raise ValueError("Only mathematical comparisons are allowed.")
                conditions.append(function(_expression(values[index]), _expression(values[index + 1])))
            return sp.And(*conditions)

        if isinstance(node, ast.BoolOp):
            function = sp.And if isinstance(node.op, ast.And) else sp.Or
            return function(*[_condition(self.read(item)) for item in node.values])

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.keywords:
                raise ValueError("Only named mathematical functions with positional arguments are allowed.")
            name = node.func.id
            if name == "Piecewise":
                pairs = []
                for item in node.args:
                    if not isinstance(item, ast.Tuple) or len(item.elts) != 2:
                        raise ValueError("Use Piecewise((expression, condition), ...).")
                    pairs.append((_expression(self.read(item.elts[0])), _condition(self.read(item.elts[1]))))
                if not pairs:
                    raise ValueError("Piecewise needs at least one expression and condition.")
                return sp.Piecewise(*pairs)
            function = _FUNCTIONS.get(name)
            if function is None or (name in self.bindings and self.bindings[name] is not function):
                raise ValueError(f"Unsupported mathematical function: {name}.")
            args = [self.read(item) for item in node.args]
            if name in ("And", "Or", "Not"):
                args = [_condition(item) for item in args]
            else:
                args = [_expression(item) for item in args]
            if name in ("factorial", "binomial", "gamma"):
                for item in args:
                    if item.is_number and item.is_real and abs(item) > MAX_POWER:
                        raise ValueError(f"Numeric {name} arguments must be at most {MAX_POWER} in magnitude.")
            try:
                return function(*args)
            except (TypeError, AttributeError) as error:
                raise ValueError(f"Invalid arguments for {name}.") from error

        raise ValueError("Unsupported syntax. Enter a mathematical expression using numbers, symbols and functions.")


def parse_math(value, locals=None):
    """Convert a public math string (or an existing numeric value) safely.

    ``locals`` contains trusted symbol bindings used to preserve each engine's
    assumptions. It cannot add callable functions to the public language.
    """
    if isinstance(value, sp.Expr):
        return value
    if isinstance(value, bool):
        raise ValueError("A boolean is not a mathematical expression.")
    if isinstance(value, numbers.Integral):
        return _expression(sp.Integer(value))
    if isinstance(value, numbers.Real):
        if not math.isfinite(value):
            raise ValueError("Numbers must be finite.")
        return sp.Float(value)
    if not isinstance(value, str):
        raise ValueError("Enter a number or a mathematical expression.")
    if not value.strip() or len(value) > MAX_CHARS:
        raise ValueError(f"An expression must contain 1 to {MAX_CHARS} characters.")
    source = value.strip().replace("^", "**")
    try:
        tree = ast.parse(source, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as error:
        raise ValueError("Invalid mathematical expression syntax.") from error
    pending, count = [(tree, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError("The expression is too large or deeply nested.")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return _expression(_MathTree(locals, source).read(tree.body))
