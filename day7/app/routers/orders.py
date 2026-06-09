
"""
routers/orders.py — Order Endpoints
=====================================
Full CRUD + status-patch + summary extension.
"""

from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import OrderRepository, get_repository
from app.models import Order, OrderCreate, OrderResponse, OrderStatus

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── CREATE ──────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
)
def create_order(
    payload: OrderCreate,
    repo: OrderRepository = Depends(get_repository),
) -> OrderResponse:
    """
    Accepts a deeply nested `OrderCreate` body:
    - **customer** → name, email, phone, shipping_address (nested)
    - **items[]**  → each item embeds a full **product** object
    - **payment_method** enum
    - **notes** (optional)

    Returns an `OrderResponse` which *extends* the stored order with a
    computed **summary** block (subtotal, discounts, grand total, item count).
    """
    order = Order(**payload.model_dump())
    saved = repo.save(order)
    return OrderResponse.from_order(saved)


# ── READ ALL ────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[OrderResponse],
    summary="List all orders",
)
def list_orders(
    status_filter: Optional[OrderStatus] = Query(
        default=None,
        alias="status",
        description="Filter orders by status (e.g. pending, shipped)",
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of orders to skip",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Max number of orders to return (1–100)",
    ),
    sort_by: Literal["created_at", "grand_total"] = Query(
        default="created_at",
        description="Sort field: 'created_at' or 'grand_total'",
    ),
    repo: OrderRepository = Depends(get_repository),
) -> List[OrderResponse]:
    """
    Returns a paginated, sorted list of orders.

    - **status** — optional filter by `OrderStatus`
    - **skip / limit** — pagination controls
    - **sort_by** — `created_at` (default) or `grand_total`, descending
    """
    orders = repo.list_all()

    # ── Task 1: filter by status ──
    if status_filter is not None:
        orders = [o for o in orders if o.status == status_filter]

    # ── Convert to response objects ──
    responses = [OrderResponse.from_order(o) for o in orders]

    # ── Task 2: sort (descending) ──
    if sort_by == "grand_total":
        responses.sort(key=lambda r: r.summary.grand_total, reverse=True)
    else:  # "created_at"
        responses.sort(key=lambda r: r.created_at, reverse=True)

    # ── Task 2: paginate ──
    return responses[skip : skip + limit]


# ── READ ONE ────────────────────────────────────────────────────────────────

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get a single order by ID",
)
def get_order(
    order_id: UUID,
    repo: OrderRepository = Depends(get_repository),
) -> OrderResponse:
    order = repo.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found.",
        )
    return OrderResponse.from_order(order)


# ── UPDATE STATUS (PATCH) ────────────────────────────────────────────────────

@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
)
def update_order_status(
    order_id: UUID,
    new_status: OrderStatus,
    repo: OrderRepository = Depends(get_repository),
) -> OrderResponse:
    """
    Extension task: PATCH only the `status` field.
    Demonstrates partial update without re-validating the whole body.
    """
    order = repo.update_status(order_id, new_status)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found.",
        )
    return OrderResponse.from_order(order)


# ── DELETE ──────────────────────────────────────────────────────────────────

@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel / delete an order",
)
def delete_order(
    order_id: UUID,
    repo: OrderRepository = Depends(get_repository),
) -> None:
    if not repo.delete(order_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found.",
        )

