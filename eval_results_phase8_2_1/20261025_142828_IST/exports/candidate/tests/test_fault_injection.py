import pytest
import ast
from benchmark.fault_injector import FaultInjector, validate_mutation, calculate_complexity

def test_ast_complexity():
    code = "def foo():\n    if True:\n        pass"
    complexity = calculate_complexity(code)
    assert complexity["loc"] == 3
    assert complexity["functions"] == 1
    assert complexity["branches"] == 1
    assert complexity["ast_nodes"] > 0

def test_valid_mutation():
    orig = "def add(a, b):\n    return a + b"
    injector = FaultInjector(seed=42)
    res = injector.inject(orig)
    assert res["success"] == True
    assert "fault" in res
    assert res["fault"]["type"] == "LOGICAL_OPERATOR_MUTATION"
    assert res["fault"]["original"] == "Add"

def test_mutation_validation():
    orig = "def add(a, b):\n    return a + b"
    mutated = "def add(a, b):\n    return a - b"
    tests = ["assert add(2, 2) == 4", "assert add(-1, 1) == 0"]
    
    # orig passes tests, mutated fails, so validate returns True
    assert validate_mutation(orig, mutated, tests) == True

def test_invalid_mutation_rejected():
    orig = "def noop(a):\n    return a"
    injector = FaultInjector(seed=42)
    res = injector.inject(orig)
    # no mutable nodes
    assert res["success"] == False
