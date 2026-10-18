from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from mysite.database.db import get_db

app = FastAPI(title="AI Personal Assistant Agent")


@app.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Report whether the application can connect to its database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503, detail="Database unavailable"
        ) from exc
    return {"status": "ok"}
