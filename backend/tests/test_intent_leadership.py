"""
Tests for IntentClassifier leadership detection.
"""
import unittest
from backend.intent_classifier import detect_query_intent, LEADERSHIP_KEYWORDS


class TestIntentClassifierLeadership(unittest.TestCase):
    """Test leadership query detection in IntentClassifier."""

    def test_leadership_query_with_company_name(self):
        """Test that leadership queries with company names are detected."""
        query = "Who is on the leadership team at Acme Corp?"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertFalse(intent.include_insights)
        self.assertTrue(intent.is_leadership_query, "Should detect leadership query")

    def test_leadership_query_ceo(self):
        """Test CEO queries are detected as leadership."""
        query = "First Solar CEO executives"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertTrue(intent.is_leadership_query, "CEO query should be leadership")

    def test_leadership_query_board_of_directors(self):
        """Test board of directors queries are detected."""
        query = "Tesla board of directors"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertTrue(intent.is_leadership_query, "Board query should be leadership")

    def test_leadership_query_executive_team(self):
        """Test executive team queries are detected."""
        query = "OpenAI executive team leadership"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertTrue(intent.is_leadership_query, "Executive team query should be leadership")

    def test_leadership_query_c_suite(self):
        """Test C-suite queries are detected."""
        query = "Microsoft C-suite executives"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertTrue(intent.is_leadership_query, "C-suite query should be leadership")

    def test_leadership_query_founder(self):
        """Test founder queries are detected."""
        query = "Apple founder leadership"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertTrue(intent.is_leadership_query, "Founder query should be leadership")

    def test_non_leadership_icp_query(self):
        """Test that ICP queries without leadership keywords are not leadership mode."""
        query = "ideal customer profile for construction tech"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "icp_profiles")
        self.assertFalse(intent.include_insights)
        self.assertFalse(intent.is_leadership_query, "Non-leadership ICP query should not be leadership mode")

    def test_funding_query_not_leadership(self):
        """Test that funding queries are not leadership mode."""
        query = "Tesla raised funding"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "funding")
        self.assertFalse(intent.is_leadership_query, "Funding query should not be leadership mode")

    def test_industry_query_not_leadership(self):
        """Test that generic industry queries are not leadership mode."""
        query = "solar energy trends"
        intent = detect_query_intent(query)
        
        self.assertEqual(intent.use_case, "industry")
        self.assertFalse(intent.is_leadership_query, "Industry query should not be leadership mode")

    def test_leadership_keywords_list(self):
        """Test that all expected leadership keywords are in the list."""
        expected_keywords = [
            "leadership", "board of directors", "board", "ceo", "founder",
            "executive team", "executives", "c-suite", "org chart",
            "vp ops", "cro", "cto", "cfo", "chief", "president"
        ]
        
        for keyword in expected_keywords:
            self.assertIn(keyword.lower(), [k.lower() for k in LEADERSHIP_KEYWORDS],
                         f"Keyword '{keyword}' should be in LEADERSHIP_KEYWORDS")


if __name__ == "__main__":
    unittest.main()

