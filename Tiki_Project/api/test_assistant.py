# ============================================================
# TEST SUITE - AI Business Assistant
# ============================================================

import sys
import os
import json
import unittest

# Ensure the api directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from model_loader import ModelLoader
from search_engine_v2 import SearchEngine
from chat_assistant import AIBusinessAssistant
from config import settings

class TestAIBusinessAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up standard instances before running tests"""
        print("\n📥 Initializing test dependencies...")
        cls.data_loader = DataLoader(data_dir=settings.DATA_PATH)
        cls.model_loader = ModelLoader(models_dir=settings.MODELS_PATH)
        cls.search_engine = SearchEngine(
            data_loader=cls.data_loader,
            model_loader=cls.model_loader,
            rag_engine=None,
            gemini_model=None
        )
        cls.assistant = AIBusinessAssistant(search_engine=cls.search_engine)
        print("✅ Dependencies loaded successfully")

    def test_assistant_initialization(self):
        """Test assistant is correctly initialized with instruction and tools"""
        self.assertIsNotNone(self.assistant)
        self.assertIsNotNone(self.assistant.system_instruction)
        self.assertTrue(len(self.assistant.tools) >= 7)
        print("✅ Assistant initialization check passed")

    def test_recommend_business(self):
        """Test recommend_business tool calculations"""
        session_id = "test_sess_recommend"
        self.assistant.sessions[session_id] = {
            "history": [],
            "profile": {"capital": None, "location": "TP.HCM", "interest": None, "experience": None},
            "active_business": None
        }
        
        # Call recommend business
        res_str = self.assistant.recommend_business(capital=100000000.0, location="TP.HCM", interest="tai nghe", experience="beginner")
        res = json.loads(res_str)
        
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("capital"), 100000000.0)
        self.assertTrue(len(res.get("recommendations", [])) > 0)
        
        # Verify recommended model has a matching score and stats
        rec = res["recommendations"][0]
        self.assertIn("category", rec)
        self.assertIn("matching_score", rec)
        self.assertTrue(rec["matching_score"] > 0)
        self.assertTrue(rec["average_price"] > 0)
        self.assertTrue(len(rec["examples"]) > 0)
        print(f"✅ recommend_business check passed (matching score: {rec['matching_score']}%)")

    def test_get_business_detail(self):
        """Test get_business_detail fetches product information"""
        res_str = self.assistant.get_business_detail("Bộ 4 Chân Kê Chống Rung Máy Giặt")
        res = json.loads(res_str)
        self.assertTrue(res.get("success"))
        self.assertIsNotNone(res.get("product"))
        
        p = res["product"]
        self.assertTrue(len(p["title"]) > 0)
        self.assertTrue(p["price"] > 0)
        print(f"✅ get_business_detail check passed ({p['title'][:40]}...)")

    def test_analyze_profit(self):
        """Test analyze_profit calculates realistic numbers"""
        res_str = self.assistant.analyze_profit("Bộ 4 Chân Kê Chống Rung Máy Giặt")
        res = json.loads(res_str)
        self.assertTrue(res.get("success"))
        self.assertIsNotNone(res.get("analysis"))
        
        a = res["analysis"]
        self.assertTrue(a["monthly_sold_units"] >= 0)
        self.assertTrue(a["estimated_monthly_profit"] >= 0)
        self.assertTrue(a["estimated_payback_months"] > 0)
        self.assertTrue(a["breakdown"]["total_initial_investment"] > 0)
        print(f"✅ analyze_profit check passed (monthly profit: {a['estimated_monthly_profit']:,} VND)")

    def test_analyze_risk(self):
        """Test analyze_risk counts review sentiments correctly"""
        res_str = self.assistant.analyze_risk("Bộ 4 Chân Kê Chống Rung Máy Giặt")
        res = json.loads(res_str)
        self.assertTrue(res.get("success"))
        self.assertIsNotNone(res.get("risk_analysis"))
        
        ra = res["risk_analysis"]
        self.assertTrue(ra["rating"] > 0)
        self.assertIn("sentiment_distribution", ra)
        self.assertIn("competition_risk_level", ra["risk_profile"])
        print(f"✅ analyze_risk check passed (rating: {ra['rating']}⭐)")

    def test_analyze_market(self):
        """Test analyze_market macro statistics"""
        res_str = self.assistant.analyze_market("máy giặt")
        res = json.loads(res_str)
        self.assertTrue(res.get("success"))
        self.assertIsNotNone(res.get("market"))
        
        m = res["market"]
        self.assertTrue(m["total_competitor_listings"] > 0)
        self.assertTrue(m["estimated_monthly_market_size_revenue"] > 0)
        print(f"✅ analyze_market check passed (market size: {m['estimated_monthly_market_size_revenue']:,} VND)")

    def test_compare_businesses(self):
        """Test compare_businesses comparison dictionary"""
        res_str = self.assistant.compare_businesses("Bộ 4 Chân Kê Chống Rung Máy Giặt", "Nhang sạch Liên Tâm")
        res = json.loads(res_str)
        self.assertTrue(res.get("success"))
        self.assertIn("comparison", res)
        self.assertIn("item_a", res["comparison"])
        self.assertIn("item_b", res["comparison"])
        print("✅ compare_businesses check passed")

    def test_generate_roadmap(self):
        """Test generate_roadmap step steps"""
        res_str = self.assistant.generate_roadmap("Bộ 4 Chân Kê Chống Rung Máy Giặt")
        res = json.loads(res_str)
        self.assertTrue(res.get("success"))
        self.assertIn("roadmap", res)
        self.assertTrue(len(res["roadmap"]["steps"]) >= 5)
        print(f"✅ generate_roadmap check passed (steps count: {len(res['roadmap']['steps'])})")

if __name__ == "__main__":
    unittest.main()
