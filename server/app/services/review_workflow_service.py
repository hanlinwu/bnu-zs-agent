"""Service for managing configurable state-machine workflows."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_workflow import ReviewWorkflow, ResourceWorkflowBinding, ReviewRecord


# --- Pure functions on workflow definition ---

def get_definition(workflow: ReviewWorkflow) -> dict:
    """Get the definition dict, falling back to empty structure."""
    if workflow.definition:
        return workflow.definition
    return {"nodes": [], "actions": [], "transitions": []}


def get_start_node(workflow: ReviewWorkflow) -> str | None:
    """Return the ID of the start node."""
    defn = get_definition(workflow)
    for node in defn.get("nodes", []):
        if node.get("type") == "start":
            return node["id"]
    return None


def get_node_info(workflow: ReviewWorkflow, node_id: str) -> dict | None:
    """Get full node definition by ID."""
    defn = get_definition(workflow)
    for node in defn.get("nodes", []):
        if node["id"] == node_id:
            return node
    return None


def get_all_nodes(workflow: ReviewWorkflow) -> list[dict]:
    """Get all nodes from workflow definition."""
    return get_definition(workflow).get("nodes", [])


def get_all_actions(workflow: ReviewWorkflow) -> list[dict]:
    """Get all actions from workflow definition."""
    return get_definition(workflow).get("actions", [])


def get_available_actions(workflow: ReviewWorkflow, current_node: str) -> list[dict]:
    """Return actions available at the given node: [{id, name}]."""
    defn = get_definition(workflow)
    transitions = defn.get("transitions", [])
    actions = defn.get("actions", [])
    action_map = {a["id"]: a for a in actions}

    available_action_ids = set()
    for t in transitions:
        if t["from_node"] == current_node:
            available_action_ids.add(t["action"])

    return [action_map[aid] for aid in available_action_ids if aid in action_map]


def get_next_node(workflow: ReviewWorkflow, current_node: str, action: str) -> str | None:
    """Given current node + action, return the target node ID."""
    defn = get_definition(workflow)
    for t in defn.get("transitions", []):
        if t["from_node"] == current_node and t["action"] == action:
            return t["to_node"]
    return None


def is_terminal_node(workflow: ReviewWorkflow, node_id: str) -> bool:
    """Check if a node is a terminal state."""
    node = get_node_info(workflow, node_id)
    return node is not None and node.get("type") == "terminal"


def compute_status_from_node(workflow: ReviewWorkflow, node_id: str) -> str:
    """Derive a status string from the current node for backward compatibility."""
    node = get_node_info(workflow, node_id)
    if not node:
        return node_id
    node_type = node.get("type", "")
    if node_type == "start":
        return "pending"
    elif node_type == "terminal":
        return node_id
    else:
        return "reviewing"


# --- Async service functions ---

async def get_workflow_for_resource(resource_type: str, db: AsyncSession) -> ReviewWorkflow | None:
    """Get the active workflow bound to a resource type."""
    result = await db.execute(
        select(ReviewWorkflow)
        .join(ResourceWorkflowBinding, ResourceWorkflowBinding.workflow_id == ReviewWorkflow.id)
        .where(
            ResourceWorkflowBinding.resource_type == resource_type,
            ResourceWorkflowBinding.enabled == True,
        )
    )
    return result.scalar_one_or_none()


async def get_workflow_definition_for_resource(resource_type: str, db: AsyncSession) -> dict | None:
    """Get the full workflow definition for a resource type (for frontend rendering)."""
    workflow = await get_workflow_for_resource(resource_type, db)
    if not workflow:
        return None
    defn = get_definition(workflow)
    return {
        "workflow_id": str(workflow.id),
        "workflow_name": workflow.name,
        "workflow_code": workflow.code,
        **defn,
    }


async def execute_action(
    resource_type: str,
    resource_id: uuid.UUID,
    current_node: str,
    action: str,
    reviewer_id: uuid.UUID,
    note: str | None,
    db: AsyncSession,
) -> dict:
    """Execute a workflow action.

    Returns dict with:
        - new_node: the target node ID
        - new_status: derived status string for backward compat
        - is_terminal: whether the target is a terminal node
    """
    workflow = await get_workflow_for_resource(resource_type, db)
    if not workflow:
        raise ValueError(f"No active workflow bound to resource type '{resource_type}'")

    # Validate action is available at current node
    available = get_available_actions(workflow, current_node)
    available_ids = {a["id"] for a in available}
    if action not in available_ids:
        raise ValueError(f"Action '{action}' is not available at node '{current_node}'")

    # Compute target node
    to_node = get_next_node(workflow, current_node, action)
    if not to_node:
        raise ValueError(f"No transition defined for node '{current_node}' + action '{action}'")

    # Create review record
    record = ReviewRecord(
        resource_type=resource_type,
        resource_id=resource_id,
        from_node=current_node,
        action=action,
        to_node=to_node,
        reviewer_id=reviewer_id,
        note=note,
    )
    db.add(record)

    new_status = compute_status_from_node(workflow, to_node)
    terminal = is_terminal_node(workflow, to_node)

    return {
        "new_node": to_node,
        "new_status": new_status,
        "is_terminal": terminal,
    }


async def get_review_history(
    resource_type: str,
    resource_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    """Get review history for a resource."""
    from app.models.admin import AdminUser

    result = await db.execute(
        select(ReviewRecord, AdminUser.username, AdminUser.real_name)
        .outerjoin(AdminUser, AdminUser.id == ReviewRecord.reviewer_id)
        .where(
            ReviewRecord.resource_type == resource_type,
            ReviewRecord.resource_id == resource_id,
        )
        .order_by(ReviewRecord.created_at.asc())
    )

    # Get workflow for node name resolution
    workflow = await get_workflow_for_resource(resource_type, db)
    node_names = {}
    action_names = {}
    if workflow:
        defn = get_definition(workflow)
        node_names = {n["id"]: n["name"] for n in defn.get("nodes", [])}
        action_names = {a["id"]: a["name"] for a in defn.get("actions", [])}

    records = []
    for row in result.all():
        record = row[0]
        username = row[1]
        real_name = row[2]
        records.append({
            "id": str(record.id),
            "from_node": record.from_node,
            "from_node_name": node_names.get(record.from_node, record.from_node) if record.from_node else "",
            "action": record.action,
            "action_name": action_names.get(record.action, record.action),
            "to_node": record.to_node,
            "to_node_name": node_names.get(record.to_node, record.to_node) if record.to_node else "",
            "reviewer_id": str(record.reviewer_id),
            "reviewer_name": real_name or username or "",
            "note": record.note,
            "created_at": record.created_at.isoformat(),
        })
    return records


# --- Workflow CRUD ---

def _workflow_to_dict(w: ReviewWorkflow) -> dict:
    """Serialize a workflow to API response dict."""
    return {
        "id": str(w.id),
        "name": w.name,
        "code": w.code,
        "definition": w.definition or {"nodes": [], "actions": [], "transitions": []},
        "is_system": w.is_system,
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


async def list_workflows(db: AsyncSession) -> list[dict]:
    """List all workflow templates."""
    result = await db.execute(
        select(ReviewWorkflow).order_by(ReviewWorkflow.created_at.asc())
    )
    return [_workflow_to_dict(w) for w in result.scalars().all()]


async def create_workflow(name: str, code: str, definition: dict, db: AsyncSession) -> dict:
    """Create a new workflow template."""
    workflow = ReviewWorkflow(
        name=name,
        code=code,
        definition=definition,
        is_system=False,
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)
    return _workflow_to_dict(workflow)


async def update_workflow(workflow_id: uuid.UUID, name: str | None, definition: dict | None, db: AsyncSession) -> dict:
    """Update a workflow template."""
    result = await db.execute(
        select(ReviewWorkflow).where(ReviewWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise ValueError("Workflow not found")

    if name is not None:
        workflow.name = name
    if definition is not None:
        workflow.definition = definition
    workflow.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(workflow)
    return _workflow_to_dict(workflow)


async def delete_workflow(workflow_id: uuid.UUID, db: AsyncSession) -> None:
    """Delete a workflow (only if not bound to any resource)."""
    binding = await db.execute(
        select(ResourceWorkflowBinding).where(ResourceWorkflowBinding.workflow_id == workflow_id)
    )
    if binding.scalar_one_or_none():
        raise ValueError("Cannot delete workflow that is bound to a resource type")

    result = await db.execute(
        select(ReviewWorkflow).where(ReviewWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise ValueError("Workflow not found")
    if workflow.is_system:
        raise ValueError("Cannot delete system workflow")

    await db.delete(workflow)


async def list_bindings(db: AsyncSession) -> list[dict]:
    """List all resource-workflow bindings."""
    result = await db.execute(
        select(ResourceWorkflowBinding, ReviewWorkflow.name, ReviewWorkflow.code, ReviewWorkflow.definition)
        .outerjoin(ReviewWorkflow, ReviewWorkflow.id == ResourceWorkflowBinding.workflow_id)
        .order_by(ResourceWorkflowBinding.resource_type)
    )
    bindings = []
    for row in result.all():
        binding = row[0]
        wf_name = row[1]
        wf_code = row[2]
        wf_definition = row[3]
        bindings.append({
            "id": str(binding.id),
            "resource_type": binding.resource_type,
            "workflow_id": str(binding.workflow_id),
            "workflow_name": wf_name,
            "workflow_code": wf_code,
            "workflow_definition": wf_definition or {"nodes": [], "actions": [], "transitions": []},
            "enabled": binding.enabled,
            "created_at": binding.created_at.isoformat(),
        })
    return bindings


async def update_binding(resource_type: str, workflow_id: uuid.UUID | None, enabled: bool | None, db: AsyncSession) -> dict:
    """Update or create a resource-workflow binding."""
    result = await db.execute(
        select(ResourceWorkflowBinding).where(ResourceWorkflowBinding.resource_type == resource_type)
    )
    binding = result.scalar_one_or_none()

    if binding:
        if workflow_id is not None:
            binding.workflow_id = workflow_id
        if enabled is not None:
            binding.enabled = enabled
    else:
        if workflow_id is None:
            raise ValueError("workflow_id is required when creating a new binding")
        binding = ResourceWorkflowBinding(
            resource_type=resource_type,
            workflow_id=workflow_id,
            enabled=enabled if enabled is not None else True,
        )
        db.add(binding)

    await db.flush()
    await db.refresh(binding)

    wf = await db.execute(
        select(ReviewWorkflow).where(ReviewWorkflow.id == binding.workflow_id)
    )
    workflow = wf.scalar_one_or_none()

    return {
        "id": str(binding.id),
        "resource_type": binding.resource_type,
        "workflow_id": str(binding.workflow_id),
        "workflow_name": workflow.name if workflow else "",
        "workflow_code": workflow.code if workflow else "",
        "workflow_definition": workflow.definition if workflow else {"nodes": [], "actions": [], "transitions": []},
        "enabled": binding.enabled,
        "created_at": binding.created_at.isoformat(),
    }
