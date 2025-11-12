from datetime import datetime

import json5 as json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

sample_json = """
{
  "title": title of the article,
  "date": today's date,
  "paragraphs": [
    "paragraph 1",
    "paragraph 2",
    "paragraph 3",
    "paragraph 4",
    "paragraph 5",
    ],
    "summary": "2 sentences summary of the article"
}
"""

sample_revise_json = """
{
    "paragraphs": [
        "paragraph 1",
        "paragraph 2",
        "paragraph 3",
        "paragraph 4",
        "paragraph 5",
    ],
    "message": "message to the critique"
}
"""


class WriterAgent:
    def __init__(self):
        pass

    def writer(self, query: str, sources: list):
        messages = [
            SystemMessage(
                content=(
                    "You are a newspaper writer. Your sole purpose is to write a well-written article about a "
                    "topic using a list of articles.\n "
                )
            ),
            HumanMessage(
                content=(
                    f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                    f"Query or Topic: {query}"
                    f"{sources}\n"
                    "Your task is to write a critically acclaimed article for me about the provided query or topic "
                    "based on the sources.\n "
                    "Please return nothing but a JSON in the following format:\n"
                    f"{sample_json}\n "
                )
            ),
        ]

        optional_params = {"response_format": {"type": "json_object"}}

        response = (
            ChatOpenAI(
                model="gpt-4-0125-preview",
                max_retries=1,
                model_kwargs=optional_params,
            )
            .invoke(messages)
            .content
        )
        return json.loads(response)

    def revise(self, article: dict):
        messages = [
            SystemMessage(
                content=(
                    "You are a newspaper editor. Your sole purpose is to edit a well-written article about a "
                    "topic based on given critique\n "
                )
            ),
            HumanMessage(
                content=(
                    f"{str(article)}\n"
                    "Your task is to edit the article based on the critique given.\n "
                    "Please return json format of the 'paragraphs' and a new 'message' field"
                    "to the critique that explain your changes or why you didn't change anything.\n"
                    "please return nothing but a JSON in the following format:\n"
                    f"{sample_revise_json}\n "
                )
            ),
        ]

        optional_params = {"response_format": {"type": "json_object"}}

        response = (
            ChatOpenAI(
                model="gpt-4-0125-preview",
                max_retries=1,
                model_kwargs=optional_params,
            )
            .invoke(messages)
            .content
        )
        response = json.loads(response)
        print(f"For article: {article['title']}")
        print(f"Writer Revision Message: {response['message']}\n")
        return response

    def run(self, article: dict):
        critique = article.get("critique")
        if critique is not None:
            article.update(self.revise(article))
        else:
            article.update(self.writer(article["query"], article["sources"]))
        return article
