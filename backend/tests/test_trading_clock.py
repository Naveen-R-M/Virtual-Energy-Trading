# Test Suite for PJM Trading Clock - DST-Safe Trading Day State Machine
# Comprehensive tests including DST transitions and edge cases

import pytest
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.trading_clock import TradingClock, TradingState, get_trading_state
from app.services.da_rules import DAOrderRulesEngine, DAOrderValidationError

class TestTradingClock:
    """Test PJM Trading Clock with DST transitions and edge cases"""
    
    def setup_method(self):
        """Setup test environment"""
        # Set test environment variables
        os.environ["PJM_STATE_MACHINE_ENABLED"] = "true"
        os.environ["ORDER_CUTOFF_HOUR"] = "11"
        os.environ["ORDER_CUTOFF_MINUTE"] = "0"
        os.environ["ORDER_CUTOFF_SECOND"] = "0"
        
        self.trading_clock = TradingClock()
        
    def test_dst_spring_forward_transition(self):
        """Test DST spring forward transition (2:00 AM -> 3:00 AM)"""
        # March 10, 2024 - Spring forward at 2:00 AM ET
        spring_forward_date = datetime(2024, 3, 10, 7, 0, 0)  # 2:00 AM ET = 7:00 AM UTC
        
        # Before transition - should be PRE_11AM
        state = self.trading_clock.get_trading_state(spring_forward_date)
        assert state == TradingState.PRE_11AM
        
        # After 11 AM on spring forward day
        after_cutoff = datetime(2024, 3, 10, 15, 0, 0)  # 11:00 AM EDT = 15:00 UTC
        state = self.trading_clock.get_trading_state(after_cutoff)
        assert state == TradingState.POST_11AM
    
    def test_dst_fall_back_transition(self):
        """Test DST fall back transition (2:00 AM -> 1:00 AM)"""
        # November 3, 2024 - Fall back at 2:00 AM ET
        fall_back_date = datetime(2024, 11, 3, 6, 0, 0)  # 1:00 AM EST = 6:00 AM UTC
        
        # Before transition - should be PRE_11AM
        state = self.trading_clock.get_trading_state(fall_back_date)
        assert state == TradingState.PRE_11AM
        
        # After 11 AM on fall back day
        after_cutoff = datetime(2024, 11, 3, 16, 0, 0)  # 11:00 AM EST = 16:00 UTC
        state = self.trading_clock.get_trading_state(after_cutoff)
        assert state == TradingState.POST_11AM
    
    def test_critical_cutoff_edge_cases(self):
        """Test critical 11:00:00 cutoff boundary with microsecond precision"""
        # Test date in standard time (no DST complications)
        test_date = datetime(2024, 1, 15)
        
        # 10:59:59.999 ET = should allow DA
        before_cutoff = datetime(2024, 1, 15, 15, 59, 59, 999000)  # UTC
        state = self.trading_clock.get_trading_state(before_cutoff)
        assert state == TradingState.PRE_11AM
        assert self.trading_clock.is_da_allowed(before_cutoff) == True
        
        # 11:00:00.000 ET = should block DA
        at_cutoff = datetime(2024, 1, 15, 16, 0, 0, 0)  # UTC
        state = self.trading_clock.get_trading_state(at_cutoff)
        assert state == TradingState.POST_11AM
        assert self.trading_clock.is_da_allowed(at_cutoff) == False
        
        # 11:00:00.001 ET = should block DA
        after_cutoff = datetime(2024, 1, 15, 16, 0, 0, 1000)  # UTC
        state = self.trading_clock.get_trading_state(after_cutoff)
        assert state == TradingState.POST_11AM
        assert self.trading_clock.is_da_allowed(after_cutoff) == False
    
    def test_state_transitions_throughout_day(self):
        """Test all state transitions throughout trading day"""
        base_date = datetime(2024, 6, 15)  # June 15, 2024 (EDT)
        
        # Midnight ET = 4:00 AM UTC (EDT)
        midnight_utc = datetime(2024, 6, 15, 4, 0, 0)
        assert self.trading_clock.get_trading_state(midnight_utc) == TradingState.PRE_11AM
        
        # 6:00 AM ET = 10:00 AM UTC
        morning_utc = datetime(2024, 6, 15, 10, 0, 0)
        assert self.trading_clock.get_trading_state(morning_utc) == TradingState.PRE_11AM
        
        # 11:00 AM ET = 15:00 PM UTC
        cutoff_utc = datetime(2024, 6, 15, 15, 0, 0)
        assert self.trading_clock.get_trading_state(cutoff_utc) == TradingState.POST_11AM
        
        # 6:00 PM ET = 22:00 PM UTC
        evening_utc = datetime(2024, 6, 15, 22, 0, 0)
        assert self.trading_clock.get_trading_state(evening_utc) == TradingState.POST_11AM
        
        # 11:59 PM ET = 03:59 AM UTC (next day)
        late_night_utc = datetime(2024, 6, 16, 3, 59, 0)
        assert self.trading_clock.get_trading_state(late_night_utc) == TradingState.POST_11AM
    
    def test_next_transition_calculations(self):
        """Test next state transition time calculations"""
        # Test at 10:30 AM ET
        test_time = datetime(2024, 6, 15, 14, 30, 0)  # 10:30 AM EDT = 14:30 UTC
        
        info = self.trading_clock.get_trading_info(test_time)
        
        assert info["state"] == TradingState.PRE_11AM.value
        assert info["next_transition"]["next_state"] == TradingState.POST_11AM.value
        assert info["next_transition"]["seconds_until"] == 1800  # 30 minutes = 1800 seconds
    
    def test_feature_flag_disabled(self):
        """Test behavior when feature flag is disabled"""
        # Temporarily disable feature flag
        os.environ["PJM_STATE_MACHINE_ENABLED"] = "false"
        disabled_clock = TradingClock()
        
        # Should always return PRE_11AM (legacy behavior)
        test_time = datetime(2024, 6, 15, 20, 0, 0)  # Well after 11 AM
        state = disabled_clock.get_trading_state(test_time)
        assert state == TradingState.PRE_11AM
        
        # Restore flag
        os.environ["PJM_STATE_MACHINE_ENABLED"] = "true"
    
    def test_timezone_handling_consistency(self):
        """Test timezone handling consistency across different times of year"""
        # Test times in different parts of the year
        test_cases = [
            datetime(2024, 1, 15, 16, 0, 0),  # Winter (EST)
            datetime(2024, 4, 15, 15, 0, 0),  # Spring (EDT) 
            datetime(2024, 7, 15, 15, 0, 0),  # Summer (EDT)
            datetime(2024, 10, 15, 15, 0, 0), # Fall (EDT)
            datetime(2024, 12, 15, 16, 0, 0)  # Winter (EST)
        ]
        
        for test_time in test_cases:
            state = self.trading_clock.get_trading_state(test_time)
            # All should be POST_11AM since they represent 11:00 AM ET in their respective timezones
            assert state == TradingState.POST_11AM


