"""C# methods and cyclomatic complexity, following the Java rules.

A method or local function with a body is an entry. Constructors, abstract
methods, and lambdas are not. A decision inside a lambda, a local function, or
a nested type stays with that nested body. The namespace is
`Namespace.Outer.Inner`.
"""

from crapper.languages.treesitter import (
    binary_logic,
    child_of_type,
    complexity,
    end_line,
    node_text,
    parse,
    start_line,
)
from crapper.model import Function

_TYPES = {
    "class_declaration",
    "interface_declaration",
    "struct_declaration",
    "record_declaration",
    "enum_declaration",
}
_DECISIONS = {
    "if_statement",
    "for_statement",
    "foreach_statement",
    "while_statement",
    "do_statement",
    "catch_clause",
    "conditional_expression",
    "switch_section",
}
_NESTED_BODY = {"lambda_expression", "local_function_statement"}


def _is_decision(node) -> bool:
    return node.type in _DECISIONS or binary_logic(node)


def _complexity_of(node) -> int:
    def skip(current) -> bool:
        if current is node:
            return False
        return current.type in _TYPES or current.type in _NESTED_BODY

    return complexity(node, _is_decision, skip)


def _hidden(node) -> bool:
    current = node.parent
    while current is not None:
        if node.type == "local_function_statement" and current.type == "method_declaration":
            current = current.parent
            continue
        if current.type in {
            "method_declaration",
            "constructor_declaration",
            "lambda_expression",
            "local_function_statement",
        }:
            return True
        current = current.parent
    return False


def _name_of(data: bytes, node) -> str | None:
    ident = child_of_type(node, "identifier")
    if ident is None:
        return None
    return node_text(data, ident)


def _namespace_names(data: bytes, node) -> list[str]:
    names: list[str] = []
    current = node.parent
    while current is not None:
        if current.type == "namespace_declaration":
            ident = child_of_type(current, "qualified_name", "identifier")
            if ident is not None:
                names.append(node_text(data, ident))
        current = current.parent
    names.reverse()
    return names


def _file_namespace(data: bytes, root) -> str | None:
    for child in root.children:
        if child.type != "file_scoped_namespace_declaration":
            continue
        ident = child_of_type(child, "qualified_name", "identifier")
        if ident is not None:
            return node_text(data, ident)
    return None


def _type_chain(data: bytes, node) -> list[str]:
    names: list[str] = []
    current = node.parent
    while current is not None:
        if current.type in _TYPES:
            ident = child_of_type(current, "identifier")
            if ident is not None:
                names.append(node_text(data, ident))
        current = current.parent
    names.reverse()
    return names


def _qualify(namespace: list[str], types: list[str]) -> str:
    return ".".join([*namespace, *types])


def _has_body(node) -> bool:
    return child_of_type(node, "block", "arrow_expression_clause") is not None


def functions_in_source(
    source: str, path: str, project_root: str | None = None
) -> list[Function]:
    del project_root
    data, tree = parse(source, "csharp")
    file_namespace = _file_namespace(data, tree.root_node)
    found: list[Function] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in {"method_declaration", "local_function_statement"} and _has_body(node):
            name = _name_of(data, node)
            types = _type_chain(data, node)
            if name is not None and types and not _hidden(node):
                namespace = _namespace_names(data, node)
                if file_namespace:
                    namespace = [file_namespace, *namespace]
                found.append(
                    Function(
                        name=name,
                        namespace=_qualify(namespace, types),
                        complexity=_complexity_of(node),
                        start_line=start_line(node),
                        end_line=end_line(node),
                        path=path,
                        language="csharp",
                    )
                )
        stack.extend(reversed(node.children))
    return found
