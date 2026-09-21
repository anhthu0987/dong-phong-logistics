import unittest
from unittest.mock import Mock, patch
from dp_dispatch.dp_dispatch import simulator


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(base_url='http://localhost:8086', api_key='test-key',
                           api_secret='test-secret', interval_seconds=0,
                           vehicle='TEST', delivery_trip='TEST-TRIP')

    @patch.dict(simulator.os.environ, {}, clear=True)
    @patch('builtins.print')
    def test_auth_and_distinct_runs(self, output):
        response = Mock(status_code=200)
        response.json.return_value = {'message': {'status': 'success'}}
        with patch.object(simulator.requests, 'post', return_value=response) as post:
            simulator.run_simulation(self.config)
            first = post.call_args_list[0].kwargs
            self.assertEqual(first['headers']['Authorization'], 'token test-key:test-secret')
            self.assertFalse(first['allow_redirects'])
            self.assertEqual(post.call_count, len(simulator.SIMULATED_ROUTE))
            post.reset_mock()
            simulator.run_simulation(self.config)
            self.assertNotEqual(first['data']['source_event_id'], post.call_args_list[0].kwargs['data']['source_event_id'])

    @patch.dict(simulator.os.environ, {}, clear=True)
    def test_missing_auth_sends_nothing(self):
        with patch.object(simulator.requests, 'post') as post:
            with self.assertRaises(ValueError):
                simulator.run_simulation({})
            post.assert_not_called()

    @patch.dict(simulator.os.environ, {}, clear=True)
    @patch('builtins.print')
    def test_rejection_stops_route(self, output):
        with patch.object(simulator.requests, 'post', return_value=Mock(status_code=403)) as post:
            with self.assertRaisesRegex(RuntimeError, '403'):
                simulator.run_simulation(self.config)
            self.assertEqual(post.call_count, 1)
            self.assertFalse(any('HOÀN THÀNH' in str(c) for c in output.call_args_list))

    @patch.dict(simulator.os.environ, {'DP_GPS_API_KEY':'env-key', 'DP_GPS_API_SECRET':'env-secret'}, clear=True)
    @patch('builtins.print')
    def test_env_overrides_private_config(self, output):
        response = Mock(status_code=200)
        response.json.return_value = {'message': {'status': 'success'}}
        with patch.object(simulator.requests, 'post', return_value=response) as post:
            simulator.run_simulation(self.config)
            self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'token env-key:env-secret')


if __name__ == '__main__':
    unittest.main()
