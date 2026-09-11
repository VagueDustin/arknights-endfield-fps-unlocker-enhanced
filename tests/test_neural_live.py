import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import neural_live

class NativeControlTests(unittest.TestCase):
    def settings(self):
        return dict(enabled=1,style=2,preset=0,intensity=1,structure=1,tone=1,skin=-1,auto_mask=1)
    def test_round_trip(self):
        self.assertEqual(neural_live.decode(neural_live.encode(self.settings())),self.settings())
    def test_invalid_values(self):
        for key,value in [('style',3),('preset',4),('enabled',2),('auto_mask',-1),
                          ('intensity',math.nan),('tone',math.inf),('skin',-2),('structure',2.1),('style',1.5)]:
            with self.subTest(key=key,value=value):
                data=self.settings();data[key]=value
                with self.assertRaises(ValueError):neural_live.encode(data)
    def test_acceptance_is_not_rendering(self):
        state=dict(accepted=2,evaluated=0,frames=0,settings=self.settings())
        self.assertIn('not yet confirmed',neural_live.describe(state))
        state['evaluated']=2
        self.assertIn('successful NR evaluation',neural_live.describe(state))

if __name__=='__main__':unittest.main()
