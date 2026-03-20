"""Action-consequence association graph for Graph-RAG reflex arcs.

Implements a lightweight knowledge graph where:
- Nodes represent actions, systems, files, and concepts
- Edges represent relationships (requires_check, located_in, modifies, etc.)

This enables multi-hop reasoning:
  "create root file" → (requires_check) → "gitignore whitelist"
                     → (located_in) → "GitIgnoreManager.base_patterns"
                     → (file) → "logic/git/manager.py"

Graph-RAG research shows 94% accuracy on multi-hop queries vs 61% for
vector-only RAG (AAIA 2026). This module provides the graph layer;
vector search is handled by the RAG brain blueprint.

Storage: JSON file (action_graph.json) — human-readable, version-controllable.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set


class ActionGraph:
    """In-memory action-consequence association graph."""

    def __init__(self, graph_path: Optional[Path] = None):
        self.graph_path = graph_path
        self.nodes: Dict[str, dict] = {}
        self.edges: List[dict] = []
        if graph_path and graph_path.exists():
            self._load()

    def _load(self):
        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.nodes = {n["id"]: n for n in data.get("nodes", [])}
            self.edges = data.get("edges", [])
        except Exception:
            self.nodes = {}
            self.edges = []

    def save(self):
        if not self.graph_path:
            return
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "description": "Action-consequence association graph for multi-hop reflex arcs",
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_node(self, node_id: str, node_type: str, label: str,
                 description: str = "", **kwargs):
        """Add or update a node.

        node_type: action, system, file, concept, tool, pattern
        """
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "label": label,
            "description": description,
            **kwargs,
        }

    def add_edge(self, source: str, target: str, relation: str,
                 weight: float = 1.0, **kwargs):
        """Add a directed edge.

        relation types: requires_check, located_in, modifies, produces,
                       triggers, depends_on, replaces, conflicts_with
        """
        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
            **kwargs,
        })

    def traverse(self, start_id: str, max_hops: int = 3,
                 relation_filter: Optional[Set[str]] = None) -> List[List[dict]]:
        """Multi-hop traversal from a start node.

        Returns list of paths, each path being a list of
        {node, edge_relation, node, edge_relation, ...} dicts.
        """
        if start_id not in self.nodes:
            return []

        adjacency: Dict[str, List[dict]] = {}
        for edge in self.edges:
            src = edge["source"]
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(edge)

        paths = []
        queue = [([self.nodes[start_id]], 0)]

        while queue:
            path, depth = queue.pop(0)
            if depth >= max_hops:
                continue

            current_id = path[-1]["id"] if isinstance(path[-1], dict) and "id" in path[-1] else None
            if not current_id:
                continue

            for edge in adjacency.get(current_id, []):
                rel = edge["relation"]
                if relation_filter and rel not in relation_filter:
                    continue
                target_id = edge["target"]
                if target_id not in self.nodes:
                    continue
                target_node = self.nodes[target_id]
                if any(isinstance(p, dict) and p.get("id") == target_id for p in path):
                    continue
                new_path = path + [{"relation": rel}, target_node]
                paths.append(new_path)
                queue.append((new_path, depth + 1))

        paths.sort(key=len)
        return paths

    def query(self, action_text: str, max_hops: int = 3,
              start_types: Optional[Set[str]] = None) -> List[List[dict]]:
        """Find relevant paths by matching action text against graph nodes.

        By default matches against "action" type nodes. Set start_types
        to search other node types (e.g., {"action", "system"}).
        """
        if start_types is None:
            start_types = {"action"}

        action_words = set(action_text.lower().split())
        scored_starts = []

        for node in self.nodes.values():
            if node["type"] not in start_types:
                continue
            label_words = set(node["label"].lower().split())
            desc_words = set(node.get("description", "").lower().split())
            overlap = len(action_words & (label_words | desc_words))
            if overlap > 0:
                scored_starts.append((overlap, node["id"]))

        scored_starts.sort(key=lambda x: x[0], reverse=True)

        all_paths = []
        for _, start_id in scored_starts[:3]:
            paths = self.traverse(start_id, max_hops)
            all_paths.extend(paths)

        return all_paths

    def format_paths(self, paths: List[List[dict]], max_paths: int = 5) -> Optional[str]:
        """Format traversal paths as human-readable injection text."""
        if not paths:
            return None

        lines = ["[Graph-RAG Association — multi-hop reasoning]"]
        seen = set()

        for path in paths[:max_paths]:
            parts = []
            for item in path:
                if "label" in item:
                    parts.append(item["label"])
                elif "relation" in item:
                    parts.append(f"→({item['relation']})→")
            chain = " ".join(parts)
            if chain not in seen:
                seen.add(chain)
                lines.append(f"  {chain}")

        return "\n".join(lines) if len(lines) > 1 else None


def build_ecosystem_graph(root: Path) -> ActionGraph:
    """Build the core action-consequence graph for the ecosystem.

    This pre-seeds the graph with well-known associations.
    New associations can be added dynamically as lessons accumulate.
    """
    graph_path = root / "runtime" / "brain" / "action_graph.json"
    graph = ActionGraph(graph_path)

    # --- Action nodes ---
    graph.add_node("act:create_root_file", "action", "create root file",
                   "Creating a new file in the project root directory")
    graph.add_node("act:modify_tool_dir", "action", "modify tool directory",
                   "Creating or modifying directories under a tool")
    graph.add_node("act:cross_tool_import", "action", "cross-tool import",
                   "Writing import statements between tools or logic modules")
    graph.add_node("act:edit_brain", "action", "edit brain paths",
                   "Reading or writing brain instance data")
    graph.add_node("act:edit_documentation", "action", "edit documentation",
                   "Modifying README.md, AGENT.md, or AGENT_REFLECTION.md")
    graph.add_node("act:delete_symlink", "action", "delete symlink",
                   "Removing a symbolic link via rm or unlink")
    graph.add_node("act:install_tool", "action", "install tool",
                   "Running setup.py or TOOL install")
    graph.add_node("act:update_convention", "action", "update convention",
                   "Changing a root-level pattern or standard")

    # --- System nodes ---
    graph.add_node("sys:gitignore", "system", "gitignore system",
                   "Auto-generated .gitignore with deny-all + whitelist pattern")
    graph.add_node("sys:symmetric_dirs", "system", "symmetric directories",
                   "logic/ interface/ hooks/ data/ test/ pattern")
    graph.add_node("sys:import_rules", "system", "import rules",
                   "Interface facade: import from interface.*, not logic.*")
    graph.add_node("sys:brain_sessions", "system", "brain session management",
                   "BrainSessionManager for instance path resolution")
    graph.add_node("sys:doc_hierarchy", "system", "doc stability hierarchy",
                   "README=stable, for_agent=operational, for_agent_reflection=protocol")
    graph.add_node("sys:template", "system", "tool template",
                   "logic/tool/template/ for new tool scaffolding")

    # --- File nodes ---
    graph.add_node("file:git_manager", "file", "logic/git/manager.py",
                   "GitIgnoreManager with base_patterns")
    graph.add_node("file:for_agent", "file", "AGENT.md",
                   "Bootstrap guide, Section 9 covers gitignore")
    graph.add_node("file:tool_template", "file", "logic/tool/template/",
                   "Template files for TOOL --dev create")
    graph.add_node("file:brain_loader", "file", "logic/brain/loader.py",
                   "Blueprint loading and session resolution")
    graph.add_node("file:interface_main", "file", "interface/main.py",
                   "Cross-tool facade layer")

    # --- Edges: create root file ---
    graph.add_edge("act:create_root_file", "sys:gitignore", "requires_check")
    graph.add_edge("sys:gitignore", "file:git_manager", "located_in")
    graph.add_edge("file:git_manager", "file:for_agent", "documented_in",
                   weight=0.5, note="Section 9: Auto-Generated .gitignore")

    # --- Edges: modify tool dir ---
    graph.add_edge("act:modify_tool_dir", "sys:symmetric_dirs", "requires_check")
    graph.add_edge("sys:symmetric_dirs", "file:tool_template", "reference")

    # --- Edges: cross-tool import ---
    graph.add_edge("act:cross_tool_import", "sys:import_rules", "requires_check")
    graph.add_edge("sys:import_rules", "file:interface_main", "located_in")

    # --- Edges: brain editing ---
    graph.add_edge("act:edit_brain", "sys:brain_sessions", "requires_check")
    graph.add_edge("sys:brain_sessions", "file:brain_loader", "located_in")

    # --- Edges: documentation ---
    graph.add_edge("act:edit_documentation", "sys:doc_hierarchy", "requires_check")

    # --- Edges: delete symlink ---
    graph.add_edge("act:delete_symlink", "act:create_root_file", "may_trigger",
                   weight=0.3, note="Deleting symlinks can affect tracked files")

    # --- Edges: install tool ---
    graph.add_edge("act:install_tool", "sys:gitignore", "triggers",
                   note="setup.py calls GitIgnoreManager.rewrite() on every install")

    # --- Edges: update convention ---
    graph.add_edge("act:update_convention", "sys:template", "requires_check",
                   note="Root rules must cascade to templates")

    # ===================================================================
    # Capability dimensions — the meta-patterns from metacognitive probes.
    #
    # Each dimension represents an agent awareness category. When a user
    # asks "does the agent know about X?", these nodes + edges help the
    # graph surface what systems support that awareness and what gaps exist.
    #
    # The probe meta-template is:
    #   "想象一个没有context的assistant..." + [dimension] + "gap?" + "修缮"
    # ===================================================================

    # --- Agent awareness actions (meta-probes) ---
    graph.add_node("probe:discovery", "action", "discover tools skills",
                   "Agent exploring what tools, skills, and docs exist")
    graph.add_node("probe:convention", "action", "learn conventions patterns",
                   "Agent learning symmetric dirs, import rules, naming")
    graph.add_node("probe:self_test", "action", "self test iterate",
                   "Agent testing its own code, iterating on failures")
    graph.add_node("probe:environment", "action", "detect environment IDE",
                   "Agent recognizing Cursor, VS Code, or other IDE")
    graph.add_node("probe:feedback_loop", "action", "maintain feedback USERINPUT",
                   "Agent sustaining the USERINPUT feedback loop")
    graph.add_node("probe:knowledge_creation", "action", "create skills lessons",
                   "Agent creating skills, recording lessons, building tools")
    graph.add_node("probe:strategic_pivot", "action", "pivot strategy alternative",
                   "Agent recognizing failure and switching approach")
    graph.add_node("probe:hardening", "action", "harden strengthen infrastructure",
                   "Agent hardening infrastructure: quality, robustness, tests")
    graph.add_node("probe:brain_record", "action", "record brain log reflect",
                   "Agent recording work in the brain, reflecting on progress")
    graph.add_node("probe:interface_expose", "action", "expose interface facade",
                   "Agent exposing functionality via interface/main.py")

    # --- System support nodes for each dimension ---
    graph.add_node("sys:tool_search", "system", "TOOL --search",
                   "Semantic search across tools, skills, interfaces")
    graph.add_node("sys:skills_list", "system", "SKILLS list",
                   "Skill catalog with descriptions and categories")
    graph.add_node("sys:for_agent_md", "system", "AGENT.md bootstrap",
                   "Section 0 bootstraps agent with ecosystem overview")
    graph.add_node("sys:for_agent_reflection", "system", "AGENT_REFLECTION.md",
                   "Self-check protocol, system gaps, reflexive awareness")
    graph.add_node("sys:brain_commands", "system", "BRAIN commands",
                   "log, reflect, recall, snapshot, digest")
    graph.add_node("sys:userinput", "system", "USERINPUT tool",
                   "Blocking feedback loop with user")
    graph.add_node("sys:hooks", "system", "IDE hooks",
                   "sessionStart, postToolUse, stop — auto-inject context")
    graph.add_node("sys:audit_tools", "system", "audit commands",
                   "TOOL --audit code, --audit imports, --audit quality")
    graph.add_node("sys:knowledge_pipeline", "system", "knowledge pipeline",
                   "lesson → skill → infrastructure → hook progression")
    graph.add_node("sys:ide_detect", "system", "IDE detection",
                   "logic/setup/ide_detect.py — auto-detect and configure IDE")

    # --- File support nodes ---
    graph.add_node("file:for_agent_reflection", "file", "AGENT_REFLECTION.md",
                   "Root-level self-check protocol and gap tracking")
    graph.add_node("file:ide_detect", "file", "logic/setup/ide_detect.py",
                   "IDE auto-detection and hook deployment")
    graph.add_node("file:procedural", "file", "logic/brain/utils/procedural.py",
                   "Three-layer reflex arc matching (skills + lessons + graph)")

    # --- Edges: discovery dimension ---
    graph.add_edge("probe:discovery", "sys:tool_search", "supported_by")
    graph.add_edge("probe:discovery", "sys:skills_list", "supported_by")
    graph.add_edge("probe:discovery", "sys:for_agent_md", "bootstrapped_by")

    # --- Edges: convention dimension ---
    graph.add_edge("probe:convention", "sys:for_agent_md", "taught_by",
                   note="Symmetric dirs, import rules in AGENT.md")
    graph.add_edge("probe:convention", "sys:symmetric_dirs", "requires_check")
    graph.add_edge("probe:convention", "sys:import_rules", "requires_check")

    # --- Edges: self-test dimension ---
    graph.add_edge("probe:self_test", "sys:audit_tools", "supported_by")
    graph.add_edge("probe:self_test", "sys:for_agent_reflection", "guided_by")

    # --- Edges: environment awareness ---
    graph.add_edge("probe:environment", "sys:ide_detect", "supported_by")
    graph.add_edge("sys:ide_detect", "file:ide_detect", "located_in")
    graph.add_edge("probe:environment", "sys:hooks", "enables")

    # --- Edges: feedback loop ---
    graph.add_edge("probe:feedback_loop", "sys:userinput", "depends_on")
    graph.add_edge("probe:feedback_loop", "sys:hooks", "reinforced_by",
                   note="postToolUse hook re-injects USERINPUT reminder")

    # --- Edges: knowledge creation ---
    graph.add_edge("probe:knowledge_creation", "sys:knowledge_pipeline", "follows")
    graph.add_edge("probe:knowledge_creation", "sys:brain_commands", "uses")
    graph.add_edge("probe:knowledge_creation", "sys:for_agent_reflection", "guided_by",
                   note="Knowledge Creation self-check section")

    # --- Edges: strategic pivoting ---
    graph.add_edge("probe:strategic_pivot", "sys:tool_search", "uses",
                   note="Search for alternative tools/approaches")
    graph.add_edge("probe:strategic_pivot", "sys:for_agent_reflection", "guided_by",
                   note="Strategic Pivoting self-check section")

    # --- Edges: hardening ---
    graph.add_edge("probe:hardening", "sys:audit_tools", "uses")
    graph.add_edge("probe:hardening", "sys:knowledge_pipeline", "advances",
                   note="Harden = advance lessons→skills→infra→hooks")
    graph.add_edge("probe:hardening", "sys:for_agent_reflection", "guided_by",
                   note="Hardening Awareness self-check section")

    # --- Edges: brain recording ---
    graph.add_edge("probe:brain_record", "sys:brain_commands", "uses")
    graph.add_edge("probe:brain_record", "sys:for_agent_reflection", "guided_by")

    # --- Edges: interface exposure ---
    graph.add_edge("probe:interface_expose", "sys:import_rules", "follows")
    graph.add_edge("probe:interface_expose", "file:interface_main", "target")

    # --- Cross-dimension edges (how dimensions reinforce each other) ---
    graph.add_edge("probe:self_test", "probe:strategic_pivot", "escalates_to",
                   note="3+ failures → pivot approach")
    graph.add_edge("probe:strategic_pivot", "probe:knowledge_creation", "produces",
                   note="Pivots generate lessons worth recording")
    graph.add_edge("probe:knowledge_creation", "probe:hardening", "matures_into",
                   note="3+ lessons on same topic → skill → infrastructure")
    graph.add_edge("probe:feedback_loop", "probe:brain_record", "triggers",
                   note="USERINPUT milestone → BRAIN log")

    graph.save()
    return graph
