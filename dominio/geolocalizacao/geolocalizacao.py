"""Geolocalizacao (diagrama): ponto na Terra + distância pela fórmula de Haversine."""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

# Raio médio da Terra (IUGG), em metros.
RAIO_TERRA_METROS = 6_371_008.8


@dataclass(frozen=True)
class Geolocalizacao:
    latitude: float
    longitude: float

    def __post_init__(self):
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude deve estar entre -90 e 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude deve estar entre -180 e 180")

    def get_coordenadas(self) -> str:
        return f"{self.latitude}, {self.longitude}"

    def calcular_distancia_em_metros(self, destino: "Geolocalizacao") -> float:
        """Distância em círculo máximo (Haversine), em metros."""
        phi1, phi2 = radians(self.latitude), radians(destino.latitude)
        d_phi = phi2 - phi1
        d_lambda = radians(destino.longitude - self.longitude)
        a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
        return 2 * RAIO_TERRA_METROS * asin(min(1.0, sqrt(a)))