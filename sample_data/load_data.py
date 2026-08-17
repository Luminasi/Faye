# -*- coding: utf-8 -*-
"""向知识库导入示例数据的辅助脚本（可重复执行，幂等）"""
import json
import os
import sys
import time
import urllib.request

BASE = "http://localhost:8002"
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = [
    "智能手机产品手册.md",
    "家电产品手册.md",
    "笔记本与平板产品手册.md",
    "平台服务政策FAQ.md",
]


def req(method, path, token=None, data=None, content_type=None, timeout=120):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = data.encode("utf-8") if isinstance(data, str) else data
        headers["Content-Type"] = content_type or "application/json"
    r = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    # 1. 登录
    login = req("POST", "/api/auth/login", data="username=admin&password=123456",
                content_type="application/x-www-form-urlencoded")
    token = login["access_token"]
    print("[1/4] 登录成功")

    # 2. 查找或创建知识库（幂等）
    kbs = req("GET", "/api/admin/kb", token)
    kb = next((k for k in kbs if k["name"] == "电商商品知识库"), None)
    if not kb:
        kb = req("POST", "/api/admin/kb", token,
                 data=json.dumps({"name": "电商商品知识库",
                                  "description": "示例商品资料：手机/家电/笔记本/平板及平台服务政策"}))
        print("[2/4] 知识库已创建:", kb["id"])
    else:
        print("[2/4] 知识库已存在:", kb["id"])
    kb_id = kb["id"]

    # 3. 上传文件（已上传过的跳过）
    import uuid
    boundary = uuid.uuid4().hex
    existing = {d["file_name"] for d in req("GET", f"/api/admin/kb/{kb_id}/documents", token)}
    for name in FILES:
        if name in existing:
            print(f"     跳过（已存在）: {name}")
            continue
        path = os.path.join(HERE, name)
        with open(path, "rb") as f:
            content = f.read()
        body = (f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
                f"Content-Type: text/markdown\r\n\r\n").encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode()
        doc = req("POST", f"/api/admin/kb/{kb_id}/documents/upload", token,
                  data=body, content_type=f"multipart/form-data; boundary={boundary}")
        print(f"     上传: {name} -> id={doc['id']} status={doc['status']}")

    # 4. 轮询直到全部 ready
    print("[3/4] 等待向量化完成 ...")
    for _ in range(60):
        docs = req("GET", f"/api/admin/kb/{kb_id}/documents", token)
        statuses = {d["file_name"]: d["status"] for d in docs}
        if all(s == "ready" for s in statuses.values()) and statuses:
            print("[4/4] 全部文档就绪:")
            for d in docs:
                print(f"     [{d['status']}] {d['file_name']} (chunks={d.get('chunk_count', '?')})")
            return
        if any(s == "failed" for s in statuses.values()):
            for d in docs:
                if d["status"] == "failed":
                    print("上传失败:", d["file_name"], d.get("error_msg"))
            sys.exit(1)
        time.sleep(3)
    print("超时：仍有文档未就绪:", {d["file_name"]: d["status"] for d in docs})
    sys.exit(1)


if __name__ == "__main__":
    main()
