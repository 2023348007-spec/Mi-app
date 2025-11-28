from datetime import datetime, timedelta
from typing import List
import os
import shutil
from jose import jwt
from jose.exceptions import JWTError
from fastapi import FastAPI, UploadFile, Form, File, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from pydantic import BaseModel

app = FastAPI()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "mysql+pymysql://root:@127.0.0.1/fotografias_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

SECRET_KEY = "tu_clave_secreta_muy_segura_aqui_cambiar_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security = HTTPBearer()
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(TIMESTAMP, default=datetime.utcnow)

class Foto(Base):
    __tablename__ = "P10_foto"
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(255), nullable=False)
    ruta_foto = Column(String(255), nullable=False)
    fecha = Column(TIMESTAMP, default=datetime.utcnow)
    usuario_id = Column(Integer, default=1)

Base.metadata.create_all(bind=engine)

class UsuarioBase(BaseModel):
    email: str
    nombre: str

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    fecha_creacion: datetime
    class Config:
        from_attributes = True

class UsuarioLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class FotoBase(BaseModel):
    descripcion: str

class FotoCreate(FotoBase):
    pass

class FotoResponse(FotoBase):
    id: int
    ruta_foto: str
    fecha: datetime
    class Config:
        from_attributes = True

def verificar_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def crear_token_acceso(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_usuario_actual(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    db = SessionLocal()
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    db.close()
    if usuario is None:
        raise credentials_exception
    return usuario

@app.post("/registro", response_model=Token)
async def registrar_usuario(usuario: UsuarioCreate):
    db = SessionLocal()
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    usuario_db = Usuario(
        email=usuario.email,
        password_hash=get_password_hash(usuario.password),
        nombre=usuario.nombre
    )
    db.add(usuario_db)
    db.commit()
    db.refresh(usuario_db)
    db.close()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_token_acceso(
        data={"sub": usuario.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
async def login(usuario: UsuarioLogin):
    db = SessionLocal()
    usuario_db = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    db.close()
    if not usuario_db or not verificar_password(usuario.password, usuario_db.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_token_acceso(
        data={"sub": usuario_db.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/fotos/", response_model=dict)
async def subir_foto(
    descripcion: str = Form(...),
    file: UploadFile = File(...),
    usuario_actual: Usuario = Depends(get_usuario_actual)
):
    db = SessionLocal()
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
        os.makedirs("uploads", exist_ok=True)
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"foto_{timestamp}_{usuario_actual.id}.{file_extension}"
        ruta = f"uploads/{unique_filename}"
        with open(ruta, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        nueva_foto = Foto(
            descripcion=descripcion, 
            ruta_foto=ruta,
            usuario_id=usuario_actual.id
        )
        db.add(nueva_foto)
        db.commit()
        db.refresh(nueva_foto)
        return {
            "msg": "Foto subida correctamente",
            "foto": {
                "id": nueva_foto.id,
                "descripcion": nueva_foto.descripcion,
                "ruta_foto": nueva_foto.ruta_foto,
                "fecha": nueva_foto.fecha.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error al subir foto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al subir la foto: {str(e)}")
    finally:
        db.close()

@app.get("/fotos/", response_model=List[FotoResponse])
def listar_fotos(usuario_actual: Usuario = Depends(get_usuario_actual)):
    try:
        db = SessionLocal()
        fotos = db.query(Foto).all()
        db.close()
        return fotos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "API de Fotografías funcionando"}

@app.get("/crear-usuario-prueba")
def crear_usuario_prueba():
    db = SessionLocal()
    usuario_existente = db.query(Usuario).filter(Usuario.email == "test@test.com").first()
    if usuario_existente:
        db.close()
        return {"message": "Usuario de prueba ya existe", "email": "test@test.com", "password": "123456"}
    usuario_prueba = Usuario(
        email="test@test.com",
        password_hash=get_password_hash("123456"),
        nombre="Usuario Prueba"
    )
    db.add(usuario_prueba)
    db.commit()
    db.close()
    return {
        "message": "Usuario de prueba creado", 
        "email": "test@test.com", 
        "password": "123456",
        "instrucciones": "Usa estas credenciales para hacer login"
    }

@app.get("/debug-fotos")
def debug_fotos():
    db = SessionLocal()
    try:
        fotos_count = db.query(Foto).count()
        usuarios_count = db.query(Usuario).count()
        return {
            "database_connection": "OK",
            "total_fotos": fotos_count,
            "total_usuarios": usuarios_count,
            "tablas_creadas": True
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)