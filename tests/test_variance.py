from starry_process import StarryProcess
import numpy as np

# BROKEN!
def test_variance():

    sp = StarryProcess()
    cov = sp.cov([0.0, 0.1])
    var = sp.cov([0.0])

    assert np.allclose(cov[0, 0], var)