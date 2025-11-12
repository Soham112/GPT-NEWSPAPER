from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class CritiqueAgent:
    def __init__(self):
        pass

    def critique(self, article: dict):
        messages = [
            SystemMessage(
                content=(
                    "You are a newspaper writing critique. Your sole purpose is to provide short feedback on a "
                    "written article so the writer will know what to fix.\n "
                )
            ),
            HumanMessage(
                content=(
                    f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                    f"{str(article)}\n"
                    "Your task is to provide a really short feedback on the article only if necessary.\n"
                    "if you think the article is good, please return None.\n"
                    "if you noticed the field 'message' in the article, it means the writer has revised the article"
                    "based on your previous critique. you can provide feedback on the revised article or just "
                    "return None if you think the article is good.\n"
                    "Please return a string of your critique or None.\n"
                )
            ),
        ]

        response = ChatOpenAI(model="gpt-4", max_retries=1).invoke(messages).content
        if response == "None":
            return {"critique": None}
        else:
            print(f"For article: {article['title']}")
            print(f"Feedback: {response}\n")
            return {"critique": response, "message": None}

    def run(self, article: dict):
        article.update(self.critique(article))
        return article
