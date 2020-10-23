from .defaults import update_with_defaults
import starry
import numpy as np
from tqdm import tqdm


class Star(object):
    def __init__(self, nlon=300, ydeg=30, linear=True):
        # Generate a uniform intensity grid
        self.nlon = nlon
        self.nlat = nlon // 2
        self.lon = np.linspace(-180, 180, self.nlon)
        self.lat = np.linspace(-90, 90, self.nlat)
        self.lon, self.lat = np.meshgrid(self.lon, self.lat)
        self.intensity = np.zeros_like(self.lat)
        self.linear = linear

        # Instantiate a starry map
        self.map = starry.Map(ydeg, lazy=False)

    def _angular_distance(self, lam1, lam2, phi1, phi2):
        # https://en.wikipedia.org/wiki/Great-circle_distance
        return (
            np.arccos(
                np.sin(phi1 * np.pi / 180) * np.sin(phi2 * np.pi / 180)
                + np.cos(phi1 * np.pi / 180)
                * np.cos(phi2 * np.pi / 180)
                * np.cos((lam2 - lam1) * np.pi / 180)
            )
            * 180
            / np.pi
        )

    def reset(self):
        self.intensity = np.zeros_like(self.lat)

    def add_spot(self, lon, lat, radius, contrast):
        idx = self._angular_distance(lon, self.lon, lat, self.lat) <= radius
        if self.linear:
            self.intensity[idx] -= contrast
        else:
            self.intensity[idx] = -contrast

    def flux(self, t, period=1.0, inc=60.0, smoothing=0.1):
        # Expand in Ylms
        self.map.load(self.intensity)
        self.map.inc = inc

        # Smooth to get rid of ringing
        if smoothing > 0:
            l = np.concatenate(
                [np.repeat(l, 2 * l + 1) for l in range(self.map.ydeg + 1)]
            )
            s = np.exp(-0.5 * l * (l + 1) * smoothing ** 2)
            self.map._y *= s

        # Get the flux
        return self.map.flux(theta=360.0 / period * t)


def generate(**kwargs):

    # Get kwargs
    kwargs = update_with_defaults(**kwargs)
    gen_kwargs = kwargs["generate"]
    normalized = gen_kwargs["normalized"]
    nlon = gen_kwargs["nlon"]
    ydeg = gen_kwargs["ydeg"]
    smoothing = gen_kwargs["smoothing"]
    seed = gen_kwargs["seed"]
    nlc = gen_kwargs["nlc"]
    npts = gen_kwargs["npts"]
    tmax = gen_kwargs["tmax"]
    period = gen_kwargs["period"]
    ferr = gen_kwargs["ferr"]
    nspots = lambda: int(
        gen_kwargs["nspots"]["mu"]
        + gen_kwargs["nspots"]["sigma"] * np.random.randn()
    )
    radius = lambda: (
        gen_kwargs["radius"]["mu"]
        + gen_kwargs["radius"]["sigma"] * np.random.randn()
    )
    longitude = lambda: np.random.uniform(-180, 180)
    latitude = lambda: (
        (1 if np.random.random() < 0.5 else -1) * gen_kwargs["latitude"]["mu"]
        + gen_kwargs["latitude"]["sigma"] * np.random.randn()
    )
    contrast = lambda: (
        gen_kwargs["contrast"]["mu"]
        + gen_kwargs["contrast"]["sigma"] * np.random.randn()
    )

    # Generate `nlc` light curves
    np.random.seed(seed)
    t = np.linspace(0, tmax, npts)
    flux0 = np.empty((nlc, npts))
    flux = np.empty((nlc, npts))
    images = [None for k in range(nlc)]
    incs = 180 / np.pi * np.arccos(np.random.uniform(0, 1, size=nlc))
    y = np.zeros((nlc, (ydeg + 1) ** 2))
    star = Star(nlon=nlon, ydeg=ydeg, linear=gen_kwargs["nspots"]["linear"])
    for k in tqdm(range(nlc)):

        # Generate the stellar map
        star.reset()
        nspots_cur = nspots()
        for _ in range(nspots_cur):
            star.add_spot(longitude(), latitude(), radius(), contrast())

        # Get the light curve
        flux0[k] = star.flux(
            t, period=period, inc=incs[k], smoothing=smoothing
        )

        # Render the surface
        images[k] = 1.0 + star.map.render(projection="moll", res=300)
        y[k] = np.array(star.map.amp * star.map.y)

    # Add photon noise
    for k in tqdm(range(nlc)):
        flux[k] = flux0[k] + ferr * np.random.randn(npts)

        if normalized:
            flux[k] = (1 + flux[k]) / (1 + np.median(flux[k])) - 1

    # Return a dict
    data = dict(
        t=t,
        flux0=flux0,
        flux=flux,
        ferr=ferr,
        period=period,
        incs=incs,
        images=images,
        y=y,
    )
    return data