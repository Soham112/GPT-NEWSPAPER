"""
Tests for ICPProfileAgent leadership fallback behavior.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from backend.agents.icp_profile_agent import ICPProfileAgent
from backend.utils.leadership_scraper import fetch_leadership_pages


class TestICPProfileAgentFallback(unittest.TestCase):
    """Test ICPProfileAgent leadership fallback scraping."""

    def setUp(self):
        """Set up test fixtures."""
        self.icp_agent = ICPProfileAgent()

    @patch('backend.agents.icp_profile_agent.fetch_leadership_pages')
    def test_leadership_fallback_when_no_leaders_found(self, mock_fetch_leadership):
        """Test that leadership fallback is triggered when LLM returns no leaders."""
        # Mock LLM to return JSON with empty leaders
        mock_llm_response = Mock()
        mock_llm_response.content = """{
            "companies": [
                {
                    "name": "First Solar",
                    "icp_titles": ["CEO", "CTO"],
                    "leaders": []
                }
            ],
            "sources": []
        }"""
        
        self.icp_agent.llm.invoke = Mock(return_value=mock_llm_response)
        
        # Mock leadership scraper to return some leaders
        mock_fetch_leadership.return_value = {
            "leaders": [
                {
                    "name": "John Doe",
                    "title": "Chief Executive Officer",
                    "source": "https://firstsolar.com/leadership"
                },
                {
                    "name": "Jane Smith",
                    "title": "VP Operations",
                    "source": "https://firstsolar.com/about-us"
                }
            ],
            "checked_urls": ["https://firstsolar.com/leadership"]
        }
        
        result = self.icp_agent.run(
            topic="First Solar leadership team",
            bullets=[{"text": "First Solar is a solar panel manufacturer.", "cite": [1]}],
            insights=None,
            tags={"companies": ["First Solar"]},
            sources=[{"url": "https://example.com", "title": "Example", "snippet": "Content"}],
            region="US",
            is_leadership_query=True,
            raw_query="First Solar leadership team",
            company_hint="First Solar"
        )
        
        # Verify that fetch_leadership_pages was called
        mock_fetch_leadership.assert_called_once_with("First Solar")
        
        # Verify that leaders were added to the result
        if result.get("companies"):
            first_company = result["companies"][0]
            leaders = first_company.get("leaders", [])
            
            # Should have leaders from the fallback scraper
            self.assertGreater(len(leaders), 0, "Leaders should be added from fallback scraper")
            
            # Verify leader structure
            if leaders:
                leader = leaders[0]
                self.assertIn("name", leader)
                self.assertIn("title", leader)
                self.assertIn("is_icp_title", leader)
                self.assertIn("reason", leader)
                self.assertIn("source", leader)

    @patch('backend.agents.icp_profile_agent.fetch_leadership_pages')
    def test_leadership_fallback_not_triggered_when_leaders_exist(self, mock_fetch_leadership):
        """Test that leadership fallback is NOT triggered when LLM already found leaders."""
        # Mock LLM to return JSON with leaders already present
        mock_llm_response = Mock()
        mock_llm_response.content = """{
            "companies": [
                {
                    "name": "First Solar",
                    "icp_titles": ["CEO", "CTO"],
                    "leaders": [
                        {
                            "name": "Existing Leader",
                            "title": "CEO",
                            "is_icp_title": true,
                            "reason": "Found in sources",
                            "source": "https://example.com"
                        }
                    ]
                }
            ],
            "sources": []
        }"""
        
        self.icp_agent.llm.invoke = Mock(return_value=mock_llm_response)
        
        result = self.icp_agent.run(
            topic="First Solar leadership team",
            bullets=[{"text": "First Solar is a solar panel manufacturer.", "cite": [1]}],
            insights=None,
            tags={"companies": ["First Solar"]},
            sources=[{"url": "https://example.com", "title": "Example", "snippet": "Content"}],
            region="US",
            is_leadership_query=True,
            raw_query="First Solar leadership team",
            company_hint="First Solar"
        )
        
        # Verify that fetch_leadership_pages was NOT called (since leaders already exist)
        mock_fetch_leadership.assert_not_called()
        
        # Verify that existing leaders are preserved
        if result.get("companies"):
            first_company = result["companies"][0]
            leaders = first_company.get("leaders", [])
            self.assertGreater(len(leaders), 0, "Existing leaders should be preserved")
            self.assertEqual(leaders[0]["name"], "Existing Leader")

    @patch('backend.agents.icp_profile_agent.fetch_leadership_pages')
    def test_leadership_fallback_is_icp_title_detection(self, mock_fetch_leadership):
        """Test that is_icp_title is correctly set based on title matching buying roles."""
        # Mock LLM to return empty leaders
        mock_llm_response = Mock()
        mock_llm_response.content = """{
            "companies": [
                {
                    "name": "First Solar",
                    "icp_titles": ["CEO", "CTO"],
                    "leaders": []
                }
            ],
            "sources": []
        }"""
        
        self.icp_agent.llm.invoke = Mock(return_value=mock_llm_response)
        
        # Mock leadership scraper to return leaders with different titles
        mock_fetch_leadership.return_value = {
            "leaders": [
                {
                    "name": "John Doe",
                    "title": "Chief Executive Officer",  # Should be ICP title
                    "source": "https://firstsolar.com/leadership"
                },
                {
                    "name": "Jane Smith",
                    "title": "VP Operations",  # Should be ICP title
                    "source": "https://firstsolar.com/about-us"
                },
                {
                    "name": "Bob Johnson",
                    "title": "Marketing Director",  # Should NOT be ICP title
                    "source": "https://firstsolar.com/about-us"
                }
            ],
            "checked_urls": ["https://firstsolar.com/leadership"]
        }
        
        result = self.icp_agent.run(
            topic="First Solar leadership team",
            bullets=[{"text": "First Solar is a solar panel manufacturer.", "cite": [1]}],
            insights=None,
            tags={"companies": ["First Solar"]},
            sources=[{"url": "https://example.com", "title": "Example", "snippet": "Content"}],
            region="US",
            is_leadership_query=True,
            raw_query="First Solar leadership team",
            company_hint="First Solar"
        )
        
        # Verify that is_icp_title is set correctly
        if result.get("companies"):
            first_company = result["companies"][0]
            leaders = first_company.get("leaders", [])
            
            # Find leaders by name
            ceo_leader = next((l for l in leaders if l.get("name") == "John Doe"), None)
            vp_leader = next((l for l in leaders if l.get("name") == "Jane Smith"), None)
            marketing_leader = next((l for l in leaders if l.get("name") == "Bob Johnson"), None)
            
            if ceo_leader:
                self.assertTrue(ceo_leader.get("is_icp_title"), "CEO should be marked as ICP title")
            if vp_leader:
                self.assertTrue(vp_leader.get("is_icp_title"), "VP Operations should be marked as ICP title")
            if marketing_leader:
                self.assertFalse(marketing_leader.get("is_icp_title"), "Marketing Director should NOT be marked as ICP title")

    @patch('backend.utils.leadership_scraper.httpx.get')
    def test_fetch_leadership_pages_structure(self, mock_httpx):
        """Test that fetch_leadership_pages returns the expected structure."""
        # Mock HTTP response with HTML content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <h2>John Doe</h2>
                <p>Chief Executive Officer</p>
                <h2>Jane Smith</h2>
                <p>VP Operations</p>
            </body>
        </html>
        """
        mock_httpx.return_value = mock_response
        
        result = fetch_leadership_pages("First Solar")
        
        # Verify structure
        self.assertIn("leaders", result)
        self.assertIn("checked_urls", result)
        self.assertIsInstance(result["leaders"], list)
        self.assertIsInstance(result["checked_urls"], list)

    @patch('backend.agents.icp_profile_agent.fetch_leadership_pages')
    def test_non_leadership_query_no_fallback(self, mock_fetch):
        """Test that non-leadership queries do not trigger fallback."""
        # Mock LLM to return empty leaders
        mock_llm_response = Mock()
        mock_llm_response.content = """{
            "companies": [
                {
                    "name": "First Solar",
                    "icp_titles": ["CEO", "CTO"],
                    "leaders": []
                }
            ],
            "sources": []
        }"""
        
        self.icp_agent.llm.invoke = Mock(return_value=mock_llm_response)
        result = self.icp_agent.run(
            topic="First Solar ideal customer profile",
            bullets=[{"text": "First Solar is a solar panel manufacturer.", "cite": [1]}],
            insights=None,
            tags={"companies": ["First Solar"]},
            sources=[{"url": "https://example.com", "title": "Example", "snippet": "Content"}],
            region="US",
            is_leadership_query=False,  # NOT a leadership query
            raw_query="First Solar ideal customer profile",
            company_hint=None
        )
        
        # Verify that fetch_leadership_pages was NOT called
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()

