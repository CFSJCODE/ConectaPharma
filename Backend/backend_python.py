"""
ConectaPharma API v3.0 - Enterprise Edition
Refatoração Arquitetural: Monolito Modular (Clean Architecture)
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field

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
    id: int
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

class ConsumoSimulacaoRequest(BaseModel):
    medicamento_id: int
    dose_diaria_comprimidos: float = Field(..., gt=0)
    estoque_atual: int = Field(..., ge=0)

class EntregaStatus(BaseModel):
    tracking_id: str
    paciente_id: int
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
            {"id": 1, "nome": "Losartana 50mg", "dose_diaria_comprimidos": 1, "stock": 3},
            {"id": 2, "nome": "Metformina 850mg", "dose_diaria_comprimidos": 2, "stock": 22},
            {"id": 3, "nome": "Dipirona 500mg", "dose_diaria_comprimidos": 1, "stock": 14},
        ]
        self.farmacias = [
            {
                "id": 1,
                "nome": "Farmácia Central",
                "distancia_km": 1.2,
                "disponibilidade_farmaco": True,
                "horario_funcionamento": "07:00 - 19:00",
                "endereco": "Av. Saúde, 120 - Centro",
                "avaliacao": 4.8,
                "inv": {1: 6, 2: 22, 3: 8},
            },
            {
                "id": 2,
                "nome": "Drogaria Sul",
                "distancia_km": 3.5,
                "disponibilidade_farmaco": False,
                "horario_funcionamento": "24 Horas",
                "endereco": "Rua das Flores, 88 - Zona Sul",
                "avaliacao": 4.4,
                "inv": {1: 0, 2: 12, 3: 0},
            },
            {
                "id": 3,
                "nome": "Unidade Popular Norte",
                "distancia_km": 4.1,
                "disponibilidade_farmaco": True,
                "horario_funcionamento": "08:00 - 17:00",
                "endereco": "Rua Comunitária, 45 - Zona Norte",
                "avaliacao": 4.6,
                "inv": {1: 4, 2: 0, 3: 20},
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

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    payload = SecurityHelper.decode_jwt_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido, expirado ou assinatura incorreta.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = payload.get("sub")
    user = next((u for u in db.users if str(u["id"]) == str(user_id)), None)
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado no banco de dados.")
        
    return user

def seed_default_user() -> None:
    """Cria um usuário de desenvolvimento para testes manuais."""
    default_email = "admin@conectapharma.com"
    if any(u["email"] == default_email for u in db.users):
        return

    db.users.append({
        "id": 1,
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

@router_auth.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    if any(u["email"] == user_in.email for u in db.users):
        raise HTTPException(status_code=409, detail="Email já cadastrado.")
    
    new_user = {
        "id": len(db.users) + 1,
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
