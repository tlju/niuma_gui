from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("用户名不能为空")
        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', v):
            raise ValueError("用户名只能包含字母、数字、下划线和中文")
        return v


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', v):
            raise ValueError("用户名只能包含字母、数字、下划线和中文")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', v):
            raise ValueError("邮箱格式不正确")
        return v


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    status: Optional[int] = Field(None, ge=0, le=2)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', v):
            raise ValueError("邮箱格式不正确")
        return v


class AssetCreateRequest(BaseModel):
    unit_name: str = Field(..., min_length=1, max_length=100, description="单位名称")
    system_name: str = Field(..., min_length=1, max_length=100, description="系统名称")
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")
    ip: Optional[str] = Field(None, max_length=45, description="IP地址")
    ipv6: Optional[str] = Field(None, max_length=45, description="IPv6地址")
    port: Optional[int] = Field(None, ge=1, le=65535, description="端口")
    host_name: Optional[str] = Field(None, max_length=100, description="主机名")
    notes: Optional[str] = Field(None, description="备注")
    business_service: Optional[str] = Field(None, max_length=200, description="业务服务")
    location: Optional[str] = Field(None, max_length=100, description="位置")
    server_type: Optional[str] = Field(None, max_length=100, description="服务器类型")
    vip: Optional[str] = Field(None, max_length=200, description="VIP")

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v:
            ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ipv4_pattern, v):
                raise ValueError("IPv4地址格式不正确")
            parts = v.split('.')
            for part in parts:
                if int(part) > 255:
                    raise ValueError("IPv4地址格式不正确")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 65535):
            raise ValueError("端口范围应在1-65535之间")
        return v


class AssetUpdateRequest(BaseModel):
    unit_name: Optional[str] = Field(None, min_length=1, max_length=100)
    system_name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1, max_length=128)
    ip: Optional[str] = Field(None, max_length=45)
    ipv6: Optional[str] = Field(None, max_length=45)
    port: Optional[int] = Field(None, ge=1, le=65535)
    host_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    business_service: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=100)
    server_type: Optional[str] = Field(None, max_length=100)
    vip: Optional[str] = Field(None, max_length=200)


class DictCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="字典名称")
    code: str = Field(..., min_length=1, max_length=50, description="字典编码")
    description: Optional[str] = Field(None, description="描述")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("字典编码只能包含字母、数字和下划线")
        return v


class ParamCreateRequest(BaseModel):
    param_name: str = Field(..., min_length=1, max_length=100, description="参数名称")
    param_code: str = Field(..., min_length=1, max_length=50, description="参数编码")
    param_value: str = Field(..., min_length=1, description="参数值")
    description: Optional[str] = Field(None, description="描述")

    @field_validator("param_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("参数编码只能包含字母、数字和下划线")
        return v


class TodoCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    description: Optional[str] = Field(None, description="描述")
    priority: Optional[str] = Field("medium", description="优先级")
    recurrence: Optional[str] = Field("none", description="重复类型")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ("low", "medium", "high"):
            raise ValueError("优先级必须是 low/medium/high")
        return v

    @field_validator("recurrence")
    @classmethod
    def validate_recurrence(cls, v: str) -> str:
        if v not in ("none", "daily", "weekly", "monthly"):
            raise ValueError("重复类型必须是 none/daily/weekly/monthly")
        return v
