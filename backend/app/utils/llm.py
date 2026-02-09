from app.utils.retry import with_retry


@with_retry(max_attempts=3, min_wait=1, max_wait=4)
def invoke_llm(llm, prompt: str):
    return llm.invoke(prompt)
