"""
EKG extractor: docker-compose.yaml -> Docker service nodes + Setting (env
var) nodes. Parsed with `yaml.safe_load`, not regex - compose files are
structured YAML, so there is no reason to hand-parse them.

Scope: this pilot models the Docker/Setting layer once for the whole
project (it is not per-app), so it is meant to be extracted a single time
and merged into whichever app-scoped graph is being built.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from tools.ekg import schema

ENV_VAR_RE = re.compile(r"\$\{([A-Z0-9_]+)(?::[?-][^}]*)?\}")


def extract_docker_compose(project_root: Path) -> schema.Graph:
    graph = schema.Graph()
    path = project_root / "docker-compose.yaml"
    if not path.exists():
        return graph

    compose = yaml.safe_load(path.read_text(encoding="utf-8"))
    services = compose.get("services", {}) if compose else {}

    for name, definition in services.items():
        if not isinstance(definition, dict):
            continue
        docker_node_id = schema.docker_service_id(name)
        graph.add_node(
            schema.Node(
                docker_node_id,
                schema.NODE_DOCKER,
                {
                    "name": name,
                    "image": definition.get("image", ""),
                    "container_name": definition.get("container_name", ""),
                },
            )
        )

        depends_on = definition.get("depends_on", {})
        dep_names = list(depends_on.keys()) if isinstance(depends_on, dict) else list(depends_on or [])
        for dep_name in dep_names:
            dep_node_id = schema.docker_service_id(dep_name)
            graph.add_node(schema.Node(dep_node_id, schema.NODE_DOCKER, {"name": dep_name}))
            graph.add_edge(schema.Edge(docker_node_id, dep_node_id, schema.REL_DEPENDS_ON))

        env_vars: set[str] = set()
        env_block = definition.get("environment")
        if isinstance(env_block, dict):
            for value in env_block.values():
                env_vars.update(ENV_VAR_RE.findall(str(value)))
        elif isinstance(env_block, list):
            for item in env_block:
                env_vars.update(ENV_VAR_RE.findall(str(item)))

        for var_name in env_vars:
            setting_node_id = schema.setting_id(var_name)
            graph.add_node(schema.Node(setting_node_id, schema.NODE_SETTING, {"name": var_name}))
            graph.add_edge(schema.Edge(docker_node_id, setting_node_id, schema.REL_USES))

    return graph
