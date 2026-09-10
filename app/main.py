from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import (
    Ascent,
    Climber,
    Group,
    GroupClimber,
    Mountain,
    Report,
)
from app.schemas import (
    AscentCreate,
    AscentRead,
    ClimberCreate,
    ClimberRead,
    GroupClimberCreate,
    GroupClimberRead,
    GroupCreate,
    GroupRead,
    MountainCreate,
    MountainRead,
    ReportCreate,
    ReportRead,
)

load_dotenv()

app = FastAPI(
    title="Alpine Club API",
    version=os.getenv("APP_VERSION", "0.1.0"),
)

ALLOWED_EXPERIENCE_LEVELS = {"beginner", "intermediate", "advanced", "expert"}
ALLOWED_ROLES = {"member", "leader", "instructor", "medic"}
ALLOWED_REPORT_TYPES = {"final", "incident", "medical"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": "unavailable"},
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
        "version": os.getenv("APP_VERSION", "0.1.0"),
    }


@app.get("/api/mountains", response_model=list[MountainRead])
def list_mountains(db: Session = Depends(get_db)):
    return db.query(Mountain).all()


@app.post("/api/mountains", response_model=MountainRead, status_code=201)
def create_mountain(payload: MountainCreate, db: Session = Depends(get_db)):
    mountain = Mountain(**payload.model_dump())
    db.add(mountain)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mountain with this name already exists")
    db.refresh(mountain)
    return mountain


@app.get("/api/mountains/{mountain_id}", response_model=MountainRead)
def get_mountain(mountain_id: int, db: Session = Depends(get_db)):
    mountain = db.get(Mountain, mountain_id)
    if not mountain:
        raise HTTPException(status_code=404, detail="Mountain not found")
    return mountain


@app.get("/api/climbers", response_model=list[ClimberRead])
def list_climbers(db: Session = Depends(get_db)):
    return db.query(Climber).all()


@app.post("/api/climbers", response_model=ClimberRead, status_code=201)
def create_climber(payload: ClimberCreate, db: Session = Depends(get_db)):
    if payload.experience_level not in ALLOWED_EXPERIENCE_LEVELS:
        raise HTTPException(status_code=422, detail="Invalid experience_level")
    if payload.birth_date > date.today():
        raise HTTPException(status_code=422, detail="birth_date cannot be in the future")

    climber = Climber(**payload.model_dump())
    db.add(climber)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Climber with this email already exists")
    db.refresh(climber)
    return climber


@app.get("/api/climbers/{climber_id}", response_model=ClimberRead)
def get_climber(climber_id: int, db: Session = Depends(get_db)):
    climber = db.get(Climber, climber_id)
    if not climber:
        raise HTTPException(status_code=404, detail="Climber not found")
    return climber


@app.get("/api/groups", response_model=list[GroupRead])
def list_groups(db: Session = Depends(get_db)):
    return db.query(Group).all()


@app.post("/api/groups", response_model=GroupRead, status_code=201)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    group = Group(**payload.model_dump())
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Group with this name already exists")
    db.refresh(group)
    return group


@app.get("/api/groups/{group_id}", response_model=GroupRead)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@app.post("/api/groups/{group_id}/climbers", response_model=GroupClimberRead, status_code=201)
def add_climber_to_group(
    group_id: int,
    payload: GroupClimberCreate,
    db: Session = Depends(get_db),
):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    climber = db.get(Climber, payload.climber_id)
    if not climber:
        raise HTTPException(status_code=404, detail="Climber not found")

    if payload.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=422, detail="Invalid role")

    existing = (
        db.query(GroupClimber)
        .filter(
            GroupClimber.group_id == group_id,
            GroupClimber.climber_id == payload.climber_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Climber already in group")

    membership = GroupClimber(
        group_id=group_id,
        climber_id=payload.climber_id,
        role=payload.role,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@app.get("/api/groups/{group_id}/climbers", response_model=list[GroupClimberRead])
def list_group_climbers(group_id: int, db: Session = Depends(get_db)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return db.query(GroupClimber).filter(GroupClimber.group_id == group_id).all()


@app.get("/api/ascents", response_model=list[AscentRead])
def list_ascents(db: Session = Depends(get_db)):
    return db.query(Ascent).all()


@app.post("/api/ascents", response_model=AscentRead, status_code=201)
def create_ascent(payload: AscentCreate, db: Session = Depends(get_db)):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="end_date cannot be earlier than start_date")

    if not db.get(Mountain, payload.mountain_id):
        raise HTTPException(status_code=404, detail="Mountain not found")
    if not db.get(Group, payload.group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    ascent = Ascent(**payload.model_dump(), status="planned")
    db.add(ascent)
    db.commit()
    db.refresh(ascent)
    return ascent


@app.get("/api/ascents/{ascent_id}", response_model=AscentRead)
def get_ascent(ascent_id: int, db: Session = Depends(get_db)):
    ascent = db.get(Ascent, ascent_id)
    if not ascent:
        raise HTTPException(status_code=404, detail="Ascent not found")
    return ascent


@app.post("/api/ascents/{ascent_id}/complete", response_model=AscentRead)
def complete_ascent(ascent_id: int, db: Session = Depends(get_db)):
    # ИСПРАВЛЕНИЕ N+1: Подгружаем группу и участников одним запросом
    ascent = (
        db.query(Ascent)
        .options(joinedload(Ascent.group).joinedload(Group.memberships))
        .filter(Ascent.id == ascent_id)
        .first()
    )
    if not ascent:
        raise HTTPException(status_code=404, detail="Ascent not found")

    if ascent.status == "completed":
        return ascent
    if ascent.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cannot complete cancelled ascent")
    if len(ascent.group.memberships) == 0:
        raise HTTPException(status_code=409, detail="Cannot complete ascent without group participants")

    ascent.status = "completed"
    db.commit()
    db.refresh(ascent)
    return ascent


@app.post("/api/ascents/{ascent_id}/cancel", response_model=AscentRead)
def cancel_ascent(ascent_id: int, db: Session = Depends(get_db)):
    ascent = db.get(Ascent, ascent_id)
    if not ascent:
        raise HTTPException(status_code=404, detail="Ascent not found")
    if ascent.status == "completed":
        raise HTTPException(status_code=409, detail="Cannot cancel completed ascent")
    if ascent.status == "cancelled":
        return ascent

    ascent.status = "cancelled"
    db.commit()
    db.refresh(ascent)
    return ascent


@app.get("/api/reports", response_model=list[ReportRead])
def list_reports(db: Session = Depends(get_db)):
    return db.query(Report).all()


@app.post("/api/reports", response_model=ReportRead, status_code=201)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)):
    if payload.report_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid report_type")

    ascent = db.get(Ascent, payload.ascent_id)
    if not ascent:
        raise HTTPException(status_code=404, detail="Ascent not found")
    if ascent.status != "completed":
        raise HTTPException(status_code=409, detail="Report can be created only for completed ascent")

    report = Report(**payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@app.get("/api/reports/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/ascents/{ascent_id}/reports", response_model=list[ReportRead])
def list_ascent_reports(ascent_id: int, db: Session = Depends(get_db)):
    if not db.get(Ascent, ascent_id):
        raise HTTPException(status_code=404, detail="Ascent not found")
    return db.query(Report).filter(Report.ascent_id == ascent_id).all()
