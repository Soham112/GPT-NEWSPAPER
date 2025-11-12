from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class CuratorAgent:
    def __init__(self):
        pass

    def curate_sources(self, query: str, sources: list):
        """
        Curate relevant sources for a query
        :param input:
        :return:
        """
        messages = [
            SystemMessage(
                content=(
                    "You are a personal newspaper editor. Your sole purpose is to choose 5 most relevant "
                    "article for me to read from a list of articles.\n "
                )
            ),
            HumanMessage(
                content=(
                    f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                    f"Topic or Query: {query}\n"
                    "Your task is to return the 5 most relevant articles for me to read for the provided topic "
                    "or query\n "
                    f"Here is a list of articles:\n{sources}\n"
                    "Please return nothing but a list of the strings of the URLs in this structure: "
                    "['url1','url2','url3','url4','url5'].\n "
                )
            ),
        ]

        response = ChatOpenAI(model="gpt-4-0125-preview", max_retries=1).invoke(messages).content
        chosen_sources = response
        for item in list(sources):
            if item["url"] not in chosen_sources:
                sources.remove(item)
        return sources

    def run(self, article: dict):
        article["sources"] = self.curate_sources(article["query"], article["sources"])
        return article
