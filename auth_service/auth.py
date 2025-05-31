from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr 
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from jose import jwt
import datetime

# MODELE DANYCH (Pydantic)
class UserIn(BaseModel):
    email: EmailStr
    password: str

# KONFIGURACJA BAZY DANYCH (SQLite)
engine = create_engine(
    "sqlite:///auth.db",
    connect_args={"check_same_thread": False}
)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)

Base.metadata.create_all(engine)

#INICJALIZACJA APLIKACJI (FastAPI)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# USTAWIENIA JWT
SECRET = "super-tajne-haslo"
ALGORITHM = "HS256"
EXP_HOURS = 1

# ENDPOINTY REST

@app.post("/register")
def register(user: UserIn):
    
    # minimum 8 znaków do hasła
    if len(user.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Hasło musi mieć przynajmniej 8 znaków"
        )

    db = SessionLocal()
    # unikalny email
    if db.query(UserModel).filter_by(email=user.email).first():
        db.close()
        raise HTTPException(status_code=400, detail="Email zajęty")

    # tworzenie użytkownika
    db_user = UserModel(email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.close()
    return {"message": "Rejestracja OK"}

@app.post("/login")
def login(user: UserIn):

    db = SessionLocal()
    db_user = db.query(UserModel).filter_by(
        email=user.email, password=user.password
    ).first()
    db.close()
    if not db_user:
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane")
    payload = {
        "user_id": db_user.id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=EXP_HOURS)
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    return {"token": token}

@app.get("/validate")
def validate(authorization: str = Header(None)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak tokena")
    token = authorization.split()[1]
    try:
        data = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token nieważny lub wygasł")
    return {"user_id": data["user_id"]}
