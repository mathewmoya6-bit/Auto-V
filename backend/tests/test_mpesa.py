# tests/test_mpesa.py – M-Pesa Unit Tests

import unittest
from unittest.mock import Mock, patch
from services.mpesa_service import initiate_stk_push, normalize_phone

class TestMpesaService(unittest.TestCase):
    
    def test_normalize_phone(self):
        """Test phone number normalization."""
        # Test local format
        self.assertEqual(normalize_phone('0712345678'), '254712345678')
        
        # Test with +254
        self.assertEqual(normalize_phone('+254712345678'), '254712345678')
        
        # Test already normalized
        self.assertEqual(normalize_phone('254712345678'), '254712345678')
        
        # Test invalid
        with self.assertRaises(ValueError):
            normalize_phone('12345')
    
    @patch('services.mpesa_service.get_access_token')
    @patch('services.mpesa_service.requests.post')
    def test_initiate_stk_push(self, mock_post, mock_token):
        """Test STK Push initiation."""
        mock_token.return_value = 'fake_token'
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'ResponseCode': '0',
            'CheckoutRequestID': 'ws_CO_123456789',
            'ResponseDescription': 'Success'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = initiate_stk_push(
            phone='0712345678',
            amount=100,
            payment_id='test-123',
            service='valuation'
        )
        
        self.assertEqual(result['ResponseCode'], '0')
        self.assertEqual(result['CheckoutRequestID'], 'ws_CO_123456789')

if __name__ == '__main__':
    unittest.main()
