"""
ConectaPharma — Integration Gateway

Módulo complementar para receber eventos autorizados de farmácias parceiras,
ERPs, plataformas de e-commerce e conectores B2B. A responsabilidade deste
arquivo é normalizar payloads externos sem alterar a interface pública da
plataforma.

Uso esperado no FastAPI principal:

    from integration_gateway import router as integration_router
    app.include_router(integration_router)

Em produção, persista os eventos normalizados em Firestore, Pub/Sub, fila ou
banco transacional. Este módulo não armazena segredos em código-fonte.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, HttpUrl, field_validator


router = APIRouter(prefix="/api/v1/integrations", tags=["pharmacy-integrations"])


class AvailabilityStatus(str, Enum):
    """Estados públicos e normalizados de disponibilidade."""

    AVAILABLE = "available"
    LOW_STOCK = "low_stock"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class StockWebhookPayload(BaseModel):
    """Payload canônico recebido de farmácias, ERPs ou marketplaces."""

    eventId: str = Field(..., min_length=8, max_length=160)
    eventType: str = Field(default="stock.updated")
    partnerId: str = Field(..., min_length=2, max_length=80)
    pharmacyId: str = Field(..., min_length=2, max_length=120)
    externalSku: str = Field(..., min_length=1, max_length=120)
    ean: Optional[str] = Field(default=None, max_length=32)
    commercialName: str = Field(..., min_length=2, max_length=180)
    activeIngredient: Optional[str] = Field(default=None, max_length=180)
    concentration: Optional[str] = Field(default=None, max_length=80)
    pharmaceuticalForm: Optional[str] = Field(default=None, max_length=80)
    availabilityStatus: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    quantity: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    price: Optional[float] = Field(default=None, ge=0)
    officialProductUrl: Optional[HttpUrl] = None
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("eventType")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        allowed = {"stock.updated", "stock.created", "stock.deleted", "catalog.updated"}
        if value not in allowed:
            raise ValueError(f"eventType inválido. Use um destes valores: {sorted(allowed)}")
        return value


class NormalizedInventoryItem(BaseModel):
    """Documento equivalente à coleção `pharmacy_inventory` do Firestore."""

    pharmacyId: str
    medicineId: Optional[str] = None
    externalSku: str
    ean: Optional[str] = None
    commercialName: str
    activeIngredient: Optional[str] = None
    concentration: Optional[str] = None
    pharmaceuticalForm: Optional[str] = None
    availabilityStatus: AvailabilityStatus
    quantityInternal: Optional[int] = None
    quantityPublic: AvailabilityStatus
    price: Optional[float] = None
    officialProductUrl: Optional[str] = None
    source: str = "webhook"
    integrationProvider: str
    lastSyncAt: datetime


class WebhookResponse(BaseModel):
    """Resposta mínima e determinística para integradores."""

    status: str
    eventId: str
    payloadHash: str
    normalized: NormalizedInventoryItem


def _get_partner_secret(partner_id: str) -> str:
    """
    Resolve o segredo HMAC do parceiro.

    A convenção permite configurar variáveis por parceiro, por exemplo:
    CONNECTAPHARMA_WEBHOOK_SECRET_RD_MARKETPLACE_DEMO=...

    Para desenvolvimento, CONNECTAPHARMA_WEBHOOK_SECRET funciona como fallback.
    """

    normalized = "".join(char if char.isalnum() else "_" for char in partner_id.upper())
    return os.getenv(f"CONNECTAPHARMA_WEBHOOK_SECRET_{normalized}") or os.getenv("CONNECTAPHARMA_WEBHOOK_SECRET", "")


def _timing_safe_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def _public_status(status_value: AvailabilityStatus, quantity: Optional[int]) -> AvailabilityStatus:
    """Reduz a granularidade operacional para o usuário final."""

    if status_value == AvailabilityStatus.UNAVAILABLE:
        return AvailabilityStatus.UNAVAILABLE
    if quantity is not None and quantity <= 3:
        return AvailabilityStatus.LOW_STOCK
    if status_value == AvailabilityStatus.AVAILABLE:
        return AvailabilityStatus.AVAILABLE
    return AvailabilityStatus.UNKNOWN


def normalize_stock_payload(payload: StockWebhookPayload) -> NormalizedInventoryItem:
    """Normaliza o evento externo para o modelo interno do ConectaPharma."""

    return NormalizedInventoryItem(
        pharmacyId=payload.pharmacyId,
        externalSku=payload.externalSku,
        ean=payload.ean,
        commercialName=payload.commercialName,
        activeIngredient=payload.activeIngredient,
        concentration=payload.concentration,
        pharmaceuticalForm=payload.pharmaceuticalForm,
        availabilityStatus=payload.availabilityStatus,
        quantityInternal=payload.quantity,
        quantityPublic=_public_status(payload.availabilityStatus, payload.quantity),
        price=payload.price,
        officialProductUrl=str(payload.officialProductUrl) if payload.officialProductUrl else None,
        integrationProvider=payload.partnerId,
        lastSyncAt=payload.updatedAt,
    )


async def verify_hmac_request(
    partner_id: str,
    request: Request,
    signature: Optional[str],
    timestamp_header: Optional[str],
) -> bytes:
    """
    Valida assinatura HMAC SHA-256 e rejeita eventos sem segredo configurado.

    O cabeçalho de timestamp reduz replay attacks. O limite padrão é 5 minutos,
    ajustável por CONNECTAPHARMA_WEBHOOK_MAX_SKEW_SECONDS.
    """

    secret = _get_partner_secret(partner_id)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Segredo HMAC do parceiro não configurado.",
        )

    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura ausente.")

    if timestamp_header:
        try:
            event_timestamp = int(timestamp_header)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Timestamp inválido.") from exc

        max_skew = int(os.getenv("CONNECTAPHARMA_WEBHOOK_MAX_SKEW_SECONDS", "300"))
        if abs(int(time.time()) - event_timestamp) > max_skew:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Evento expirado.")

    raw_body = await request.body()
    expected = _timing_safe_signature(raw_body, secret)
    received = signature.removeprefix("sha256=")

    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida.")

    return raw_body


@router.post("/webhooks/{partner_id}/stock", response_model=WebhookResponse)
async def receive_stock_webhook(
    partner_id: str,
    payload: StockWebhookPayload,
    request: Request,
    x_conectapharma_signature: Optional[str] = Header(default=None),
    x_conectapharma_timestamp: Optional[str] = Header(default=None),
) -> WebhookResponse:
    """
    Recebe estoque de farmácia parceira e devolve o objeto normalizado.

    Persistência recomendada:
    - `webhook_events/{eventId}` para idempotência;
    - `pharmacy_inventory/{pharmacyId_externalSku}` para disponibilidade;
    - `integration_logs` para observabilidade.
    """

    if payload.partnerId != partner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="partnerId do path e do payload não correspondem.",
        )

    raw_body = await verify_hmac_request(
        partner_id=partner_id,
        request=request,
        signature=x_conectapharma_signature,
        timestamp_header=x_conectapharma_timestamp,
    )
    normalized = normalize_stock_payload(payload)
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    return WebhookResponse(
        status="processed",
        eventId=payload.eventId,
        payloadHash=payload_hash,
        normalized=normalized,
    )


@router.get("/adapters")
async def list_supported_adapters() -> Dict[str, Any]:
    """Lista adaptadores previstos sem expor credenciais de parceiros."""

    return {
        "adapters": [
            {"provider": "vtex", "mode": "api", "status": "contract_required"},
            {"provider": "nuvemshop", "mode": "api_and_webhooks", "status": "contract_required"},
            {"provider": "rd_marketplace", "mode": "marketplace_or_private_api", "status": "contract_required"},
            {"provider": "dpsp_private", "mode": "private_api_or_integrator", "status": "contract_required"},
            {"provider": "araujo_private", "mode": "private_api_or_csv", "status": "contract_required"},
            {"provider": "csv_manual", "mode": "file_import", "status": "available_for_mvp"},
        ]
    }
