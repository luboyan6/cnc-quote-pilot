"""CNC 业务域：CRUD 资源、产品路由与平台适配器。

两层结构：
- ``cnc_*`` 子包：标准 CRUD 资源（model / schema / crud / service / controller），
  由 ``app/api/v1/routers.py`` 以 ``/cnc`` 前缀注册。
- ``batch`` / ``quote`` / ``login`` / ``monitor`` / ``browser`` / ``recovery`` / ``mcp``：
  跨资源的领域服务与平台适配层。
"""
