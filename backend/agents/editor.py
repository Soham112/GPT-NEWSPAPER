import os

# Single, clean article template
ARTICLE_TEMPLATE = """
    <div class="article">
        <a href="{{path}}" target="_blank"><h2>{{title}}</h2></a>
        <img src="{{image}}" alt="Article Image">
        <p>{{summary}}</p>
    </div>
"""


class EditorAgent:
    def __init__(self, layout=None):
        """
        Initialize EditorAgent.
        
        Args:
            layout: Deprecated parameter, kept for backward compatibility.
                   The agent now uses a single unified layout.
        """
        self.layout = "layout.html"  # Always use the unified layout

    def load_html_template(self):
        """Load the unified newspaper layout template."""
        template_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'templates', 
            'newspaper', 
            'layouts', 
            self.layout
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def render_article(self, article):
        """
        Render a single article using the unified template.
        
        Args:
            article: Dictionary containing article data (title, image, summary, path)
            
        Returns:
            HTML string for the article
        """
        article_html = ARTICLE_TEMPLATE.replace("{{title}}", article.get("title", ""))
        article_html = article_html.replace("{{image}}", article.get("image", ""))
        article_html = article_html.replace("{{summary}}", article.get("summary", ""))
        article_html = article_html.replace("{{path}}", article.get("path", "#"))
        return article_html

    def editor(self, articles):
        """
        Generate the complete newspaper HTML from articles.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Complete newspaper HTML string
        """
        if not articles:
            raise ValueError("Articles list cannot be empty")

        html_template = self.load_html_template()

        # Generate articles HTML
        articles_html = ""
        for article in articles:
            articles_html += self.render_article(article)

        # Replace placeholders in template
        date = articles[0].get("date", "")
        html_template = html_template.replace("{{date}}", date)
        newspaper_html = html_template.replace("{{articles}}", articles_html)
        
        return newspaper_html

    def run(self, articles):
        """
        Main entry point for generating newspaper HTML.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Complete newspaper HTML string
        """
        return self.editor(articles)
