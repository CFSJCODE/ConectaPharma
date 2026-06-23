"""
ConectaPharma API v3.0 - Enterprise Edition
Refatoração Arquitetural: Monolito Modular (Clean Architecture)
"""

import asyncio
import heapq
import logging
import math
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials as firebase_credentials
except ImportError:  # Firebase Admin é opcional para execução puramente mockada.
    firebase_admin = None
    firebase_auth = None
    firebase_credentials = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

# =============================================================================
# 0. CONFIGURAÇÕES GERAIS E OBSERVABILIDADE
# =============================================================================

# Setup de Logging Estruturado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ConectaPharma")

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "sim", "on"}

class Settings:
    PROJECT_NAME: str = "ConectaPharma API"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv(
        "CONNECTAPHARMA_SECRET_KEY",
        "dev-only-change-this-secret-with-32-plus-bytes",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5501",
        "null",
    ]
    RNDS_ENABLED: bool = env_bool("CONNECTAPHARMA_RNDS_ENABLED", False)
    RNDS_ENVIRONMENT: str = os.getenv("CONNECTAPHARMA_RNDS_ENVIRONMENT", "homologacao")
    RNDS_AUTH_URL: str = os.getenv("CONNECTAPHARMA_RNDS_AUTH_URL", "https://ehr-auth-hmg.saude.gov.br/api")
    RNDS_SERVICES_URL: str = os.getenv("CONNECTAPHARMA_RNDS_SERVICES_URL", "https://ehr-services.hmg.saude.gov.br/api")
    RNDS_DOCUMENT_ENDPOINT: str = os.getenv("CONNECTAPHARMA_RNDS_DOCUMENT_ENDPOINT", "/fhir/r4/Bundle")
    RNDS_CLIENT_CERT_PATH: Optional[str] = os.getenv("CONNECTAPHARMA_RNDS_CLIENT_CERT_PATH")
    RNDS_CLIENT_KEY_PATH: Optional[str] = os.getenv("CONNECTAPHARMA_RNDS_CLIENT_KEY_PATH")
    RNDS_VERIFY_TLS: bool = env_bool("CONNECTAPHARMA_RNDS_VERIFY_TLS", True)
    RNDS_TIMEOUT_SECONDS: float = float(os.getenv("CONNECTAPHARMA_RNDS_TIMEOUT_SECONDS", "15"))
    ESTABELECIMENTO_CNES: Optional[str] = os.getenv("CONNECTAPHARMA_ESTABELECIMENTO_CNES")
    FIREBASE_PROJECT_ID: str = os.getenv(
        "CONNECTAPHARMA_FIREBASE_PROJECT_ID",
        os.getenv("VITE_FIREBASE_PROJECT_ID", "conectapharma-33fd7"),
    )
    FIREBASE_CREDENTIALS_PATH: Optional[str] = os.getenv(
        "CONNECTAPHARMA_FIREBASE_CREDENTIALS_PATH",
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    )
    FIREBASE_VERIFY_REVOKED: bool = env_bool("CONNECTAPHARMA_FIREBASE_VERIFY_REVOKED", False)
    ALLOW_LEGACY_JWT: bool = env_bool("CONNECTAPHARMA_ALLOW_LEGACY_JWT", False)
    APP_TIMEZONE: str = os.getenv("CONNECTAPHARMA_TIMEZONE", "America/Sao_Paulo")
    OVERPASS_ENABLED: bool = env_bool("CONNECTAPHARMA_OVERPASS_ENABLED", True)
    OVERPASS_URL: str = os.getenv("CONNECTAPHARMA_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    OVERPASS_TIMEOUT_SECONDS: float = float(os.getenv("CONNECTAPHARMA_OVERPASS_TIMEOUT_SECONDS", "12"))
    OVERPASS_CACHE_TTL_SECONDS: int = int(os.getenv("CONNECTAPHARMA_OVERPASS_CACHE_TTL_SECONDS", "900"))
    OVERPASS_RESPONSE_CACHE_TTL_SECONDS: int = int(os.getenv("CONNECTAPHARMA_OVERPASS_RESPONSE_CACHE_TTL_SECONDS", "60"))
    OVERPASS_MAX_CONNECTIONS: int = int(os.getenv("CONNECTAPHARMA_OVERPASS_MAX_CONNECTIONS", "8"))
    OVERPASS_MAX_KEEPALIVE_CONNECTIONS: int = int(os.getenv("CONNECTAPHARMA_OVERPASS_MAX_KEEPALIVE_CONNECTIONS", "4"))
    OVERPASS_USER_AGENT: str = os.getenv(
        "CONNECTAPHARMA_OVERPASS_USER_AGENT",
        "ConectaPharma-MVP/1.0 (academic prototype; contact: claudiofranciscojunior2006@gmail.com)",
    )

settings = Settings()

# =============================================================================
# 1. DOMÍNIO & SCHEMAS (Pydantic Models)
# =============================================================================

class RiscoEnum(str, Enum):
    CRITICO = "CRITICO"
    ATENCAO = "ATENCAO"
    OK = "OK"

class DeliveryStatus(str, Enum):
    PENDENTE = "PENDENTE"
    EM_TRANSITO = "EM_TRANSITO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"

# --- Request/Response Models ---

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class UserResponse(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class MedicamentoAlerta(BaseModel):
    id: int
    medicamento_id: int
    nome: str
    dias_restantes: int
    status: RiscoEnum
    recomendacao: str

class FarmaciaMapa(BaseModel):
    id: int
    nome: str
    distancia_km: float
    disponibilidade_farmaco: bool
    horario_funcionamento: str
    endereco: str
    avaliacao: float

class FarmaciaProximaItem(BaseModel):
    id: str
    name: str
    source: str
    address: str
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: float
    is_open: Optional[bool] = None
    status_label: str
    opening_hours_label: str
    maps_url: str

class FarmaciasProximasResponse(BaseModel):
    origin: Dict[str, float]
    count: int
    source: str
    radius_km: float
    open_now: bool
    generated_at: datetime
    items: List[FarmaciaProximaItem]



class MedicamentoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    categoria: Optional[str] = Field(None, max_length=80)
    descricao: Optional[str] = Field(None, max_length=240)
    dose_diaria_comprimidos: float = Field(1.0, gt=0, le=20)
    stock: int = Field(0, ge=0, le=100000)
    requires_prescription: bool = True

class MedicamentoCatalogoItem(BaseModel):
    id: int
    nome: str
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    dose_diaria_comprimidos: float
    stock: int
    requires_prescription: bool = True

class FarmaciaDiretorioItem(BaseModel):
    id: int
    nome: str
    endereco: str
    telefone: Optional[str] = None
    whatsapp: Optional[str] = None
    horario_funcionamento: str
    disponibilidade_farmaco: bool
    avaliacao: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    maps_url: Optional[str] = None

class EstabelecimentoSaudeItem(BaseModel):
    id: str
    name: str
    kind: str
    address: str
    phone: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: float
    is_open: Optional[bool] = None
    status_label: str
    opening_hours_label: str
    maps_url: str

class EstabelecimentosSaudeResponse(BaseModel):
    origin: Dict[str, float]
    count: int
    source: str
    radius_km: float
    open_now: bool
    generated_at: datetime
    items: List[EstabelecimentoSaudeItem]

class ConsumoSimulacaoRequest(BaseModel):
    medicamento_id: int
    dose_diaria_comprimidos: float = Field(..., gt=0)
    estoque_atual: int = Field(..., ge=0)

class EntregaStatus(BaseModel):
    tracking_id: str
    paciente_id: str
    status: DeliveryStatus
    voluntario: Optional[str] = None
    entrega_prevista_min: int
    ultimo_update: datetime

class SolicitacaoEntrega(BaseModel):
    medicamento_id: int
    endereco: str
    urgencia: bool = False

class RndsIntegrationStatus(BaseModel):
    enabled: bool
    configured: bool
    environment: str
    mode: str
    auth_url: str
    services_url: str
    document_endpoint: str
    missing_settings: List[str]
    notes: List[str]

class RndsDispensacaoRequest(BaseModel):
    cidadao_cns: str = Field(..., min_length=6)
    paciente_nome: str = Field(..., min_length=2)
    medicamento_nome: str = Field(..., min_length=2)
    medicamento_codigo: Optional[str] = None
    quantidade: int = Field(..., gt=0)
    unidade: str = Field("unidade", min_length=1)
    estabelecimento_cnes: Optional[str] = None
    profissional_cns: Optional[str] = None
    data_dispensacao: Optional[datetime] = None
    observacao: Optional[str] = None

class RndsSubmissionResponse(BaseModel):
    mode: str
    sent: bool
    destination: str
    message: str
    protocol: Optional[str] = None
    request_preview: Dict[str, Any]

# =============================================================================
# 2. CAMADA DE DADOS (Mock Repositories)
# =============================================================================
# Em uma aplicação real, estes seriam adaptadores do SQLAlchemy.

class MockDatabase:
    def __init__(self) -> None:
        self.users: List[Dict] = []
        self.medicamentos = [
            {
                "id": 1,
                "nome": "Losartana 50mg",
                "categoria": "Anti-hipertensivo",
                "descricao": "Medicamento de uso contínuo utilizado em protocolos de controle pressórico.",
                "dose_diaria_comprimidos": 1.0,
                "stock": 3,
                "requires_prescription": True,
            },
            {
                "id": 2,
                "nome": "Metformina 850mg",
                "categoria": "Antidiabético",
                "descricao": "Medicamento de uso contínuo associado ao controle glicêmico.",
                "dose_diaria_comprimidos": 2.0,
                "stock": 22,
                "requires_prescription": True,
            },
            {
                "id": 3,
                "nome": "Dipirona 500mg",
                "categoria": "Analgésico",
                "descricao": "Medicamento sintomático registrado apenas como item operacional do MVP.",
                "dose_diaria_comprimidos": 1.0,
                "stock": 14,
                "requires_prescription": False,
            },
        ]
        self.next_medicamento_id = 4
        self.farmacias = [
            {
                "id": 1,
                "nome": "Farmácia Central BH",
                "distancia_km": 1.2,
                "disponibilidade_farmaco": True,
                "horario_funcionamento": "08:00 - 22:00",
                "endereco": "Av. Afonso Pena, 1000 - Centro, Belo Horizonte - MG",
                "avaliacao": 4.8,
                "telefone": "(31) 3333-0000",
                "whatsapp": "5531999990000",
                "latitude": -19.9191,
                "longitude": -43.9386,
                "opening_hours": {
                    "monday": [{"open": "08:00", "close": "22:00"}],
                    "tuesday": [{"open": "08:00", "close": "22:00"}],
                    "wednesday": [{"open": "08:00", "close": "22:00"}],
                    "thursday": [{"open": "08:00", "close": "22:00"}],
                    "friday": [{"open": "08:00", "close": "22:00"}],
                    "saturday": [{"open": "08:00", "close": "18:00"}],
                    "sunday": [{"open": "08:00", "close": "12:00"}],
                },
                "inv": {1: 6, 2: 22, 3: 8},
            },
            {
                "id": 2,
                "nome": "Drogaria Plantão 24h",
                "distancia_km": 3.5,
                "disponibilidade_farmaco": True,
                "horario_funcionamento": "24 Horas",
                "endereco": "Região Centro-Sul, Belo Horizonte - MG",
                "avaliacao": 4.6,
                "telefone": "(31) 3333-1111",
                "whatsapp": "5531999991111",
                "latitude": -19.9320,
                "longitude": -43.9378,
                "opening_hours": {
                    "monday": [{"open": "00:00", "close": "23:59"}],
                    "tuesday": [{"open": "00:00", "close": "23:59"}],
                    "wednesday": [{"open": "00:00", "close": "23:59"}],
                    "thursday": [{"open": "00:00", "close": "23:59"}],
                    "friday": [{"open": "00:00", "close": "23:59"}],
                    "saturday": [{"open": "00:00", "close": "23:59"}],
                    "sunday": [{"open": "00:00", "close": "23:59"}],
                },
                "inv": {1: 10, 2: 18, 3: 12},
            },
            {
                "id": 3,
                "nome": "Unidade Popular Norte",
                "distancia_km": 4.1,
                "disponibilidade_farmaco": True,
                "horario_funcionamento": "08:00 - 17:00",
                "endereco": "Rua Comunitária, 45 - Zona Norte, Belo Horizonte - MG",
                "avaliacao": 4.6,
                "telefone": "(31) 3333-2222",
                "whatsapp": "5531999992222",
                "latitude": -19.8369,
                "longitude": -43.9676,
                "opening_hours": {
                    "monday": [{"open": "08:00", "close": "17:00"}],
                    "tuesday": [{"open": "08:00", "close": "17:00"}],
                    "wednesday": [{"open": "08:00", "close": "17:00"}],
                    "thursday": [{"open": "08:00", "close": "17:00"}],
                    "friday": [{"open": "08:00", "close": "17:00"}],
                    "saturday": [],
                    "sunday": [],
                },
                "inv": {1: 4, 2: 0, 3: 20},
            },
        ]
        self.estabelecimentos_saude = [
            {
                "id": "mock-health-1",
                "name": "Unidade Básica de Saúde Centro-Sul",
                "kind": "HEALTH_CENTER",
                "address": "Região Centro-Sul, Belo Horizonte - MG",
                "phone": "(31) 3277-0000",
                "latitude": -19.9287,
                "longitude": -43.9408,
                "opening_hours": {
                    "monday": [{"open": "07:00", "close": "17:00"}],
                    "tuesday": [{"open": "07:00", "close": "17:00"}],
                    "wednesday": [{"open": "07:00", "close": "17:00"}],
                    "thursday": [{"open": "07:00", "close": "17:00"}],
                    "friday": [{"open": "07:00", "close": "17:00"}],
                    "saturday": [],
                    "sunday": [],
                },
            },
            {
                "id": "mock-health-2",
                "name": "Hospital Metropolitano 24h",
                "kind": "HOSPITAL",
                "address": "Belo Horizonte - MG",
                "phone": "(31) 3277-1111",
                "latitude": -19.9227,
                "longitude": -43.9451,
                "opening_hours": {
                    "monday": [{"open": "00:00", "close": "23:59"}],
                    "tuesday": [{"open": "00:00", "close": "23:59"}],
                    "wednesday": [{"open": "00:00", "close": "23:59"}],
                    "thursday": [{"open": "00:00", "close": "23:59"}],
                    "friday": [{"open": "00:00", "close": "23:59"}],
                    "saturday": [{"open": "00:00", "close": "23:59"}],
                    "sunday": [{"open": "00:00", "close": "23:59"}],
                },
            },
        ]
        self.entregas: Dict[str, Dict] = {}
        self.voluntarios = [{"id": 1, "nome": "Ana Oliveira"}, {"id": 2, "nome": "Carlos Mendes"}]

db = MockDatabase()

# =============================================================================
# 3. CAMADA DE SEGURANÇA (Security Utils)
# =============================================================================

# Contexto do Passlib para hashing seguro usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityHelper:
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Gera um hash seguro da senha usando bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha em texto plano corresponde ao hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
        """Gera um token JWT assinado usando a biblioteca PyJWT."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_jwt_token(token: str) -> Optional[dict]:
        """Decodifica e verifica a assinatura do token JWT usando PyJWT."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Tentativa de acesso com token expirado.")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Tentativa de acesso com token inválido.")
            return None

security = HTTPBearer(auto_error=True)

class FirebaseAuthAdapter:
    """Adaptador mínimo para validar Firebase ID Token no FastAPI.

    O frontend envia `Authorization: Bearer <Firebase ID Token>`.
    O backend valida a assinatura pelo Firebase Admin SDK e converte o token
    em um usuário compatível com os schemas atuais do MVP.
    """

    _initialized = False

    @classmethod
    def initialize(cls) -> bool:
        if cls._initialized:
            return True

        if firebase_admin is None or firebase_auth is None:
            logger.error(
                "firebase-admin não está instalado. Instale com: pip install firebase-admin"
            )
            return False

        if firebase_admin._apps:
            cls._initialized = True
            return True

        try:
            options = {"projectId": settings.FIREBASE_PROJECT_ID}
            if settings.FIREBASE_CREDENTIALS_PATH:
                cred = firebase_credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred, options)
            else:
                # Usa Application Default Credentials quando GOOGLE_APPLICATION_CREDENTIALS
                # ou o ambiente Google Cloud já estiver configurado.
                cred = firebase_credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, options)

            cls._initialized = True
            logger.info(
                "Firebase Admin inicializado para o projeto %s.",
                settings.FIREBASE_PROJECT_ID,
            )
            return True
        except Exception:
            logger.exception("Falha ao inicializar Firebase Admin SDK.")
            return False

    @classmethod
    def verify_token(cls, id_token: str) -> Dict:
        if not cls.initialize():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Firebase Admin SDK não está configurado no backend. "
                    "Defina CONNECTAPHARMA_FIREBASE_CREDENTIALS_PATH ou "
                    "GOOGLE_APPLICATION_CREDENTIALS com um service account válido."
                ),
            )

        try:
            decoded = firebase_auth.verify_id_token(
                id_token,
                check_revoked=settings.FIREBASE_VERIFY_REVOKED,
            )
        except Exception as exc:
            logger.warning("Firebase ID Token inválido: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase ID Token inválido, expirado ou revogado.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        uid = decoded.get("uid") or decoded.get("sub")
        email = decoded.get("email") or "usuario.firebase@conectapharma.local"
        name = decoded.get("name") or decoded.get("displayName") or email
        issued_at = decoded.get("auth_time") or decoded.get("iat")
        created_at = datetime.fromtimestamp(issued_at, timezone.utc) if issued_at else datetime.now(timezone.utc)

        return {
            "id": str(uid),
            "uid": str(uid),
            "email": email,
            "name": name,
            "photo_url": decoded.get("picture"),
            "provider": "firebase",
            "created_at": created_at,
            "firebase_claims": decoded,
        }


def get_legacy_current_user(token: str) -> Dict:
    payload = SecurityHelper.decode_jwt_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token legado inválido, expirado ou assinatura incorreta.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = next((u for u in db.users if str(u["id"]) == str(user_id)), None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado no banco de dados legado.",
        )
    return user


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials

    try:
        return FirebaseAuthAdapter.verify_token(token)
    except HTTPException as firebase_exc:
        if settings.ALLOW_LEGACY_JWT:
            try:
                return get_legacy_current_user(token)
            except HTTPException:
                raise firebase_exc
        raise firebase_exc

def seed_default_user() -> None:
    """Cria um usuário de desenvolvimento para testes manuais."""
    default_email = "admin@conectapharma.com"
    if any(u["email"] == default_email for u in db.users):
        return

    db.users.append({
        "id": "1",
        "email": default_email,
        "name": "Administrador ConectaPharma",
        "password_hash": SecurityHelper.get_password_hash("admin123"),
        "created_at": datetime.now(timezone.utc),
    })

# =============================================================================
# 4. CAMADA DE SERVIÇOS (Business Logic / Domain)
# =============================================================================

class HealthService:
    @staticmethod
    def avaliar_risco(dias_restantes: int) -> tuple[RiscoEnum, str]:
        if dias_restantes <= 3:
            return RiscoEnum.CRITICO, "Reposição URGENTE. Acione rede solidária."
        if dias_restantes <= 10:
            return RiscoEnum.ATENCAO, "Planeje reposição em até 5 dias."
        return RiscoEnum.OK, "Estoque em níveis seguros."

    @staticmethod
    def montar_alerta(medicamento: Dict) -> MedicamentoAlerta:
        dias = int(medicamento["stock"] / medicamento["dose_diaria_comprimidos"])
        risco, recomendacao = HealthService.avaliar_risco(dias)
        return MedicamentoAlerta(
            id=medicamento["id"],
            medicamento_id=medicamento["id"],
            nome=medicamento["nome"],
            dias_restantes=dias,
            status=risco,
            recomendacao=recomendacao,
        )

class LogisticsService:
    @staticmethod
    def calcular_eta(distancia_km: float, urgencia: bool) -> int:
        base_min = max(15, int(distancia_km * 10))
        return int(base_min * 0.6) if urgencia else base_min

    @staticmethod
    def alocar_voluntario() -> Dict:
        return secrets.choice(db.voluntarios)

WEEK_DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

OSM_DAY_TOKENS = {
    "Mo": 0,
    "Tu": 1,
    "We": 2,
    "Th": 3,
    "Fr": 4,
    "Sa": 5,
    "Su": 6,
}


def get_app_now() -> datetime:
    """Retorna o horário operacional do backend no fuso configurado.

    A decisão de abertura/fechamento deve ocorrer no backend para manter o
    frontend como camada de apresentação e evitar divergência entre clientes.
    """
    try:
        return datetime.now(ZoneInfo(settings.APP_TIMEZONE))
    except ZoneInfoNotFoundError:
        logger.warning(
            "Timezone %s não encontrado. Usando horário local do servidor.",
            settings.APP_TIMEZONE,
        )
        return datetime.now()


class GeoDistanceService:
    @staticmethod
    def haversine_km(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> float:
        """Calcula distância geodésica aproximada entre dois pontos.

        A fórmula de Haversine é determinística, gratuita e suficiente para o
        MVP urbano, em que a distância em linha reta é usada apenas para ordenar
        farmácias antes de eventual abertura de rota externa pelo navegador.
        """
        earth_radius_km = 6371.0
        delta_lat = math.radians(dest_lat - origin_lat)
        delta_lng = math.radians(dest_lng - origin_lng)
        lat1 = math.radians(origin_lat)
        lat2 = math.radians(dest_lat)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
        )
        return 2 * earth_radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class OpeningHoursService:
    _time_range_re = re.compile(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}|24:00)")
    _day_expr_re = re.compile(r"\b(Mo|Tu|We|Th|Fr|Sa|Su)(?:\s*-\s*(Mo|Tu|We|Th|Fr|Sa|Su))?\b")

    @staticmethod
    def _time_to_minutes(value: str) -> int:
        if value == "24:00":
            return 24 * 60
        hours, minutes = value.split(":")
        return int(hours) * 60 + int(minutes)

    @staticmethod
    def _period_matches_now(open_time: str, close_time: str, current_minutes: int) -> bool:
        open_minutes = OpeningHoursService._time_to_minutes(open_time)
        close_minutes = OpeningHoursService._time_to_minutes(close_time)

        if close_minutes == 24 * 60:
            close_minutes = 23 * 60 + 59

        if open_minutes <= close_minutes:
            return open_minutes <= current_minutes <= close_minutes
        return current_minutes >= open_minutes or current_minutes <= close_minutes

    @staticmethod
    def is_structured_open_now(opening_hours: Optional[Dict[str, List[Dict[str, str]]]], now: datetime) -> Optional[bool]:
        if not opening_hours:
            return None

        day_key = WEEK_DAYS[now.weekday()]
        periods = opening_hours.get(day_key, [])
        if not periods:
            return False

        current_minutes = now.hour * 60 + now.minute
        return any(
            OpeningHoursService._period_matches_now(period.get("open", ""), period.get("close", ""), current_minutes)
            for period in periods
            if period.get("open") and period.get("close")
        )

    @staticmethod
    def _parse_days(day_expression: str) -> set[int]:
        matches = OpeningHoursService._day_expr_re.findall(day_expression)
        if not matches:
            return set(range(7))

        days: set[int] = set()
        for start, end in matches:
            start_idx = OSM_DAY_TOKENS[start]
            if not end:
                days.add(start_idx)
                continue

            end_idx = OSM_DAY_TOKENS[end]
            if start_idx <= end_idx:
                days.update(range(start_idx, end_idx + 1))
            else:
                days.update(range(start_idx, 7))
                days.update(range(0, end_idx + 1))
        return days

    @staticmethod
    def parse_osm_opening_hours(opening_hours: Optional[str], now: datetime) -> Optional[bool]:
        """Interpreta subconjunto seguro do padrão OSM `opening_hours`.

        O formato OSM completo é extenso. Para o MVP, cobrimos os casos mais
        comuns em farmácias: `24/7`, faixas por dia (`Mo-Fr 08:00-18:00`) e
        múltiplas regras separadas por ponto e vírgula. Expressões não
        reconhecidas retornam `None`, preservando honestidade operacional.
        """
        if not opening_hours:
            return None

        expression = opening_hours.strip()
        if not expression:
            return None
        if expression == "24/7":
            return True

        current_day = now.weekday()
        current_minutes = now.hour * 60 + now.minute
        matched_rule = False

        for raw_rule in expression.split(";"):
            rule = raw_rule.strip()
            if not rule:
                continue

            days = OpeningHoursService._parse_days(rule)
            if current_day not in days:
                continue

            matched_rule = True
            if re.search(r"\boff\b", rule, flags=re.IGNORECASE):
                return False

            time_ranges = OpeningHoursService._time_range_re.findall(rule)
            if not time_ranges:
                continue

            if any(
                OpeningHoursService._period_matches_now(open_time, close_time, current_minutes)
                for open_time, close_time in time_ranges
            ):
                return True

        if matched_rule:
            return False
        return None

    @staticmethod
    def is_open_now(record: Dict[str, Any], now: datetime) -> Optional[bool]:
        structured = OpeningHoursService.is_structured_open_now(record.get("opening_hours"), now)
        if structured is not None:
            return structured
        return OpeningHoursService.parse_osm_opening_hours(record.get("osm_opening_hours"), now)

    @staticmethod
    def label(record: Dict[str, Any], now: datetime) -> str:
        osm_label = record.get("osm_opening_hours")
        if osm_label:
            return osm_label

        opening_hours = record.get("opening_hours")
        if not opening_hours:
            return "Horário não informado"

        day_key = WEEK_DAYS[now.weekday()]
        periods = opening_hours.get(day_key, [])
        if not periods:
            return "Fechada hoje"

        return " / ".join(
            f"{period.get('open', '--:--')} - {period.get('close', '--:--')}"
            for period in periods
        )


