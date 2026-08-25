from fastapi import APIRouter
from app.services.analytics_service import get_dashboard_summary

router = APIRouter()


@router.get("/analytics")
def dashboard_analytics():
    return get_dashboard_summary()