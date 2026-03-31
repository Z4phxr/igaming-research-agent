"""Prompt manager endpoints for editable LLM prompts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    PromptTemplateDetailOut,
    PromptTemplateDraftUpdate,
    PromptTemplateOut,
    PromptTemplatePublishRequest,
    PromptTemplateVersionOut,
)
from app.services import prompt_manager

router = APIRouter()


@router.get("", response_model=list[PromptTemplateOut])
def list_prompt_templates(db: Session = Depends(get_db)):
    prompt_manager.ensure_default_prompt_templates(db)
    db.commit()
    return prompt_manager.list_templates(db)


@router.get("/{prompt_key}", response_model=PromptTemplateDetailOut)
def get_prompt_template(prompt_key: str, db: Session = Depends(get_db)):
    prompt_manager.ensure_default_prompt_templates(db)
    db.commit()

    template = prompt_manager.get_template(db, prompt_key)
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    history = prompt_manager.list_history(db, prompt_key) or []
    payload = PromptTemplateDetailOut.model_validate(template)
    payload.history = [PromptTemplateVersionOut.model_validate(item) for item in history]
    return payload


@router.put("/{prompt_key}/draft", response_model=PromptTemplateOut)
def update_prompt_draft(prompt_key: str, payload: PromptTemplateDraftUpdate, db: Session = Depends(get_db)):
    prompt_manager.ensure_default_prompt_templates(db)
    db.commit()
    template = prompt_manager.save_draft(db, prompt_key, payload.draft_content)
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template


@router.post("/{prompt_key}/publish", response_model=PromptTemplateOut)
def publish_prompt(prompt_key: str, payload: PromptTemplatePublishRequest, db: Session = Depends(get_db)):
    prompt_manager.ensure_default_prompt_templates(db)
    db.commit()
    template = prompt_manager.publish(db, prompt_key, payload.content)
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found or empty content")
    return template


@router.get("/{prompt_key}/history", response_model=list[PromptTemplateVersionOut])
def get_prompt_history(prompt_key: str, db: Session = Depends(get_db)):
    prompt_manager.ensure_default_prompt_templates(db)
    db.commit()
    history = prompt_manager.list_history(db, prompt_key)
    if history is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return history
