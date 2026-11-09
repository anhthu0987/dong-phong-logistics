import unittest
from solver import solve
from osrm_routes import matrix,RoutesError
from unittest.mock import patch

def payload():
 return dict(horizon=3600,vehicles=[dict(name='V',capacity=100000,origin=dict(lat=10.8,lng=106.7))],orders=[dict(name='O',weight=50000,pickup=dict(lat=10.81,lng=106.71,window=[0,1800],service=60),delivery=dict(lat=10.82,lng=106.72,window=[0,2400],service=60))])

class RoutingTests(unittest.TestCase):
 def test_pickup_delivery(self):
  r=solve(payload(),[[0,60,120],[60,0,60],[120,60,0]],[[0,500,1000],[500,0,500],[1000,500,0]])
  self.assertEqual(r['status'],'Ready');self.assertEqual([s['kind'] for s in r['routes'][0]['stops']],['pickup','delivery'])
  self.assertEqual([s['load'] for s in r['routes'][0]['stops']],[50000,0])
 def test_overload(self):
  d=payload();d['orders'][0]['weight']=200000
  self.assertEqual(solve(d,[[0]*3 for _ in range(3)],[[0]*3 for _ in range(3)])['status'],'Infeasible')
 def test_bad_matrix(self):
  with self.assertRaises(ValueError):solve(payload(),[[0]],[[0]])
 def test_missing_road_fails(self):
  with patch('osrm_routes.call',return_value={'durations':[[None]*3 for _ in range(3)],'distances':[[0]*3 for _ in range(3)]}),self.assertRaises(RoutesError):matrix(payload())
 def test_wrong_vehicle_type(self):
  d=payload();d['orders'][0]['vehicle_type']='Refrigerated'
  self.assertEqual(solve(d,[[0]*3 for _ in range(3)],[[0]*3 for _ in range(3)])['status'],'Infeasible')

if __name__=='__main__':unittest.main()