class TestDAOrderRulesEngine:
    """Test DA Order Rules Engine with PJM compliance"""
    
    def setup_method(self):
        """Setup test environment"""
        os.environ["PJM_STATE_MACHINE_ENABLED"] = "true"
        os.environ["MAX_ORDERS_PER_HOUR"] = "10"
        
        self.rules_engine = DAOrderRulesEngine()
        
        # Mock session for testing
        class MockSession:
            def exec(self, statement):
                class MockResult:
                    def all(self):
                        return []  # No existing orders for simplicity
                return MockResult()
        
        self.mock_session = MockSession()
    
    def test_da_order_before_cutoff(self):
        """Test DA order validation before 11 AM cutoff"""
        # 10:30 AM ET = 14:30 UTC (EST) or 13:30 UTC (EDT)
        test_time = datetime(2024, 1, 15, 15, 30, 0)  # Using EST for simplicity
        delivery_time = datetime(2024, 1, 16, 20, 0, 0)  # Next day delivery
        
        result = self.rules_engine.validate_da_order_submission(
            self.mock_session, "test_user", "TEST_NODE", delivery_time, test_time
        )
        
        assert result["valid"] == True
        assert result["trading_state"] == TradingState.PRE_11AM.value
        assert result["permissions"]["da_orders"] == True
    
    def test_da_order_after_cutoff(self):
        """Test DA order validation after 11 AM cutoff"""
        # 2:00 PM ET = 18:00 UTC (EST)
        test_time = datetime(2024, 1, 15, 19, 0, 0)
        delivery_time = datetime(2024, 1, 16, 20, 0, 0)
        
        with pytest.raises(DAOrderValidationError) as exc_info:
            self.rules_engine.validate_da_order_submission(
                self.mock_session, "test_user", "TEST_NODE", delivery_time, test_time
            )
        
        assert exc_info.value.error_code == "DA_MARKET_CLOSED"
    
    def test_edge_case_timing_microsecond_precision(self):
        """Test edge case timing with microsecond precision"""
        # 10:59:59.999 ET - should pass
        before_cutoff = datetime(2024, 1, 15, 15, 59, 59, 999000)
        delivery_time = datetime(2024, 1, 16, 20, 0, 0)
        
        result = self.rules_engine.validate_da_order_submission(
            self.mock_session, "test_user", "TEST_NODE", delivery_time, before_cutoff
        )
        assert result["valid"] == True
        
        # 11:00:00.000 ET - should fail
        at_cutoff = datetime(2024, 1, 15, 16, 0, 0, 0)
        
        with pytest.raises(DAOrderValidationError):
            self.rules_engine.validate_da_order_submission(
                self.mock_session, "test_user", "TEST_NODE", delivery_time, at_cutoff
            )
    
    def test_feature_flag_disabled_legacy_mode(self):
        """Test legacy mode when feature flag is disabled"""
        os.environ["PJM_STATE_MACHINE_ENABLED"] = "false"
        legacy_engine = DAOrderRulesEngine()
        
        # Should use legacy validation logic
        test_time = datetime(2024, 1, 15, 19, 0, 0)  # After cutoff
        delivery_time = datetime(2024, 1, 16, 20, 0, 0)
        
        try:
            result = legacy_engine.validate_da_order_submission(
                self.mock_session, "test_user", "TEST_NODE", delivery_time, test_time
            )
            # Legacy mode may have different behavior
            assert result["trading_state"] == "LEGACY_MODE"
        except DAOrderValidationError as e:
            # Legacy validation should also catch timing violations
            assert e.error_code == "LEGACY_TIMING_CUTOFF"
        
        # Restore flag
        os.environ["PJM_STATE_MACHINE_ENABLED"] = "true"
    
    def test_dst_transition_edge_cases(self):
        """Test DA order validation during DST transitions"""
        # Spring forward - March 10, 2024
        # 10:30 AM EDT = 14:30 UTC (before cutoff)
        spring_before = datetime(2024, 3, 10, 14, 30, 0)
        delivery_time = datetime(2024, 3, 11, 20, 0, 0)
        
        result = self.rules_engine.validate_da_order_submission(
            self.mock_session, "test_user", "TEST_NODE", delivery_time, spring_before
        )
        assert result["valid"] == True
        
        # Fall back - November 3, 2024
        # 10:30 AM EST = 15:30 UTC (before cutoff)  
        fall_before = datetime(2024, 11, 3, 15, 30, 0)
        
        result = self.rules_engine.validate_da_order_submission(
            self.mock_session, "test_user", "TEST_NODE", delivery_time, fall_before
        )
        assert result["valid"] == True


