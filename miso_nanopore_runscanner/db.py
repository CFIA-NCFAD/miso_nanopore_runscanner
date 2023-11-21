from sqlmodel import SQLModel, create_engine, Session

from miso_nanopore_runscanner.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, future=True)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session
