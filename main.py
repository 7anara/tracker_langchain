from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from mysite.api.auth import auth_router
from mysite.database.db import Base, engine, get_db

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Importing the auth router registers UserProfile with the shared Base.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Personal Assistant Agent", lifespan=lifespan)
app.include_router(auth_router)


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
