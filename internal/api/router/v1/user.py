import datetime
from typing import Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_

from internal.middleware.jwt import encode_token
from internal.middleware.mysql import session
from internal.middleware.mysql.models import ApiKeySchema, UserSchema

from ...auth import jwt_auth
from ..base import StandardResponse

user_router = APIRouter(prefix="/user", tags=["user"])


class UserRequest(BaseModel):
    user: str
    password: str


@user_router.post("/register", response_model=StandardResponse)
def register_user(request: UserRequest) -> StandardResponse:
    with session() as conn:
        query = conn.query(UserSchema.user).filter(UserSchema.user == request.user)
        exist_user = query.first()

    if exist_user:
        return StandardResponse(code=1, status="error", message="User already exist")

    with session() as conn:
        if not conn.is_active:
            conn.rollback()
            conn.close()

        user = UserSchema(user=request.user, password=request.password)
        conn.add(user)
        conn.commit()

    return StandardResponse(code=0, status="success", message="Register successfully")


@user_router.post("/login", response_model=StandardResponse)
def login_user(request: UserRequest) -> StandardResponse:
    with session() as conn:
        if not conn.is_active:
            conn.rollback()
            conn.close()

        query = (
            conn.query(UserSchema.uid, UserSchema.is_admin).filter(UserSchema.user == request.user).filter(UserSchema.password == request.password)
        )
        result = query.first()

    if not result:
        return StandardResponse(code=1, status="error", message="User not exist or password incorrect")

    (uid, is_admin) = result

    data = {"uid": uid, "token": encode_token(uid=uid, level=is_admin)}

    return StandardResponse(code=0, status="success", message="Login successfully", data=data)


@user_router.get("/{uid}/key/list", response_model=StandardResponse, dependencies=[Depends(jwt_auth)])
def get_api_key_list(uid: int, info: Tuple[int, int] = Depends(jwt_auth)) -> StandardResponse:
    _uid, level = info
    if not (level or _uid == uid):
        return StandardResponse(code=1, status="error", message="No permission")
    with session() as conn:
        if not conn.is_active:
            conn.rollback()
            conn.close()

        query = (
            conn.query(ApiKeySchema.api_key_secret, ApiKeySchema.create_at, ApiKeySchema.delete_at)
            .filter(or_(ApiKeySchema.uid == uid, level == 1))
            .filter(or_(ApiKeySchema.delete_at.is_(None), ApiKeySchema.delete_at > datetime.datetime.now()))
        )
        result = query.all()

    fields = ("api_key_id", "api_key_secret", "create_at", "expire_at")
    data = {"uid": uid, "api_key_list": [dict(zip(fields, row)) for row in result]}

    return StandardResponse(code=0, status="success", message="List api key successfully", data=data)


@user_router.post("/{uid}/key/generate", response_model=StandardResponse, dependencies=[Depends(jwt_auth)])
def generate_api_key(uid: int, info: Tuple[int, int] = Depends(jwt_auth)) -> StandardResponse:
    _uid, _ = info
    if _uid != uid:
        return StandardResponse(code=1, status="error", message="No permission")
    with session() as conn:
        if not conn.is_active:
            conn.rollback()
            conn.close()

        query = conn.query(UserSchema.ak_num).filter(UserSchema.uid == uid)
        result = query.first()

    if not result:
        return StandardResponse(code=1, status="error", message="Token invalid")

    (ak_num,) = result

    if ak_num >= 5:
        return StandardResponse(code=1, status="error", message="You can only generate 5 api keys at most")

    with session() as conn:
        if not conn.is_active:
            conn.rollback()
            conn.close()

        api_key = ApiKeySchema(uid=uid)
        conn.add(api_key)
        conn.query(UserSchema).filter(UserSchema.uid == uid).filter(
            or_(UserSchema.delete_at.is_(None), datetime.datetime.now() < UserSchema.delete_at)
        ).update({"ak_num": UserSchema.ak_num + 1})
        conn.commit()
        data = {
            "uid": uid,
            "create_at": api_key.create_at,
            "expire_at": api_key.delete_at,
            "api_key_secret": api_key.api_key_secret,
        }

    return StandardResponse(
        code=0,
        status="success",
        message="Generate api key successfully. Please save it carefully.",
        data=data,
    )


@user_router.delete("/{uid}/key/delete", response_model=StandardResponse, dependencies=[Depends(jwt_auth)])
def delete_api_key(uid: int, info: Tuple[int, int] = Depends(jwt_auth), api_key_secret: str = "") -> StandardResponse:
    _uid, level = info
    if not (level or _uid == uid):
        return StandardResponse(code=1, status="error", message="No permission")

    with session() as conn:
        if not conn.is_active:
            conn.rollback()
            conn.close()

        query = (
            conn.query(ApiKeySchema.api_key_secret).filter(ApiKeySchema.api_key_secret == api_key_secret).filter(or_(ApiKeySchema.uid == uid, level))
        )
        result = query.first()

    if not result:
        return StandardResponse(code=1, status="error", message="Key not exist")

    with session() as conn:
        if not conn.is_active:
            conn.rollback()

        conn.query(ApiKeySchema).filter(ApiKeySchema.api_key_secret == api_key_secret).update({ApiKeySchema.delete_at: datetime.datetime.now()})
        conn.query(UserSchema).filter(UserSchema.uid == uid).filter(
            or_(UserSchema.delete_at.is_(None), datetime.datetime.now() < UserSchema.delete_at)
        ).update({UserSchema.ak_num: UserSchema.ak_num - 1})
        conn.commit()

    return StandardResponse(code=0, status="success", message="Delete api key successfully")
