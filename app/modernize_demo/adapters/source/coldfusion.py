"""Tree-sitter-backed ColdFusion discovery and parsing for the demo."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

from ...core.hashing import sha256_file, sha256_json
from ...core.models import AstArtifact, FunctionArgument, FunctionNode, QueryInfo

ADAPTER_NAME = "coldfusion-demo-adapter"
ADAPTER_VERSION = "0.2.0"
PARSER = None


def _parser():
    global PARSER
    if PARSER is None:
        try:
            PARSER = get_parser("html")
        except Exception as exc:
            raise RuntimeError(
                "Unable to initialize the Tree-sitter HTML parser. "
                "The tree-sitter-language-pack package may be trying to download parser assets "
                "from GitHub and your machine rejected the TLS certificate chain. "
                "On Windows this often happens behind a corporate proxy or custom root CA. "
                "Retry after fixing Python/pip certificate trust, or run in an environment that can "
                "reach GitHub releases. Original error: "
                f"{exc}"
            ) from exc
    return PARSER


def discover_source(source_root: Path) -> dict:
    """Discover source, config, and environment-relevant files."""
    source_files = sorted(
        [str(path.resolve()) for path in source_root.rglob("*") if path.suffix.lower() in {".cfc", ".cfm"}]
    )
    config_files = sorted(
        [
            str(path.resolve())
            for path in source_root.rglob("*")
            if path.suffix.lower() in {".json", ".yaml", ".yml", ".env", ".ini", ".properties"}
        ]
    )
    hashes = {path: sha256_file(Path(path)) for path in [*source_files, *config_files]}
    source_hash_summary = sha256_json(hashes)

    selected_modules = [Path(path).stem for path in source_files]
    return {
        "adapter": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        "discoveredSourceFiles": source_files,
        "discoveredConfigFiles": config_files,
        "environmentAssumptions": [
            "ColdFusion session scope may carry authentication state",
            "Datasource likely comes from application.datasource or variables.dsn",
            "CFML tags are parsed with Tree-sitter HTML grammar for demo purposes",
        ],
        "sourceHashSummary": source_hash_summary,
        "sourceHashes": hashes,
        "selectedModules": selected_modules,
    }


def demo_slice_from_discovery(discovery: dict, selection_method: str = "all_discovered") -> dict:
    """Create a generic demo-slice manifest from discovery output."""
    return {
        "selectedFiles": discovery["discoveredSourceFiles"],
        "selectedModules": discovery["selectedModules"],
        "selectionMethod": selection_method,
        "rationale": "Default to all discovered ColdFusion files for the demo until a narrower slice is chosen.",
        "sourceDiscoveryChecksum": discovery["sourceHashSummary"],
    }


def parse_file(path: Path) -> AstArtifact:
    """Parse one ColdFusion file into a deterministic AST-like artifact."""
    source_bytes = path.read_bytes()
    tree = _parser().parse(source_bytes)
    root = tree.root_node
    elements = [child for child in root.children if child.type == "element"]

    diagnostics: list[str] = []
    config_usage = sorted(_collect_prefixed_tokens(source_bytes.decode("utf-8"), ["application.", "cgi.", "server."]))
    endpoints = infer_endpoints(path, source_bytes, elements)
    module_type = "component" if path.suffix.lower() == ".cfc" else "template"
    functions: list[FunctionNode] = []
    component_extends = None
    ui_evidence: dict[str, object] = {}

    component_node = _find_first_tag(elements, source_bytes, "cfcomponent")
    if component_node:
        component_extends = _attribute_map(_start_tag(component_node), source_bytes).get("extends")

    if module_type == "component":
        if component_node:
            functions = _parse_component_functions(component_node, source_bytes)
        if not functions:
            diagnostics.append("No cffunction blocks detected")
    else:
        functions = [_parse_template_function(path, source_bytes, root)]
        ui_evidence = _extract_template_ui_evidence(root, source_bytes)

    if not config_usage:
        diagnostics.append("No explicit config usage detected")

    return AstArtifact(
        module=path.stem,
        source_file=str(path.resolve()),
        source_hash=sha256_file(path),
        adapter_version=ADAPTER_VERSION,
        parse_status="parsed",
        module_type=module_type,
        diagnostics=diagnostics,
        config_usage=config_usage,
        endpoints=endpoints,
        ui_evidence=ui_evidence,
        component_extends=component_extends,
        functions=functions,
    )


def infer_endpoints(path: Path, source_bytes: bytes, elements: list[Node]) -> list[str]:
    """Infer endpoints from the file name and any cfform actions."""
    endpoints = []
    if path.suffix.lower() == ".cfm":
        endpoints.append("/" + path.stem)
        endpoints.append("/" + path.name)
    for element in _walk_elements(elements):
        if _tag_name(element, source_bytes) == "cfform":
            action = _attribute_map(_start_tag(element), source_bytes).get("action")
            if action:
                endpoints.append(action)
    return sorted(set(endpoints))


def _parse_component_functions(component_node: Node, source_bytes: bytes) -> list[FunctionNode]:
    functions = []
    for element in _walk_elements(component_node.children):
        if _tag_name(element, source_bytes) == "cffunction":
            functions.append(_parse_function_element(element, source_bytes))
    return functions


def _parse_function_element(function_node: Node, source_bytes: bytes) -> FunctionNode:
    start = _start_tag(function_node)
    attrs = _attribute_map(start, source_bytes)
    arguments: list[FunctionArgument] = []
    queries: list[QueryInfo] = []
    conditionals: list[str] = []
    scope_writes: list[str] = []
    throws: list[str] = []
    calls: set[str] = set()
    return_present = False

    for child in _walk_elements(function_node.children):
        tag_name = _tag_name(child, source_bytes)
        child_attrs = _attribute_map(_start_tag(child), source_bytes)
        child_text = _inner_text(child, source_bytes)
        calls.update(_extract_call_tokens(child_text))

        if tag_name == "cfargument":
            arguments.append(
                FunctionArgument(
                    name=child_attrs.get("name", "arg"),
                    type=child_attrs.get("type", "any"),
                    required=child_attrs.get("required", "false").lower() == "true",
                )
            )
        elif tag_name == "cfquery":
            queries.append(_parse_query_element(child, source_bytes))
        elif tag_name == "cfif":
            conditionals.append(_raw_attribute_payload(_start_tag(child), source_bytes).strip())
        elif tag_name == "cfset":
            payload = _raw_attribute_payload(_start_tag(child), source_bytes).strip()
            if payload.startswith(("session.", "application.", "variables.")):
                scope_writes.append(payload.split("=", 1)[0].strip())
        elif tag_name == "cfthrow":
            throw_type = child_attrs.get("type")
            if throw_type:
                throws.append(throw_type)
        elif tag_name == "cfreturn":
            return_present = True

    return FunctionNode(
        name=attrs.get("name", "unnamed_function"),
        access=attrs.get("access", "public"),
        return_type=attrs.get("returntype", "any"),
        arguments=arguments,
        queries=queries,
        conditionals=conditionals,
        scope_writes=sorted(set(scope_writes)),
        calls=sorted(calls - {"createObject", "structKeyExists", "hashVerify", "dateAdd", "now", "isDefined"}),
        throws=sorted(set(throws)),
        return_present=return_present or ("<cfreturn" in _inner_text(function_node, source_bytes).lower()),
    )


def _parse_query_element(query_node: Node, source_bytes: bytes) -> QueryInfo:
    start = _start_tag(query_node)
    attrs = _attribute_map(start, source_bytes)
    body = _inner_text(query_node, source_bytes)
    sql_excerpt = " ".join(body.split())
    operation = _detect_sql_operation(sql_excerpt)
    tables = sorted(set(_extract_tables(sql_excerpt)))
    return QueryInfo(
        name=attrs.get("name", "anonymous_query"),
        operation=operation,
        tables=tables,
        parameterized="<cfqueryparam" in body.lower(),
        sql_excerpt=sql_excerpt[:220],
    )


def _parse_template_function(path: Path, source_bytes: bytes, root: Node) -> FunctionNode:
    arguments: list[FunctionArgument] = []
    conditionals: list[str] = []
    raw_calls: set[str] = set()
    queries: list[QueryInfo] = []
    object_aliases: dict[str, str] = {}
    for element in _walk_elements(root.children):
        tag_name = _tag_name(element, source_bytes)
        attrs = _attribute_map(_start_tag(element), source_bytes)
        text = _inner_text(element, source_bytes)
        extracted_calls = _extract_call_tokens(text)
        if tag_name == "cfinput":
            name = attrs.get("name")
            if name:
                arguments.append(FunctionArgument(name=name, type="string", required=attrs.get("required", "false").lower() == "true"))
        elif tag_name == "cfif":
            conditionals.append(_raw_attribute_payload(_start_tag(element), source_bytes).strip())
        elif tag_name == "cfquery":
            queries.append(_parse_query_element(element, source_bytes))
        elif tag_name == "cfset":
            payload = _raw_attribute_payload(_start_tag(element), source_bytes).strip()
            alias = _extract_createobject_alias(payload)
            if alias:
                object_aliases[alias[0]] = alias[1]
        elif tag_name == "cfform":
            extracted_calls = {call for call in extracted_calls if not call.startswith("/")}
        raw_calls.update(extracted_calls)
    calls = _normalize_call_aliases(raw_calls, object_aliases)
    return FunctionNode(
        name="render_" + path.stem.replace("-", "_"),
        access="public",
        return_type="html",
        arguments=arguments,
        queries=queries,
        conditionals=conditionals,
        scope_writes=[],
        calls=sorted(calls - {"structKeyExists", "isDefined"}),
        throws=[],
        return_present=False,
    )


def _extract_createobject_alias(payload: str) -> tuple[str, str] | None:
    match = re.search(
        r"""^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*createObject\(\s*["']component["']\s*,\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""",
        payload,
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1), match.group(2)


def _normalize_call_aliases(calls: set[str], object_aliases: dict[str, str]) -> set[str]:
    normalized: set[str] = set()
    for call in calls:
        if "." in call:
            prefix, suffix = call.split(".", 1)
            target = object_aliases.get(prefix)
            if target:
                normalized.add(f"{target}.{suffix}")
                continue
        normalized.add(call)
    return normalized


def _extract_template_ui_evidence(root: Node, source_bytes: bytes) -> dict[str, object]:
    title = None
    headings: list[str] = []
    stylesheets: list[str] = []
    forms: list[dict[str, object]] = []
    links: list[dict[str, str]] = []
    redirects: list[str] = []
    error_regions: list[str] = []

    for element in _walk_elements(root.children):
        tag_name = _tag_name(element, source_bytes)
        attrs = _attribute_map(_start_tag(element), source_bytes)
        text_content = _visible_text(element, source_bytes)

        if tag_name == "title" and not title:
            title = text_content
        elif tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"} and text_content:
            headings.append(text_content)
        elif tag_name == "link" and attrs.get("rel", "").lower() == "stylesheet" and attrs.get("href"):
            stylesheets.append(attrs["href"])
        elif tag_name == "cfform":
            forms.append(_extract_form_evidence(element, source_bytes))
        elif tag_name == "a" and attrs.get("href"):
            links.append({"href": attrs["href"], "text": text_content or attrs["href"]})
        elif tag_name == "cflocation" and attrs.get("url"):
            redirects.append(attrs["url"])
        elif text_content and "error" in attrs.get("class", "").lower():
            error_regions.append(text_content)

    return {
        "title": title,
        "headings": headings,
        "stylesheets": stylesheets,
        "forms": forms,
        "links": links,
        "redirects": redirects,
        "errorRegions": error_regions,
    }


def _extract_form_evidence(form_node: Node, source_bytes: bytes) -> dict[str, object]:
    attrs = _attribute_map(_start_tag(form_node), source_bytes)
    inputs: list[dict[str, object]] = []
    submit_labels: list[str] = []
    labels: dict[str, str] = {}

    for element in _walk_elements(form_node.children):
        if _tag_name(element, source_bytes) != "label":
            continue
        label_attrs = _attribute_map(_start_tag(element), source_bytes)
        target = label_attrs.get("for")
        text = _visible_text(element, source_bytes)
        if target and text:
            labels[target] = text

    for element in _walk_elements(form_node.children):
        tag_name = _tag_name(element, source_bytes)
        child_attrs = _attribute_map(_start_tag(element), source_bytes)
        if tag_name == "cfinput":
            input_id = child_attrs.get("id")
            input_name = child_attrs.get("name")
            inputs.append(
                {
                    "name": input_name,
                    "id": input_id,
                    "label": labels.get(input_id or "", labels.get(input_name or "", "")) or None,
                    "type": child_attrs.get("type", "text"),
                    "required": child_attrs.get("required", "false").lower() == "true",
                    "validate": child_attrs.get("validate"),
                    "message": child_attrs.get("message"),
                }
            )
        elif tag_name == "input" and child_attrs.get("type", "").lower() == "submit":
            submit_labels.append(child_attrs.get("value") or _visible_text(element, source_bytes))

    return {
        "action": attrs.get("action"),
        "method": attrs.get("method", "get").lower(),
        "inputs": inputs,
        "submitLabels": [label for label in submit_labels if label],
    }


def _find_first_tag(elements: list[Node], source_bytes: bytes, tag: str) -> Node | None:
    for element in _iter_elements(elements):
        if _tag_name(element, source_bytes) == tag:
            return element
    return None


def _iter_elements(nodes: Iterable[Node]) -> Iterable[Node]:
    for node in nodes:
        if node.type == "element" and _has_start_tag(node):
            yield node


def _walk_elements(nodes: Iterable[Node]) -> Iterable[Node]:
    for node in nodes:
        if node.type != "element":
            continue
        if _has_start_tag(node):
            yield node
        yield from _walk_elements(node.children)


def _start_tag(element: Node) -> Node:
    for child in element.children:
        if child.type == "start_tag":
            return child
    raise ValueError("element missing start_tag")


def _has_start_tag(element: Node) -> bool:
    for child in element.children:
        if child.type == "start_tag":
            return True
    return False


def _tag_name(element: Node, source_bytes: bytes) -> str:
    if not _has_start_tag(element):
        return ""
    start_tag = _start_tag(element)
    for child in start_tag.children:
        if child.type == "tag_name":
            return _node_text(child, source_bytes).lower()
    return ""


def _attribute_map(start_tag: Node, source_bytes: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    for child in start_tag.children:
        if child.type == "attribute":
            name = None
            value = ""
            for grandchild in child.children:
                if grandchild.type == "attribute_name":
                    name = _node_text(grandchild, source_bytes)
                elif grandchild.type == "quoted_attribute_value":
                    raw = _node_text(grandchild, source_bytes)
                    value = raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
            if name:
                values[name.lower()] = value
    return values


def _raw_attribute_payload(start_tag: Node, source_bytes: bytes) -> str:
    text = _node_text(start_tag, source_bytes)
    first_space = text.find(" ")
    if first_space == -1:
        return ""
    return text[first_space + 1 : text.rfind(">")].strip()


def _inner_text(node: Node, source_bytes: bytes) -> str:
    text = _node_text(node, source_bytes)
    if text.startswith("<") and "</" in text:
        first_close = text.find(">")
        last_open = text.rfind("</")
        if first_close != -1 and last_open != -1 and last_open > first_close:
            return text[first_close + 1 : last_open]
    return text


def _visible_text(node: Node, source_bytes: bytes) -> str:
    text = _inner_text(node, source_bytes)
    text = " ".join(text.replace("\n", " ").split())
    text = text.replace("<cfoutput>", "").replace("</cfoutput>", "")
    return text.strip()


def _node_text(node: Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", "ignore")


def _collect_prefixed_tokens(text: str, prefixes: list[str]) -> set[str]:
    token = []
    results: set[str] = set()
    for char in text:
        if char.isalnum() or char in "._":
            token.append(char)
        else:
            _commit_token("".join(token), prefixes, results)
            token = []
    _commit_token("".join(token), prefixes, results)
    return results


def _commit_token(token: str, prefixes: list[str], results: set[str]) -> None:
    if any(token.startswith(prefix) for prefix in prefixes):
        results.add(token)


def _extract_call_tokens(text: str) -> set[str]:
    calls: set[str] = set()
    token = []
    for index, char in enumerate(text):
        if char.isalnum() or char in "._":
            token.append(char)
            continue
        if char == "(" and token:
            calls.add("".join(token))
        token = []
    return calls


def _detect_sql_operation(sql: str) -> str:
    upper = sql.upper()
    for candidate in ["SELECT", "UPDATE", "INSERT", "DELETE"]:
        if candidate in upper:
            return candidate
    return "UNKNOWN"


def _extract_tables(sql: str) -> Iterable[str]:
    normalized = sql.replace("(", " ").replace(")", " ").replace(",", " ").replace("\n", " ")
    tokens = normalized.split()
    upper_tokens = [token.upper() for token in tokens]
    for index, token in enumerate(upper_tokens):
        if token in {"FROM", "JOIN", "UPDATE", "INTO"} and index + 1 < len(tokens):
            yield tokens[index + 1]
