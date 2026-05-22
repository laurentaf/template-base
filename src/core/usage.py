from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Global DB connection (pointing to our Docker Postgres)
DB_URL = "postgresql+psycopg://prefect:password@localhost:5433/prefect"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class TokenUsage(Base):
    __tablename__ = "token_meter"
    id = Column(Integer, primary_key=True)
    project_name = Column(String)
    model_name = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_estimate = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


def log_usage(project: str, model: str, input_tokens: int, output_tokens: int):
    """
    Logs model usage to the global Postgres ledger.
    Estimates cost based on common NIM/OpenRouter rates.
    """
    # Simple estimation logic ($0.01 per 1k tokens for high-end models)
    cost = ((input_tokens + output_tokens) / 1000) * 0.01

    session = Session()
    new_entry = TokenUsage(
        project_name=project,
        model_name=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost,
    )
    session.add(new_entry)
    session.commit()
    session.close()
    print(f"💰 Usage Logged: {input_tokens + output_tokens} tokens for {model}")


if __name__ == "__main__":
    # Test logging
    log_usage("template-test", "glm-5.1", 100, 50)
