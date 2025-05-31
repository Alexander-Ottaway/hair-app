from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import requests

#MODELE DANYCH (Pydantic)
class ServiceOut(BaseModel):
    id: int
    name: str

class BookingIn(BaseModel):
    time: str
    client_name: str
    service_id: int

class BookingOut(BaseModel):
    id: int
    time: str
    client_name: str
    service: ServiceOut

#KONFIGURACJA BAZY DANYCH (SQLite)
engine = create_engine(
    "sqlite:///booking.db",
    connect_args={"check_same_thread": False}
)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class ServiceModel(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

class BookingModel(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    time = Column(String)
    client_name = Column(String)
    service_id = Column(Integer, ForeignKey("services.id"))
    service = relationship("ServiceModel")

# Tworzymy tabele jeżeli nie istnieją
Base.metadata.create_all(engine)

# wypełniamy tabele services, jeśli jest pusta
def seed_services():
    db = SessionLocal()
    if db.query(ServiceModel).count() == 0:
        for name in [
            "hair coloring",
            "hair bleaching",
            "men's cut",
            "woman's cut"
        ]:
            db.add(ServiceModel(name=name))
        db.commit()
    db.close()

seed_services()

# FastAPI & CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#ADRES ENDPOINTU WALIDACJI (Auth Service)
AUTH_VALIDATE_URL = "http://localhost:8001/validate"

def get_user_id(authorization: str):
    # Weryfikowanie JWT, zwracamy user_id lub blad
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak tokena")
    resp = requests.get(
        AUTH_VALIDATE_URL,
        headers={"Authorization": authorization}
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Nieautoryzowany")
    return resp.json()["user_id"]

# ENDPOINT: lista usług
@app.get("/services", response_model=list[ServiceOut])
def list_services():
    db = SessionLocal()
    services = db.query(ServiceModel).all()
    db.close()
    return [ServiceOut(id=s.id, name=s.name) for s in services]

#ENDPOINT: lista rezerwacji użytkownika
@app.get("/bookings", response_model=list[BookingOut])
def list_bookings(authorization: str = Header(None)):
    user_id = get_user_id(authorization)
    db = SessionLocal()
    rows = db.query(BookingModel).filter_by(user_id=user_id).all()
    result = []
    for r in rows:
        result.append(
            BookingOut(
                id=r.id,
                time=r.time,
                client_name=r.client_name,
                service=ServiceOut(id=r.service.id, name=r.service.name)
            )
        )
    db.close()
    return result

# ENDPOINT: tworzenie rezerwacji
@app.post("/bookings", response_model=BookingOut)
def create_booking(
    booking: BookingIn,
    authorization: str = Header(None)
):
    user_id = get_user_id(authorization)
    db = SessionLocal()

    # zapobieganie podwojnemu bookowaniu
    if db.query(BookingModel).filter_by(time=booking.time).first():
        db.close()
        raise HTTPException(status_code=400, detail="Slot już zajęty")

    b = BookingModel(
        user_id=user_id,
        time=booking.time,
        client_name=booking.client_name,
        service_id=booking.service_id
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    # to pobiera pelne info o usludze na podstawie jego ID
    service = db.get(ServiceModel, b.service_id)

    out = BookingOut(
        id=b.id,
        time=b.time,
        client_name=b.client_name,
        service=ServiceOut(id=service.id, name=service.name)
    )
    db.close()
    return out
