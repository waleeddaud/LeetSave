from config import get_settings

settings = get_settings()

EXPLANATION_PROMPT = """You are explaining a user's accepted LeetCode solution.
Problem Title: {problem_title}
Problem Slug: {problem_slug}
Difficulty: {difficulty}
Language: {language}
Accepted Code:
{code}

Write a clear markdown explanation with:
- Approach
- Step-by-step logic
- Time complexity
- Space complexity
- Edge cases
Do not claim details that are not supported by the code.
Keep it concise and professional."""


FALLBACK_EXPLANATION = """# {problem_title}

Explanation generation failed. The accepted solution was still saved.

## Code

```{language}
{code}
```
"""


async def generate_explanation(
    problem_title: str,
    problem_slug: str,
    difficulty: str | None,
    language: str,
    code: str,
) -> str:
    provider = settings.llm_provider.lower().strip()
    prompt = EXPLANATION_PROMPT.format(
        problem_title=problem_title,
        problem_slug=problem_slug,
        difficulty=difficulty or "unknown",
        language=language,
        code=code,
    )

    try:
        if provider == "openai":
            return await _generate_openai(prompt)
        if provider == "gemini":
            return await _generate_gemini(prompt)
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    except Exception:
        return FALLBACK_EXPLANATION.format(
            problem_title=problem_title,
            language=language,
            code=code,
        )


async def _generate_openai(prompt: str) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    llm = ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key, temperature=0.2)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        return "".join(str(part) for part in content)
    return str(content)


async def _generate_gemini(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    model = settings.gemini_model or settings.llm_model
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=settings.gemini_api_key, temperature=0.2)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content
    if isinstance(content, list):
        return "".join(str(part) for part in content)
    return str(content)
