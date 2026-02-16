"""Service for managing configurable review workflows."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_workflow import ReviewWorkflow, ResourceWorkflowBinding, ReviewRecord


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


async def get_total_steps(resource_type: str, db: AsyncSession) -> int:
    """Get the total number of steps for a resource type's workflow."""
    workflow = await get_workflow_for_resource(resource_type, db)
    if not workflow or not workflow.steps:
        return 1  # Default single-step
    return len(workflow.steps)


async def submit_review(
    resource_type: str,
    resource_id: uuid.UUID,
    current_step: int,
    action: str,
    reviewer_id: uuid.UUID,
    note: str | None,
    db: AsyncSession,
) -> dict:
    """Submit a review action for a resource.
    
    Returns dict with:
        - new_status: the new status string
        - new_step: the new current_step value
        - is_final: whether this was the final step
    """
    workflow = await get_workflow_for_resource(resource_type, db)
    total_steps = len(workflow.steps) if workflow and workflow.steps else 1
    
    # The step being reviewed is current_step + 1 (0-indexed current_step)
    review_step = current_step + 1

    # Record the review action
    record = ReviewRecord(
        resource_type=resource_type,
        resource_id=resource_id,
        step=review_step,
        action=action,
        reviewer_id=reviewer_id,
        note=note,
    )
    db.add(record)

    if action == "reject":
        return {
            "new_status": "rejected",
            "new_step": current_step,
            "is_final": True,
        }
    
    # action == "approve"
    if review_step >= total_steps:
        # Final step - fully approved
        return {
            "new_status": "approved",
            "new_step": review_step,
            "is_final": True,
        }
    else:
        # More steps remain
        return {
            "new_status": "reviewing",
            "new_step": review_step,
            "is_final": False,
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
    
    records = []
    for row in result.all():
        record = row[0]
        username = row[1]
        real_name = row[2]
        records.append({
            "id": str(record.id),
            "step": record.step,
            "action": record.action,
            "reviewer_id": str(record.reviewer_id),
            "reviewer_name": real_name or username or "",
            "note": record.note,
            "created_at": record.created_at.isoformat(),
        })
    return records


# --- Workflow CRUD ---

async def list_workflows(db: AsyncSession) -> list[dict]:
    """List all workflow templates."""
    result = await db.execute(
        select(ReviewWorkflow).order_by(ReviewWorkflow.created_at.asc())
    )
    workflows = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "code": w.code,
            "steps": w.steps,
            "is_system": w.is_system,
            "created_at": w.created_at.isoformat(),
            "updated_at": w.updated_at.isoformat(),
        }
        for w in workflows
    ]


async def create_workflow(name: str, code: str, steps: list[dict], db: AsyncSession) -> dict:
    """Create a new workflow template."""
    workflow = ReviewWorkflow(
        name=name,
        code=code,
        steps=steps,
        is_system=False,
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "code": workflow.code,
        "steps": workflow.steps,
        "is_system": workflow.is_system,
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


async def update_workflow(workflow_id: uuid.UUID, name: str | None, steps: list[dict] | None, db: AsyncSession) -> dict:
    """Update a workflow template."""
    result = await db.execute(
        select(ReviewWorkflow).where(ReviewWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise ValueError("Workflow not found")

    if name is not None:
        workflow.name = name
    if steps is not None:
        workflow.steps = steps
    workflow.updated_at = datetime.now(timezone.utc)
    
    await db.flush()
    await db.refresh(workflow)
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "code": workflow.code,
        "steps": workflow.steps,
        "is_system": workflow.is_system,
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


async def delete_workflow(workflow_id: uuid.UUID, db: AsyncSession) -> None:
    """Delete a workflow (only if not bound to any resource)."""
    # Check if bound
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
        select(ResourceWorkflowBinding, ReviewWorkflow.name, ReviewWorkflow.code, ReviewWorkflow.steps)
        .outerjoin(ReviewWorkflow, ReviewWorkflow.id == ResourceWorkflowBinding.workflow_id)
        .order_by(ResourceWorkflowBinding.resource_type)
    )
    bindings = []
    for row in result.all():
        binding = row[0]
        wf_name = row[1]
        wf_code = row[2]
        wf_steps = row[3]
        bindings.append({
            "id": str(binding.id),
            "resource_type": binding.resource_type,
            "workflow_id": str(binding.workflow_id),
            "workflow_name": wf_name,
            "workflow_code": wf_code,
            "workflow_steps": wf_steps,
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
    
    # Fetch workflow info
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
        "workflow_steps": workflow.steps if workflow else [],
        "enabled": binding.enabled,
        "created_at": binding.created_at.isoformat(),
    }
