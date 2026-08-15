"""
样例数据一键导入脚本：
  - 确保 Ollama 服务已启动并 pull 了 nomic-embed-text 模型
  - 运行方式（backend 目录下）：
      python seed_demo_data.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 初始化 DB 表 + 管理员
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import KnowledgeBase  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.services import user_service  # noqa: E402
from app.services.knowledge_service import (
    create_kb,
    _chunks_dir,
    fl,
    vs,
)  # noqa: E402
from app.models import Document, DocStatus  # noqa: E402
from datetime import datetime  # noqa: E402
import json  # noqa: E402

settings = get_settings()

# 知识库 -> 样例文件名前缀映射
DEMO_KB_CONFIG = [
    {
        "name": "手机类知识库",
        "description": "智尚 X100 Pro 等手机产品的规格、FAQ、售后",
        "files_prefix": ["手机_"],
    },
    {
        "name": "笔记本电脑知识库",
        "description": "星瀚 P15 笔记本电脑的参数与售后政策",
        "files_prefix": ["笔记本_"],
    },
    {
        "name": "大家电知识库",
        "description": "冰箱、空调等大家电的规格、故障码与售后",
        "files_prefix": ["家电_"],
    },
    {
        "name": "通用规则知识库",
        "description": "全平台通用的退换货政策、会员与积分规则",
        "files_prefix": ["通用_"],
    },
]

SAMPLE_DOCS_DIR = Path(__file__).parent / "data" / "sample_docs"


def process_one_file(kb: KnowledgeBase, file_path: Path, db):
    """同步解析 + 向量化 + 入库，不走后台任务，保证脚本结束时就绪"""
    from app.rag import file_loader as fl_mod, vector_store as vs_mod

    ext = file_path.suffix.lstrip(".").lower()
    size = file_path.stat().st_size
    doc = Document(
        kb_id=kb.id,
        file_name=file_path.name,
        file_path=str(file_path),  # 保留原 sample_docs 路径，勿移动
        file_type=ext,
        file_size=size,
        status=DocStatus.PROCESSING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        chunks = fl_mod.load_and_split(doc.file_path, file_name=doc.file_name, doc_id=doc.id)
        # 保存预览 JSON
        chunks_path = _chunks_dir() / f"doc_{doc.id}.json"
        preview = [
            {"chunk_index": c.metadata.get("chunk_index", i), "content": c.page_content, "metadata": c.metadata}
            for i, c in enumerate(chunks)
        ]
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(preview, f, ensure_ascii=False, indent=2)

        added = 0
        if chunks:
            added = vs_mod.add_documents(kb.collection_name, chunks)
        doc.chunk_count = added
        doc.status = DocStatus.READY
        doc.updated_at = datetime.now()
        db.commit()
        print(f"  [OK] {file_path.name:40s} chunks={added}")
    except Exception as e:
        print(f"  [FAIL] {file_path.name}: {e}")
        doc.status = DocStatus.FAILED
        doc.error_msg = str(e)[:512]
        db.commit()


def main():
    if not SAMPLE_DOCS_DIR.exists():
        print(f"[ERROR] 样例文档目录不存在：{SAMPLE_DOCS_DIR}")
        sys.exit(1)

    # 1. 建表
    Base.metadata.create_all(bind=engine)

    # 2. 确保管理员账号
    db = SessionLocal()
    try:
        user_service.create_user(
            db,
            username=settings.ADMIN_USERNAME,
            password=settings.ADMIN_PASSWORD,
            email=settings.ADMIN_EMAIL,
        )
        print(f"[OK] 管理员已创建: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
    except Exception:
        print(f"[SKIP] 管理员 {settings.ADMIN_USERNAME} 已存在")
    db.close()

    # 3. 创建知识库并导入文档
    all_files = list(SAMPLE_DOCS_DIR.iterdir())
    print(f"[INFO] 扫描到样例文档 {len(all_files)} 个，开始导入...")
    print("=" * 64)

    db = SessionLocal()
    try:
        for cfg in DEMO_KB_CONFIG:
            # 知识库不存在则创建，存在则直接复用
            existed = db.query(KnowledgeBase).filter(KnowledgeBase.name == cfg["name"]).first()
            if existed:
                kb = existed
                print(f"[INFO] 复用已存在的知识库「{kb.name}」(collection={kb.collection_name})")
            else:
                kb = create_kb(db, name=cfg["name"], description=cfg["description"])
                print(f"\n[KB] 创建「{kb.name}」 (collection={kb.collection_name})")
            # 匹配文件名前缀
            matched = [p for p in all_files if any(p.name.startswith(pref) for pref in cfg["files_prefix"])]
            for fp in matched:
                # 同一知识库下，同名文件已入库则跳过（按文件名幂等）
                dup = (
                    db.query(Document)
                    .filter(Document.kb_id == kb.id, Document.file_name == fp.name)
                    .first()
                )
                if dup:
                    # 如果之前是 FAILED 状态，重新处理
                    if dup.status == DocStatus.FAILED or (dup.chunk_count or 0) == 0:
                        print(f"  [RETRY] 重新处理 {fp.name} (上一次 status={dup.status}, chunks={dup.chunk_count})")
                        db.delete(dup)
                        db.commit()
                    else:
                        print(f"  [SKIP] {fp.name:40s} 已入库 (chunks={dup.chunk_count})")
                        continue
                process_one_file(kb, fp, db)
        print("\n" + "=" * 64)
        print("[DONE] 样例数据导入完成！")
        print("  管理员账号：", settings.ADMIN_USERNAME, "/", settings.ADMIN_PASSWORD)
        print("  登录后访问：")
        print("    - 知识库管理（管理员）：http://localhost:5173/admin/kb")
        print("    - 问答页面（所有用户）：http://localhost:5173/chat")
    finally:
        db.close()


if __name__ == "__main__":
    main()
