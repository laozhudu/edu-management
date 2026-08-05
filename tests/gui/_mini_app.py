"""迷你 FastAPI app（测试专用）

供 test_server_thread_shutdown 使用：轻量 app，不触发
edu_system 完整初始化（DB/审计/调度器），避免与 GUI 测试
共享 QApplication/DB 状态导致 SIGABRT。
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