class OverpassPharmacyService:
    """Consulta gratuita ao OpenStreetMap/Overpass com cache e client HTTP reutilizável.

    O frontend não consulta serviços externos. Ele envia coordenadas ao backend;
    o backend consulta/cacheia dados OSM, calcula distância, avalia abertura,
    ordena e retorna JSON pronto para renderização.
    """

    _cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
    _response_cache: Dict[str, tuple[float, FarmaciasProximasResponse]] = {}
    _locks: Dict[str, asyncio.Lock] = {}
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Reutiliza conexões HTTP para reduzir latência nas chamadas Overpass."""
        if cls._client is None or cls._client.is_closed:
            timeout = httpx.Timeout(
                settings.OVERPASS_TIMEOUT_SECONDS,
                connect=min(5.0, settings.OVERPASS_TIMEOUT_SECONDS),
            )
            limits = httpx.Limits(
                max_connections=settings.OVERPASS_MAX_CONNECTIONS,
                max_keepalive_connections=settings.OVERPASS_MAX_KEEPALIVE_CONNECTIONS,
                keepalive_expiry=30.0,
            )
            cls._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers={"User-Agent": settings.OVERPASS_USER_AGENT},
            )
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
        cls._client = None

    @classmethod
    def clear_expired_caches(cls) -> None:
        """Remove entradas expiradas para evitar crescimento indefinido em dev/demo."""
        now_monotonic = time.monotonic()
        cls._cache = {
            key: value
            for key, value in cls._cache.items()
            if now_monotonic - value[0] <= settings.OVERPASS_CACHE_TTL_SECONDS
        }
        cls._response_cache = {
            key: value
            for key, value in cls._response_cache.items()
            if now_monotonic - value[0] <= settings.OVERPASS_RESPONSE_CACHE_TTL_SECONDS
        }

    @staticmethod
    def _cache_key(lat: float, lng: float, radius_km: float) -> str:
        # Arredondamento reduz cardinalidade do cache sem alterar a UX do MVP.
        return f"{round(lat, 3)}:{round(lng, 3)}:{round(radius_km, 1)}"

    @staticmethod
    def _response_cache_key(lat: float, lng: float, radius_km: float, open_now: bool, limit: int, source: str) -> str:
        return f"{round(lat, 3)}:{round(lng, 3)}:{round(radius_km, 1)}:{int(open_now)}:{limit}:{source}"

    @staticmethod
    def _build_overpass_query(lat: float, lng: float, radius_km: float) -> str:
        radius_m = int(radius_km * 1000)
        return f"""
