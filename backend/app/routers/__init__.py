"""业务路由汇总：借阅凭据等专用路由先注册，其余模块共用一套资源路由。"""
from __future__ import annotations

from app.routers import borrow, resource

ROUTERS = [borrow, resource]
