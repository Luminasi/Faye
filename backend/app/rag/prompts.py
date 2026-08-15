"""RAG Prompt 模板"""

RAG_SYSTEM_PROMPT_ZH = """你是一名专业的电商平台智能客服助手。请根据下面提供的【参考资料】认真回答用户的问题。

【回答规则】
1. 必须以【参考资料】中的内容为依据，禁止编造资料中不存在的信息。
2. 如果【参考资料】中没有相关信息，明确告知用户"当前知识库中暂无相关资料，请换个问题或联系人工客服"。
3. 回答语言使用**简体中文**，语气友好、专业、清晰。
4. 回答时，尽量在对应信息点后标注来源编号，例如：[1][2]。编号必须与【参考资料】一致。
5. 可以对资料内容做结构化整理（例如分点、表格化），但不要改变原意。

【参考资料】
{context}

---
用户问题：{question}
"""


def build_rag_prompt():
    from langchain_core.prompts import ChatPromptTemplate

    return ChatPromptTemplate.from_messages(
        [
            ("system", RAG_SYSTEM_PROMPT_ZH),
            ("human", "{question}"),
        ]
    )


def format_docs_for_context(docs) -> str:
    """把 docs 拼成带编号的参考资料文本，供 LLM 引用"""
    snippets = []
    for i, doc in enumerate(docs, start=1):
        md = doc.metadata or {}
        src_name = md.get("doc_name") or md.get("source") or "未知来源"
        page = md.get("page")
        page_tag = f"（第{page}页）" if page else ""
        snippet = doc.page_content.replace("\n", " ").strip()
        # 过长截断，避免上下文爆 token
        if len(snippet) > 1200:
            snippet = snippet[:1200] + "..."
        snippets.append(f"[{i}] 《{src_name}》{page_tag}：{snippet}")
    return "\n\n".join(snippets) if snippets else "（当前检索未命中任何相关资料）"