class TestSettlementCalculations:
    """Test bucket-by-bucket settlement calculations"""
    
    def test_bucket_pnl_calculation_buy_order(self):
        """Test PJM bucket P&L calculation for BUY order"""
        from app.services.settlement_engine import calculate_hour_pnl_da_vs_rt
        
        da_price = 50.00  # $/MWh
        quantity_mwh = 2.4  # MWh
        # 12 five-minute RT prices
        rt_prices = [48.0, 49.0, 51.0, 52.0, 53.0, 54.0, 
                    55.0, 54.0, 53.0, 52.0, 50.0, 49.0]
        
        result = calculate_hour_pnl_da_vs_rt(da_price, quantity_mwh, rt_prices, "BUY")
        
        # Verify bucket calculation: q/12 = 2.4/12 = 0.2 MWh per bucket
        expected_bucket_quantity = 0.2
        
        # Verify individual bucket calculations
        assert len(result["bucket_details"]) == 12
        assert result["bucket_details"][0]["bucket_quantity_mwh"] == expected_bucket_quantity
        
        # First bucket: (50 - 48) * 0.2 = 0.4
        assert result["bucket_details"][0]["bucket_pnl"] == 0.4
        
        # Calculate expected total P&L manually
        expected_total = sum((da_price - rt_price) * expected_bucket_quantity for rt_price in rt_prices)
        assert abs(result["hour_pnl_total"] - expected_total) < 0.01
        
        # Verify formula documentation
        assert result["formula_used"] == "P&L_H = Σ(P_DA - P_RT,t) × q/12"
        assert result["intervals_calculated"] == 12
    
    def test_bucket_pnl_calculation_sell_order(self):
        """Test PJM bucket P&L calculation for SELL order"""
        from app.services.settlement_engine import calculate_hour_pnl_da_vs_rt
        
        da_price = 50.00  # $/MWh
        quantity_mwh = 1.8  # MWh  
        rt_prices = [55.0, 54.0, 53.0, 52.0, 51.0, 50.0,
                    49.0, 48.0, 47.0, 46.0, 45.0, 44.0]
        
        result = calculate_hour_pnl_da_vs_rt(da_price, quantity_mwh, rt_prices, "SELL")
        
        # For SELL: P&L = (P_DA - P_RT,t) × q/12
        # When RT > DA, P&L is negative (had to buy back at higher price)
        # When RT < DA, P&L is positive (sold high, replaced cheap)
        
        bucket_quantity = 1.8 / 12  # 0.15 MWh per bucket
        
        # First bucket: RT=55, DA=50 → (50-55) * 0.15 = -0.75 (negative P&L)
        assert result["bucket_details"][0]["bucket_pnl"] == -0.75
        
        # Last bucket: RT=44, DA=50 → (50-44) * 0.15 = 0.9 (positive P&L)  
        assert result["bucket_details"][11]["bucket_pnl"] == 0.9
        
        # Verify the formula works correctly for both BUY and SELL
        expected_total = sum((da_price - rt_price) * bucket_quantity for rt_price in rt_prices)
        assert abs(result["hour_pnl_total"] - expected_total) < 0.01
    
    def test_invalid_rt_price_count(self):
        """Test error handling for invalid RT price count"""
        from app.services.settlement_engine import calculate_hour_pnl_da_vs_rt
        
        # Only 11 prices instead of required 12
        invalid_rt_prices = [50.0] * 11
        
        with pytest.raises(ValueError) as exc_info:
            calculate_hour_pnl_da_vs_rt(45.0, 2.0, invalid_rt_prices)
        
        assert "exactly 12 five-minute intervals" in str(exc_info.value)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])