from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import SystemMessage


def init_msg_prompt(sys_prompt: str) -> ChatPromptTemplate:
    chat_prompt: ChatPromptTemplate = SystemMessage(content=sys_prompt) + MessagesPlaceholder(variable_name="history") + "{user_prompt}"
    return chat_prompt


# NOTE It just inserts system prompt into user prompt
chat_template = """\
{sys_name}:{sys_prompt}
{history}
{user_name}:{user_prompt}
{ai_name}:\
"""


def init_str_prompt(sys_name: str, sys_prompt: str, user_name: str, ai_name: str) -> PromptTemplate:
    input_variables = ["user_prompt", "history"]
    template = chat_template.format(
        sys_name=sys_name,
        sys_prompt=sys_prompt,
        user_name=user_name,
        ai_name=ai_name,
        **{var: f"{{{var}}}" for var in input_variables},  # not replace
    )

    chat_prompt = PromptTemplate(
        input_variables=input_variables,
        template=template,
    )

    return chat_prompt
