"""Retention policy and rule management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_read_session, get_session
from ai_memory_layer.models.memory import RetentionPolicy, RetentionRule
from ai_memory_layer.models.user import User
from ai_memory_layer.schemas.retention import (
    RetentionExecutionResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
    RetentionRuleCreate,
    RetentionRuleResponse,
    RetentionRuleUpdate,
)
from ai_memory_layer.security import get_current_active_user, get_tenant_id_from_user, require_admin
from ai_memory_layer.services.advanced_retention import AdvancedRetentionService

router = APIRouter(prefix="/retention", tags=["retention"])
retention_service = AdvancedRetentionService()


@router.get("/policy", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> RetentionPolicyResponse:
    """Get retention policy for a tenant."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    stmt = select(RetentionPolicy).where(RetentionPolicy.tenant_id == tenant_id)
    result = await session.execute(stmt)
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention policy not found",
        )
    
    return RetentionPolicyResponse.model_validate(policy)


@router.put("/policy", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    policy_update: RetentionPolicyUpdate,
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> RetentionPolicyResponse:
    """Update retention policy for a tenant."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    stmt = select(RetentionPolicy).where(RetentionPolicy.tenant_id == tenant_id)
    result = await session.execute(stmt)
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention policy not found",
        )
    
    update_data = policy_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(policy, key, value)
    
    await session.commit()
    await session.refresh(policy)
    
    return RetentionPolicyResponse.model_validate(policy)


@router.post("/rules", response_model=RetentionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_retention_rule(
    rule_data: RetentionRuleCreate,
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> RetentionRuleResponse:
    """Create a new retention rule."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    rule = RetentionRule(
        tenant_id=tenant_id,
        name=rule_data.name,
        description=rule_data.description,
        rule_type=rule_data.rule_type,
        conditions=rule_data.conditions,
        action=rule_data.action,
        priority=rule_data.priority,
        enabled=rule_data.enabled,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    
    return RetentionRuleResponse.model_validate(rule)


@router.get("/rules", response_model=list[RetentionRuleResponse])
async def list_retention_rules(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    enabled_only: bool = Query(False, description="Only return enabled rules"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> list[RetentionRuleResponse]:
    """List retention rules for a tenant."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    stmt = select(RetentionRule).where(RetentionRule.tenant_id == tenant_id)
    if enabled_only:
        stmt = stmt.where(RetentionRule.enabled == True)  # noqa: E712
    
    stmt = stmt.order_by(RetentionRule.priority.asc(), RetentionRule.created_at.desc())
    result = await session.execute(stmt)
    rules = result.scalars().all()
    
    return [RetentionRuleResponse.model_validate(rule) for rule in rules]


@router.get("/rules/{rule_id}", response_model=RetentionRuleResponse)
async def get_retention_rule(
    rule_id: int,
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_read_session)] = None,
) -> RetentionRuleResponse:
    """Get a specific retention rule."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    stmt = select(RetentionRule).where(RetentionRule.id == rule_id)
    if tenant_id:
        stmt = stmt.where(RetentionRule.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found",
        )
    
    return RetentionRuleResponse.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=RetentionRuleResponse)
async def update_retention_rule(
    rule_id: int,
    rule_update: RetentionRuleUpdate,
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> RetentionRuleResponse:
    """Update a retention rule."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    stmt = select(RetentionRule).where(RetentionRule.id == rule_id)
    if tenant_id:
        stmt = stmt.where(RetentionRule.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found",
        )
    
    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(rule, key, value)
    
    await session.commit()
    await session.refresh(rule)
    
    return RetentionRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_retention_rule(
    rule_id: int,
    tenant_id: str | None = Query(None, description="Tenant ID"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> None:
    """Delete a retention rule."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    stmt = select(RetentionRule).where(RetentionRule.id == rule_id)
    if tenant_id:
        stmt = stmt.where(RetentionRule.tenant_id == tenant_id)
    
    result = await session.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found",
        )
    
    await session.delete(rule)
    await session.commit()


@router.post("/execute", response_model=RetentionExecutionResponse)
async def execute_retention(
    tenant_id: str | None = Query(None, description="Tenant ID"),
    dry_run: bool = Query(False, description="Perform a dry run without making changes"),
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> RetentionExecutionResponse:
    """Execute retention rules for a tenant."""
    if current_user:
        tenant_id = get_tenant_id_from_user(current_user) or tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required",
        )
    
    result = await retention_service.apply_retention_rules(
        session=session,
        tenant_id=tenant_id,
        dry_run=dry_run,
    )
    
    return RetentionExecutionResponse(**result)