[out:json][timeout:25];
(
  node["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
  way["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
  relation["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
  node["healthcare"="pharmacy"](around:{radius_m},{lat},{lng});
  way["healthcare"="pharmacy"](around:{radius_m},{lat},{lng});
  relation["healthcare"="pharmacy"](around:{radius_m},{lat},{lng});
);
out center tags;
""".strip()

    @staticmethod
    def _address_from_tags(tags: Dict[str, str]) -> str:
        street = tags.get("addr:street") or tags.get("addr:place")
        number = tags.get("addr:housenumber")
        suburb = tags.get("addr:suburb") or tags.get("addr:neighbourhood")
        city = tags.get("addr:city")
        state = tags.get("addr:state")

        address_parts = []
        if street:
            address_parts.append(f"{street}, {number}" if number else street)
        if suburb:
            address_parts.append(suburb)
        if city:
            address_parts.append(city)
        if state:
            address_parts.append(state)

        return " - ".join(address_parts) if address_parts else "Endereço não informado no OpenStreetMap"

    @staticmethod
    def _phone_from_tags(tags: Dict[str, str]) -> Optional[str]:
        return tags.get("phone") or tags.get("contact:phone") or tags.get("mobile") or tags.get("contact:mobile")

    @staticmethod
    def _whatsapp_from_tags(tags: Dict[str, str]) -> Optional[str]:
        whatsapp = tags.get("contact:whatsapp") or tags.get("whatsapp")
        if whatsapp:
            return re.sub(r"\D+", "", whatsapp)
        phone = OverpassPharmacyService._phone_from_tags(tags)
        if phone:
            digits = re.sub(r"\D+", "", phone)
            return digits if digits.startswith("55") else None
        return None

    @staticmethod
    def _record_from_element(element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tags = element.get("tags", {}) or {}
        center = element.get("center") or {}
        lat = element.get("lat", center.get("lat"))
        lng = element.get("lon", center.get("lon"))

        if lat is None or lng is None:
            return None

        name = tags.get("name") or tags.get("brand") or "Farmácia cadastrada no OpenStreetMap"

        return {
            "id": f"osm-{element.get('type', 'node')}-{element.get('id')}",
            "name": name,
            "source": "openstreetmap",
            "address": OverpassPharmacyService._address_from_tags(tags),
            "phone": OverpassPharmacyService._phone_from_tags(tags),
            "whatsapp": OverpassPharmacyService._whatsapp_from_tags(tags),
            "latitude": float(lat),
            "longitude": float(lng),
            "osm_opening_hours": tags.get("opening_hours"),
        }

    @classmethod
    async def fetch_from_overpass(cls, lat: float, lng: float, radius_km: float) -> List[Dict[str, Any]]:
        if not settings.OVERPASS_ENABLED:
            return []

        cls.clear_expired_caches()
        cache_key = cls._cache_key(lat, lng, radius_km)
        cached = cls._cache.get(cache_key)
        now_monotonic = time.monotonic()
        if cached and now_monotonic - cached[0] <= settings.OVERPASS_CACHE_TTL_SECONDS:
            return cached[1]

        lock = cls._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = cls._cache.get(cache_key)
            now_monotonic = time.monotonic()
            if cached and now_monotonic - cached[0] <= settings.OVERPASS_CACHE_TTL_SECONDS:
                return cached[1]

            query = cls._build_overpass_query(lat, lng, radius_km)
            response = await cls.get_client().post(settings.OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            payload = response.json()

            records = []
            seen: set[str] = set()
            for element in payload.get("elements", []):
                record = cls._record_from_element(element)
                if not record or record["id"] in seen:
                    continue
                seen.add(record["id"])
                records.append(record)

            cls._cache[cache_key] = (now_monotonic, records)
            return records

    @staticmethod
    def fallback_records() -> List[Dict[str, Any]]:
        return [
            {
                "id": f"mock-{farmacia['id']}",
                "name": farmacia["nome"],
                "source": "local_mock",
                "address": farmacia.get("endereco", "Endereço não informado"),
                "phone": farmacia.get("telefone"),
                "whatsapp": farmacia.get("whatsapp"),
                "latitude": float(farmacia["latitude"]),
                "longitude": float(farmacia["longitude"]),
                "opening_hours": farmacia.get("opening_hours"),
            }
            for farmacia in db.farmacias
            if farmacia.get("latitude") is not None and farmacia.get("longitude") is not None
        ]

    @classmethod
    async def search_nearby(
        cls,
        lat: float,
        lng: float,
        radius_km: float,
        open_now: bool,
        limit: int,
        source: str = "overpass",
    ) -> FarmaciasProximasResponse:
        cls.clear_expired_caches()
        response_cache_key = cls._response_cache_key(lat, lng, radius_km, open_now, limit, source)
        cached_response = cls._response_cache.get(response_cache_key)
        now_monotonic = time.monotonic()
        if cached_response and now_monotonic - cached_response[0] <= settings.OVERPASS_RESPONSE_CACHE_TTL_SECONDS:
            return cached_response[1]

        generated_at = datetime.now(timezone.utc)
        now = get_app_now()
        records: List[Dict[str, Any]] = []
        used_source = source

        if source == "mock":
            records = cls.fallback_records()
            used_source = "local_mock"
        else:
            try:
                records = await cls.fetch_from_overpass(lat, lng, radius_km)
                used_source = "openstreetmap"
            except Exception as exc:
                logger.warning("Falha ao consultar Overpass API; usando fallback local: %s", exc)
                records = cls.fallback_records()
                used_source = "local_mock_fallback"

        items: List[FarmaciaProximaItem] = []
        for record in records:
            distance_km = GeoDistanceService.haversine_km(
                lat,
                lng,
                float(record["latitude"]),
                float(record["longitude"]),
            )
            if distance_km > radius_km:
                continue

            open_state = OpeningHoursService.is_open_now(record, now)
            if open_now and open_state is not True:
                continue

            if open_state is True:
                status_label = "Aberta agora"
            elif open_state is False:
                status_label = "Fechada agora"
            else:
                status_label = "Horário não informado"

            items.append(
                FarmaciaProximaItem(
                    id=str(record["id"]),
                    name=record.get("name") or "Farmácia sem nome",
                    address=record.get("address"),
                    phone=record.get("phone"),
                    whatsapp=record.get("whatsapp"),
                    latitude=float(record["latitude"]),
                    longitude=float(record["longitude"]),
                    distance_km=round(distance_km, 2),
                    is_open=open_state,
                    status_label=status_label,
                    opening_hours_label=OpeningHoursService.label(record, now),
                    source=record.get("source", used_source),
                    maps_url=f"https://www.google.com/maps/search/?api=1&query={record['latitude']},{record['longitude']}",
                )
            )

        limited_items = heapq.nsmallest(limit, items, key=lambda item: item.distance_km)
        response = FarmaciasProximasResponse(
            origin={"latitude": lat, "longitude": lng},
            count=len(limited_items),
            source=used_source,
            radius_km=radius_km,
            open_now=open_now,
            generated_at=generated_at,
            items=limited_items,
        )
        cls._response_cache[response_cache_key] = (now_monotonic, response)
        return response


class HealthEstablishmentService:
    """Busca gratuita de estabelecimentos de saúde via OpenStreetMap/Overpass.

    Todo o processamento permanece no backend: consulta externa, cache,
    normalização, cálculo de distância, avaliação de horário, filtro e ordenação.
    """

    _cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
    _response_cache: Dict[str, tuple[float, EstabelecimentosSaudeResponse]] = {}
    _locks: Dict[str, asyncio.Lock] = {}

    KIND_LABELS = {
        "pharmacy": "Farmácia",
        "hospital": "Hospital",
        "clinic": "Clínica",
        "doctors": "Consultório médico",
        "dentist": "Odontologia",
        "health_center": "Centro de saúde",
        "laboratory": "Laboratório",
        "unknown": "Estabelecimento de saúde",
    }

    @staticmethod
    def _cache_key(lat: float, lng: float, radius_km: float, kind: str) -> str:
        return f"{round(lat, 3)}:{round(lng, 3)}:{round(radius_km, 1)}:{kind}"

    @staticmethod
    def _response_cache_key(lat: float, lng: float, radius_km: float, open_now: bool, limit: int, kind: str, source: str) -> str:
        return f"{round(lat, 3)}:{round(lng, 3)}:{round(radius_km, 1)}:{int(open_now)}:{limit}:{kind}:{source}"

    @staticmethod
    def _build_query(lat: float, lng: float, radius_km: float, kind: str) -> str:
        radius_m = int(radius_km * 1000)
        kind_filters = {
            "all": [
                '["amenity"="pharmacy"]', '["amenity"="hospital"]', '["amenity"="clinic"]', '["amenity"="doctors"]', '["amenity"="dentist"]',
                '["healthcare"="pharmacy"]', '["healthcare"="hospital"]', '["healthcare"="clinic"]', '["healthcare"="doctor"]', '["healthcare"="laboratory"]',
            ],
            "pharmacy": ['["amenity"="pharmacy"]', '["healthcare"="pharmacy"]'],
            "hospital": ['["amenity"="hospital"]', '["healthcare"="hospital"]'],
            "clinic": ['["amenity"="clinic"]', '["healthcare"="clinic"]'],
            "doctors": ['["amenity"="doctors"]', '["healthcare"="doctor"]'],
        }
        filters = kind_filters.get(kind, kind_filters["all"])
        lines = []
        for selector in filters:
            lines.append(f"node{selector}(around:{radius_m},{lat},{lng});")
            lines.append(f"way{selector}(around:{radius_m},{lat},{lng});")
            lines.append(f"relation{selector}(around:{radius_m},{lat},{lng});")
        return "\n".join(["[out:json][timeout:25];", "(", *lines, ");", "out center tags;"])

    @staticmethod
    def _kind_from_tags(tags: Dict[str, str]) -> str:
        amenity = tags.get("amenity")
        healthcare = tags.get("healthcare")
        raw = amenity or healthcare or "unknown"
        if raw == "doctor":
            return "doctors"
        return raw

    @classmethod
    def _record_from_element(cls, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tags = element.get("tags", {}) or {}
        center = element.get("center") or {}
        lat = element.get("lat", center.get("lat"))
        lng = element.get("lon", center.get("lon"))
        if lat is None or lng is None:
            return None
        kind = cls._kind_from_tags(tags)
        return {
            "id": f"osm-health-{element.get('type', 'node')}-{element.get('id')}",
            "name": tags.get("name") or tags.get("brand") or cls.KIND_LABELS.get(kind, "Estabelecimento de saúde"),
            "kind": kind,
            "source": "openstreetmap",
            "address": OverpassPharmacyService._address_from_tags(tags),
            "phone": OverpassPharmacyService._phone_from_tags(tags),
            "latitude": float(lat),
            "longitude": float(lng),
            "osm_opening_hours": tags.get("opening_hours"),
        }

    @classmethod
    def fallback_records(cls) -> List[Dict[str, Any]]:
        records = []
        for farmacia in db.farmacias:
            if farmacia.get("latitude") is None or farmacia.get("longitude") is None:
                continue
            records.append({
                "id": f"mock-pharmacy-{farmacia['id']}",
                "name": farmacia["nome"],
                "kind": "pharmacy",
                "source": "local_mock",
                "address": farmacia.get("endereco", "Endereço não informado"),
                "phone": farmacia.get("telefone"),
                "latitude": float(farmacia["latitude"]),
                "longitude": float(farmacia["longitude"]),
                "opening_hours": farmacia.get("opening_hours"),
            })
        records.extend(db.estabelecimentos_saude)
        return records

    @classmethod
    async def fetch_from_overpass(cls, lat: float, lng: float, radius_km: float, kind: str) -> List[Dict[str, Any]]:
        if not settings.OVERPASS_ENABLED:
            return []
        now_monotonic = time.monotonic()
        cache_key = cls._cache_key(lat, lng, radius_km, kind)
        cached = cls._cache.get(cache_key)
        if cached and now_monotonic - cached[0] <= settings.OVERPASS_CACHE_TTL_SECONDS:
            return cached[1]
        lock = cls._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = cls._cache.get(cache_key)
            now_monotonic = time.monotonic()
            if cached and now_monotonic - cached[0] <= settings.OVERPASS_CACHE_TTL_SECONDS:
                return cached[1]
            response = await OverpassPharmacyService.get_client().post(
                settings.OVERPASS_URL,
                data={"data": cls._build_query(lat, lng, radius_km, kind)},
            )
            response.raise_for_status()
            payload = response.json()
            records = []
            seen: set[str] = set()
            for element in payload.get("elements", []):
                record = cls._record_from_element(element)
                if not record or record["id"] in seen:
                    continue
                seen.add(record["id"])
                records.append(record)
            cls._cache[cache_key] = (now_monotonic, records)
            return records

    @classmethod
    async def search_nearby(
        cls,
        lat: float,
        lng: float,
        radius_km: float,
        open_now: bool,
        limit: int,
        kind: str = "all",
        source: str = "overpass",
    ) -> EstabelecimentosSaudeResponse:
        response_cache_key = cls._response_cache_key(lat, lng, radius_km, open_now, limit, kind, source)
        now_monotonic = time.monotonic()
        cached = cls._response_cache.get(response_cache_key)
        if cached and now_monotonic - cached[0] <= settings.OVERPASS_RESPONSE_CACHE_TTL_SECONDS:
            return cached[1]

        generated_at = datetime.now(timezone.utc)
        now = get_app_now()
        used_source = source
        if source == "mock":
            records = cls.fallback_records()
            used_source = "local_mock"
        else:
            try:
                records = await cls.fetch_from_overpass(lat, lng, radius_km, kind)
                used_source = "openstreetmap"
            except Exception as exc:
                logger.warning("Falha ao consultar estabelecimentos no Overpass; usando fallback local: %s", exc)
                records = cls.fallback_records()
                used_source = "local_mock_fallback"

        items: List[EstabelecimentoSaudeItem] = []
        for record in records:
            record_kind = record.get("kind", "unknown")
            if kind != "all" and record_kind != kind:
                continue
            distance_km = GeoDistanceService.haversine_km(lat, lng, float(record["latitude"]), float(record["longitude"]))
            if distance_km > radius_km:
                continue
            open_state = OpeningHoursService.is_open_now(record, now)
            if open_now and open_state is not True:
                continue
            status_label = "Aberto agora" if open_state is True else "Fechado agora" if open_state is False else "Horário não informado"
            items.append(EstabelecimentoSaudeItem(
                id=str(record["id"]),
                name=record.get("name") or cls.KIND_LABELS.get(record_kind, "Estabelecimento de saúde"),
                kind=cls.KIND_LABELS.get(record_kind, record_kind),
                address=record.get("address") or "Endereço não informado",
                phone=record.get("phone"),
                latitude=float(record["latitude"]),
                longitude=float(record["longitude"]),
                distance_km=round(distance_km, 2),
                is_open=open_state,
                status_label=status_label,
                opening_hours_label=OpeningHoursService.label(record, now),
                maps_url=f"https://www.google.com/maps/search/?api=1&query={record['latitude']},{record['longitude']}",
            ))

        limited_items = heapq.nsmallest(limit, items, key=lambda item: item.distance_km)
        response = EstabelecimentosSaudeResponse(
            origin={"latitude": lat, "longitude": lng},
            count=len(limited_items),
            source=used_source,
            radius_km=radius_km,
            open_now=open_now,
            generated_at=generated_at,
            items=limited_items,
        )
        cls._response_cache[response_cache_key] = (now_monotonic, response)
        return response

class RndsConfigurationError(Exception):
    pass

class RndsUpstreamError(Exception):
    pass

class RndsIntegrationService:
    @staticmethod
    def missing_settings() -> List[str]:
        required = {
            "CONNECTAPHARMA_RNDS_AUTH_URL": settings.RNDS_AUTH_URL,
            "CONNECTAPHARMA_RNDS_SERVICES_URL": settings.RNDS_SERVICES_URL,
            "CONNECTAPHARMA_RNDS_CLIENT_CERT_PATH": settings.RNDS_CLIENT_CERT_PATH,
        }
        return [name for name, value in required.items() if not value]

    @staticmethod
    def status() -> RndsIntegrationStatus:
        missing = RndsIntegrationService.missing_settings() if settings.RNDS_ENABLED else []
        configured = settings.RNDS_ENABLED and not missing
        notes = [
            "Meu SUS Digital nao expõe uma API publica direta para este prototipo; a rota oficial e via RNDS/Portal de Servicos DATASUS.",
            "O envio real exige credencial aprovada, CNES e certificado digital ICP-Brasil configurado no backend.",
        ]
        if not settings.RNDS_ENABLED:
            notes.append("Integracao em modo dry-run. Configure CONNECTAPHARMA_RNDS_ENABLED=true para ativar chamadas reais.")
        elif missing:
            notes.append("Integracao ativada, mas ainda faltam variaveis obrigatorias.")
        else:
            notes.append("Integracao configurada para chamadas reais ao ambiente informado.")

        return RndsIntegrationStatus(
            enabled=settings.RNDS_ENABLED,
            configured=configured,
            environment=settings.RNDS_ENVIRONMENT,
            mode="real" if configured else "dry-run",
            auth_url=settings.RNDS_AUTH_URL,
            services_url=settings.RNDS_SERVICES_URL,
            document_endpoint=settings.RNDS_DOCUMENT_ENDPOINT,
            missing_settings=missing,
            notes=notes,
        )

    @staticmethod
    def build_fhir_bundle(req: RndsDispensacaoRequest, current_user: Dict) -> Dict[str, Any]:
        now = req.data_dispensacao or datetime.now(timezone.utc)
        issued_at = now.astimezone(timezone.utc).isoformat()
        bundle_id = f"conectapharma-{secrets.token_hex(8)}"
        composition_id = f"composition-{secrets.token_hex(8)}"
        patient_id = f"patient-{secrets.token_hex(8)}"
        medication_id = f"medication-{secrets.token_hex(8)}"
        dispense_id = f"dispense-{secrets.token_hex(8)}"
        cnes = req.estabelecimento_cnes or settings.ESTABELECIMENTO_CNES or "CNES-PENDENTE"

        return {
            "resourceType": "Bundle",
            "id": bundle_id,
            "type": "document",
            "timestamp": issued_at,
            "meta": {
                "source": "ConectaPharma",
                "tag": [
                    {
                        "system": "https://conectapharma.local/integrations",
                        "code": "RNDS-DRAFT",
                        "display": "Rascunho de integracao para homologacao DATASUS/RNDS",
                    }
                ],
            },
            "entry": [
                {
                    "fullUrl": f"urn:uuid:{composition_id}",
                    "resource": {
                        "resourceType": "Composition",
                        "id": composition_id,
                        "status": "final",
                        "type": {
                            "coding": [
                                {
                                    "system": "http://loinc.org",
                                    "code": "60593-1",
                                    "display": "Medication dispensed",
                                }
                            ],
                            "text": "Registro de dispensacao farmaceutica",
                        },
                        "subject": {"reference": f"urn:uuid:{patient_id}"},
                        "date": issued_at,
                        "author": [{"display": current_user["name"]}],
                        "title": "Registro ConectaPharma de dispensacao",
                        "section": [
                            {
                                "title": "Medicamento dispensado",
                                "entry": [{"reference": f"urn:uuid:{dispense_id}"}],
                            }
                        ],
                    },
                },
                {
                    "fullUrl": f"urn:uuid:{patient_id}",
                    "resource": {
                        "resourceType": "Patient",
                        "id": patient_id,
                        "identifier": [
                            {
                                "system": "https://rnds.saude.gov.br/fhir/r4/NamingSystem/cns",
                                "value": req.cidadao_cns,
                            }
                        ],
                        "name": [{"text": req.paciente_nome}],
                    },
                },
                {
                    "fullUrl": f"urn:uuid:{medication_id}",
                    "resource": {
                        "resourceType": "Medication",
                        "id": medication_id,
                        "code": {
                            "text": req.medicamento_nome,
                            "coding": [
                                {
                                    "system": "https://conectapharma.local/codigos/medicamentos",
                                    "code": req.medicamento_codigo or "NAO-INFORMADO",
                                    "display": req.medicamento_nome,
                                }
                            ],
                        },
                    },
                },
                {
                    "fullUrl": f"urn:uuid:{dispense_id}",
                    "resource": {
                        "resourceType": "MedicationDispense",
                        "id": dispense_id,
                        "status": "completed",
                        "subject": {"reference": f"urn:uuid:{patient_id}"},
                        "medicationReference": {"reference": f"urn:uuid:{medication_id}"},
                        "whenHandedOver": issued_at,
                        "quantity": {"value": req.quantidade, "unit": req.unidade},
                        "performer": [
                            {
                                "actor": {
                                    "display": current_user["name"],
                                    "identifier": {"value": req.profissional_cns or current_user["email"]},
                                }
                            }
                        ],
                        "location": {
                            "identifier": {
                                "system": "https://cnes.datasus.gov.br",
                                "value": cnes,
                            }
                        },
                        "note": [{"text": req.observacao}] if req.observacao else [],
                    },
                },
            ],
        }

    @staticmethod
    def build_url(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def cert_config() -> Any:
        if settings.RNDS_CLIENT_CERT_PATH and settings.RNDS_CLIENT_KEY_PATH:
            return (settings.RNDS_CLIENT_CERT_PATH, settings.RNDS_CLIENT_KEY_PATH)
        return settings.RNDS_CLIENT_CERT_PATH

    @staticmethod
    async def authenticate() -> str:
        missing = RndsIntegrationService.missing_settings()
        if missing:
            raise RndsConfigurationError(f"Configuracao RNDS incompleta: {', '.join(missing)}")

        url = RndsIntegrationService.build_url(settings.RNDS_AUTH_URL, "/token")
        try:
            async with httpx.AsyncClient(
                cert=RndsIntegrationService.cert_config(),
                verify=settings.RNDS_VERIFY_TLS,
                timeout=settings.RNDS_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RndsUpstreamError(f"Falha na autenticacao RNDS: {exc}") from exc

        access_token = response.json().get("access_token")
        if not access_token:
            raise RndsUpstreamError("Resposta RNDS sem access_token.")
        return access_token

    @staticmethod
    async def submit_dispensacao(req: RndsDispensacaoRequest, current_user: Dict) -> RndsSubmissionResponse:
        bundle = RndsIntegrationService.build_fhir_bundle(req, current_user)
        destination = RndsIntegrationService.build_url(settings.RNDS_SERVICES_URL, settings.RNDS_DOCUMENT_ENDPOINT)

        if not settings.RNDS_ENABLED:
            return RndsSubmissionResponse(
                mode="dry-run",
                sent=False,
                destination=destination,
                message="Documento montado localmente. Configure credenciais oficiais para envio real a RNDS.",
                request_preview=bundle,
            )

        token = await RndsIntegrationService.authenticate()
        try:
            async with httpx.AsyncClient(
                verify=settings.RNDS_VERIFY_TLS,
                timeout=settings.RNDS_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    destination,
                    json=bundle,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/fhir+json",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RndsUpstreamError(f"Falha no envio RNDS: {exc}") from exc

        protocol = response.headers.get("Location")
        try:
            response_body = response.json()
            protocol = protocol or response_body.get("id")
        except ValueError:
            pass

        return RndsSubmissionResponse(
            mode="real",
            sent=True,
            destination=destination,
            protocol=protocol,
            message="Documento enviado ao endpoint RNDS configurado.",
            request_preview=bundle,
        )

# =============================================================================
# 5. PRESENTATION LAYER (API Routers)
# =============================================================================

router_auth = APIRouter(prefix="/auth", tags=["Autenticação e Usuários"])
router_dashboard = APIRouter(tags=["Dashboard"])
router_farmacias = APIRouter(prefix="/farmacias", tags=["Farmácias"])
router_health = APIRouter(prefix="/saude", tags=["Monitoramento de Saúde"])
router_logistics = APIRouter(prefix="/logistica", tags=["Logística e Entregas"])
router_integrations = APIRouter(prefix="/integracoes", tags=["Integrações Governamentais"])
router_estabelecimentos = APIRouter(prefix="/estabelecimentos-saude", tags=["Estabelecimentos de Saúde"])

@router_auth.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    if any(u["email"] == user_in.email for u in db.users):
        raise HTTPException(status_code=409, detail="Email já cadastrado.")
    
    new_user = {
        "id": str(len(db.users) + 1),
        "email": user_in.email,
        "name": user_in.name,
        "password_hash": SecurityHelper.get_password_hash(user_in.password),
        "created_at": datetime.now(timezone.utc)
    }
    db.users.append(new_user)
    logger.info(f"Novo usuário registrado: {user_in.email}")
    return new_user

@router_auth.post("/login", response_model=Token)
async def login(user_in: UserLogin):
    user = next((u for u in db.users if u["email"] == user_in.email), None)
    
    if not user or not SecurityHelper.verify_password(user_in.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais incorretas.")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = SecurityHelper.create_jwt_token(
        data={"sub": str(user["id"]), "email": user["email"]}, 
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, user=user)

@router_auth.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

@router_dashboard.get("/alertas", response_model=List[MedicamentoAlerta])
async def listar_alertas():
    return [HealthService.montar_alerta(medicamento) for medicamento in db.medicamentos]

@router_farmacias.get("/mapa", response_model=List[FarmaciaMapa])
async def listar_farmacias_mapa():
    return [
        FarmaciaMapa(
            id=farmacia["id"],
            nome=farmacia["nome"],
            distancia_km=farmacia["distancia_km"],
            disponibilidade_farmaco=farmacia["disponibilidade_farmaco"],
            horario_funcionamento=farmacia["horario_funcionamento"],
            endereco=farmacia["endereco"],
            avaliacao=farmacia["avaliacao"],
        )
        for farmacia in db.farmacias
    ]


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    replacements = str.maketrans("áàãâäéèêëíìîïóòõôöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return value.translate(replacements)

@router_farmacias.get("", response_model=List[FarmaciaDiretorioItem])
async def listar_farmacias(
    query_text: Optional[str] = Query(None, alias="q", min_length=1, max_length=120),
    limit: int = Query(30, ge=1, le=100),
):
    """Lista e pesquisa farmácias da base operacional local do MVP."""
    normalized_query = normalize_text(query_text) if query_text else None
    items = []
    for farmacia in db.farmacias:
        searchable = " ".join([
            farmacia.get("nome", ""),
            farmacia.get("endereco", ""),
            farmacia.get("horario_funcionamento", ""),
        ])
        if normalized_query and normalized_query not in normalize_text(searchable):
            continue
        lat = farmacia.get("latitude")
        lng = farmacia.get("longitude")
        items.append(FarmaciaDiretorioItem(
            id=int(farmacia["id"]),
            nome=farmacia["nome"],
            endereco=farmacia.get("endereco", "Endereço não informado"),
            telefone=farmacia.get("telefone"),
            whatsapp=farmacia.get("whatsapp"),
            horario_funcionamento=farmacia.get("horario_funcionamento", "Horário não informado"),
            disponibilidade_farmaco=bool(farmacia.get("disponibilidade_farmaco", False)),
            avaliacao=float(farmacia.get("avaliacao", 0)),
            latitude=lat,
            longitude=lng,
            maps_url=f"https://www.google.com/maps/search/?api=1&query={lat},{lng}" if lat is not None and lng is not None else None,
        ))
    return items[:limit]

@router_health.get("/medicamentos", response_model=List[MedicamentoCatalogoItem])
async def listar_medicamentos(
    query_text: Optional[str] = Query(None, alias="q", min_length=1, max_length=120),
    limit: int = Query(50, ge=1, le=200),
):
    """Lista e pesquisa medicamentos cadastrados no catálogo operacional do MVP."""
    normalized_query = normalize_text(query_text) if query_text else None
    items = []
    for medicamento in db.medicamentos:
        searchable = " ".join([
            medicamento.get("nome", ""),
            medicamento.get("categoria", ""),
            medicamento.get("descricao", ""),
        ])
        if normalized_query and normalized_query not in normalize_text(searchable):
            continue
        items.append(MedicamentoCatalogoItem(
            id=int(medicamento["id"]),
            nome=medicamento["nome"],
            categoria=medicamento.get("categoria"),
            descricao=medicamento.get("descricao"),
            dose_diaria_comprimidos=float(medicamento.get("dose_diaria_comprimidos", 1)),
            stock=int(medicamento.get("stock", 0)),
            requires_prescription=bool(medicamento.get("requires_prescription", True)),
        ))
    return items[:limit]

@router_health.post("/medicamentos", response_model=MedicamentoCatalogoItem, status_code=status.HTTP_201_CREATED)
async def cadastrar_medicamento(req: MedicamentoCreate, current_user: dict = Depends(get_current_user)):
    """Cadastra medicamento no catálogo operacional do MVP.

    Não armazena dados clínicos de pacientes, prescrição, diagnóstico ou CNS/CPF.
    """
    normalized_name = normalize_text(req.nome)
    if any(normalize_text(med.get("nome", "")) == normalized_name for med in db.medicamentos):
        raise HTTPException(status_code=409, detail="Medicamento já cadastrado no catálogo.")
    med = {
        "id": db.next_medicamento_id,
        "nome": req.nome.strip(),
        "categoria": req.categoria.strip() if req.categoria else None,
        "descricao": req.descricao.strip() if req.descricao else None,
        "dose_diaria_comprimidos": float(req.dose_diaria_comprimidos),
        "stock": int(req.stock),
        "requires_prescription": bool(req.requires_prescription),
    }
    db.next_medicamento_id += 1
    db.medicamentos.append(med)
    return MedicamentoCatalogoItem(**med)

@router_estabelecimentos.get("/proximos", response_model=EstabelecimentosSaudeResponse)
async def listar_estabelecimentos_saude_proximos(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=50),
    open_now: bool = Query(False),
    limit: int = Query(10, ge=1, le=50),
    kind: str = Query("all", pattern="^(all|pharmacy|hospital|clinic|doctors)$"),
    source: str = Query("overpass", pattern="^(overpass|mock)$"),
):
    """Localiza estabelecimentos de saúde próximos via backend.

    Suporta OpenStreetMap/Overpass gratuito, fallback local e processamento integral no servidor.
    """
    return await HealthEstablishmentService.search_nearby(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        open_now=open_now,
        limit=limit,
        kind=kind,
        source=source,
    )

@router_farmacias.get("/proximas", response_model=FarmaciasProximasResponse)
async def listar_farmacias_proximas(
    lat: float = Query(..., ge=-90, le=90, description="Latitude da localização autorizada pelo usuário."),
    lng: float = Query(..., ge=-180, le=180, description="Longitude da localização autorizada pelo usuário."),
    radius_km: float = Query(10.0, gt=0, le=50, description="Raio máximo de busca em quilômetros."),
    open_now: bool = Query(True, description="Quando true, retorna apenas farmácias abertas agora."),
    limit: int = Query(10, ge=1, le=50, description="Quantidade máxima de resultados."),
    source: str = Query("overpass", pattern="^(overpass|mock)$", description="Fonte: overpass ou mock para testes locais."),
):
    """Lista farmácias próximas e abertas usando processamento 100% no backend.

    O frontend apenas envia latitude/longitude autorizadas pelo usuário e renderiza
    a resposta. A API consulta OpenStreetMap/Overpass quando `source=overpass`,
    aplica cache em memória, calcula distância, avalia horário de funcionamento
    e ordena por proximidade.
    """
    return await OverpassPharmacyService.search_nearby(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        open_now=open_now,
        limit=limit,
        source=source,
    )

@router_health.post("/consumo/simulacao", response_model=MedicamentoAlerta)
async def simular_consumo(req: ConsumoSimulacaoRequest, current_user: dict = Depends(get_current_user)):
    med = next((m for m in db.medicamentos if m["id"] == req.medicamento_id), None)
    if not med:
        raise HTTPException(status_code=404, detail="Medicamento não mapeado no sistema.")
    
    dias = int(req.estoque_atual / req.dose_diaria_comprimidos)
    risco, recomendacao = HealthService.avaliar_risco(dias)
    
    return MedicamentoAlerta(
        id=med["id"],
        medicamento_id=med["id"],
        nome=med["nome"],
        dias_restantes=dias,
        status=risco,
        recomendacao=recomendacao
    )

@router_logistics.post("/entrega", response_model=EntregaStatus)
async def criar_entrega(req: SolicitacaoEntrega, current_user: dict = Depends(get_current_user)):
    tracking_id = f"CP-{secrets.randbelow(999999):06d}"
    voluntario = LogisticsService.alocar_voluntario()
    eta = LogisticsService.calcular_eta(distancia_km=5.0, urgencia=req.urgencia) # Distância mockada
    
    entrega = {
        "tracking_id": tracking_id,
        "paciente_id": current_user["id"],
        "status": DeliveryStatus.EM_TRANSITO,
        "voluntario": voluntario["nome"],
        "entrega_prevista_min": eta,
        "ultimo_update": datetime.now(timezone.utc)
    }
    db.entregas[tracking_id] = entrega
    logger.info(f"Entrega {tracking_id} criada para o usuário {current_user['id']}.")
    return entrega

@router_logistics.get("/entrega/{tracking_id}", response_model=EntregaStatus)
async def rastrear_entrega(tracking_id: str, current_user: dict = Depends(get_current_user)):
    entrega = db.entregas.get(tracking_id)
    if not entrega:
        raise HTTPException(status_code=404, detail="Tracking ID inválido ou não encontrado.")
    
    # Autorização: Apenas o dono ou admin pode ver.
    if entrega["paciente_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado a esta entrega.")
        
    return entrega

@router_integrations.get("/rnds/status", response_model=RndsIntegrationStatus)
async def rnds_status(current_user: dict = Depends(get_current_user)):
    return RndsIntegrationService.status()

@router_integrations.post("/rnds/dispensacao", response_model=RndsSubmissionResponse)
async def enviar_dispensacao_rnds(req: RndsDispensacaoRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await RndsIntegrationService.submit_dispensacao(req, current_user)
    except RndsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RndsUpstreamError as exc:
        logger.exception("Erro na integracao RNDS")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

# =============================================================================
# 6. APP FACTORY E INICIALIZAÇÃO
# =============================================================================

def create_app() -> FastAPI:
    seed_default_user()

    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Hub de Assistência Farmacêutica. Arquitetura Modular Segura.",
        docs_url="/docs",
        redoc_url=None
    )

    # Compressão reduz latência percebida e payloads JSON/HTML em conexões lentas.
    application.add_middleware(GZipMiddleware, minimum_size=1024)

    # Middleware CORS seguro
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registrar Roteadores
    application.include_router(router_auth, prefix=settings.API_V1_STR)
    application.include_router(router_dashboard, prefix=settings.API_V1_STR)
    application.include_router(router_farmacias, prefix=settings.API_V1_STR)
    application.include_router(router_health, prefix=settings.API_V1_STR)
    application.include_router(router_logistics, prefix=settings.API_V1_STR)
    application.include_router(router_integrations, prefix=settings.API_V1_STR)
    application.include_router(router_estabelecimentos, prefix=settings.API_V1_STR)

    @application.on_event("startup")
    async def startup_resources():
        # Inicialização preguiçosa do client HTTP para aproveitar keep-alive nas chamadas Overpass.
        OverpassPharmacyService.get_client()

    @application.on_event("shutdown")
    async def shutdown_resources():
        await OverpassPharmacyService.close_client()

    @application.get("/healthz", tags=["Infra"])
    async def health_check():
        """Liveness probe para orquestradores (Kubernetes)."""
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    return application

app = create_app()

if __name__ == "__main__":
    import uvicorn
    # Execução em ambiente de desenvolvimento
    uvicorn.run("backend_python:app", host="127.0.0.1", port=8000, reload=True)
