"""
Embedded Python Block: ADS-B Max-Range-per-ICAO Logger (+ session stats)
Consumes decoded ADS-B position messages (PMT dict with keys:
lat, lon, alt, icao) and maintains:
  1) a CSV of the MAXIMUM range seen per aircraft (ICAO) this session
  2) a one-line summary CSV with total messages, unique aircraft count,
     and best range achieved -- for quick antenna-config comparison
"""

import numpy as np
import pmt
import csv
import time
import os
from gnuradio import gr


class blk(gr.basic_block):
    def __init__(self, rx_lat=0.0, rx_lon=0.0, rx_alt=0.0,
                 config_name="default",
                 csv_path="/tmp/adsb_max_ranges.csv",
                 summary_path="/tmp/adsb_summary.csv"):
        gr.basic_block.__init__(
            self,
            name="ADS-B Max Range Logger",
            in_sig=[],
            out_sig=[]
        )

        self.rx_lat = rx_lat
        self.rx_lon = rx_lon
        self.rx_alt = rx_alt       # meters
        self.config_name = config_name
        self.csv_path = csv_path
        self.summary_path = summary_path

        self._best = {}            # icao -> record dict
        self._total_msgs = 0
        self._start_time = time.time()

        self.message_port_register_in(pmt.intern("pos_in"))
        self.set_msg_handler(pmt.intern("pos_in"), self.handle_msg)

    def handle_msg(self, msg):
        try:
            d = pmt.to_python(msg)
        except Exception:
            return

        if not isinstance(d, dict):
            return

        lat = d.get("lat")
        lon = d.get("lon")
        alt = d.get("alt")   # meters expected; adjust if your decoder uses feet
        icao = d.get("icao", "unknown")

        if lat is None or lon is None or alt is None:
            return

        self._total_msgs += 1

        rng_m = self._range_m(self.rx_lat, self.rx_lon, self.rx_alt,
                               lat, lon, alt)

        prev = self._best.get(icao)
        updated = False
        if prev is None or rng_m > prev["range_m"]:
            self._best[icao] = {
                "icao": icao,
                "lat": lat,
                "lon": lon,
                "alt_m": alt,
                "range_m": rng_m,
                "range_nm": rng_m / 1852.0,
                "timestamp": time.time(),
            }
            updated = True

        if updated:
            self._write_csv()
        self._write_summary()  # cheap, always keep this current

    def _write_csv(self):
        tmp_path = self.csv_path + ".tmp"
        with open(tmp_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "config_name", "icao", "max_range_m", "max_range_nm",
                "ac_lat", "ac_lon", "ac_alt_m", "timestamp"
            ])
            for rec in sorted(self._best.values(),
                               key=lambda r: r["range_m"], reverse=True):
                writer.writerow([
                    self.config_name, rec["icao"],
                    rec["range_m"], rec["range_nm"],
                    rec["lat"], rec["lon"], rec["alt_m"],
                    rec["timestamp"]
                ])
        os.replace(tmp_path, self.csv_path)

    def _write_summary(self):
        elapsed_s = time.time() - self._start_time
        unique_icaos = len(self._best)
        best_nm = max((r["range_nm"] for r in self._best.values()), default=0.0)
        # rough median of best ranges -- gives a sense of typical, not just peak, range
        if unique_icaos:
            med_nm = float(np.median([r["range_nm"] for r in self._best.values()]))
        else:
            med_nm = 0.0

        tmp_path = self.summary_path + ".tmp"
        with open(tmp_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "config_name", "elapsed_s", "total_msgs",
                "unique_icaos", "best_range_nm", "median_best_range_nm"
            ])
            writer.writerow([
                self.config_name, round(elapsed_s, 1), self._total_msgs,
                unique_icaos, round(best_nm, 2), round(med_nm, 2)
            ])
        os.replace(tmp_path, self.summary_path)

    @staticmethod
    def _range_m(lat1, lon1, alt1, lat2, lon2, alt2):
        """Slant range in meters via ECEF, WGS-84 ellipsoid."""
        a = 6378137.0
        f = 1 / 298.257223563
        e2 = f * (2 - f)

        def geodetic_to_ecef(lat, lon, alt):
            lat_r = np.radians(lat)
            lon_r = np.radians(lon)
            N = a / np.sqrt(1 - e2 * np.sin(lat_r) ** 2)
            x = (N + alt) * np.cos(lat_r) * np.cos(lon_r)
            y = (N + alt) * np.cos(lat_r) * np.sin(lon_r)
            z = (N * (1 - e2) + alt) * np.sin(lat_r)
            return np.array([x, y, z])

        p1 = geodetic_to_ecef(lat1, lon1, alt1)
        p2 = geodetic_to_ecef(lat2, lon2, alt2)
        return float(np.linalg.norm(p2 - p1))
        
