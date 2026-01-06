from enum import Enum
from typing import Optional, Dict, Any

class ServiceType(str, Enum):
    PREVENTIVNA_PREHLIADKA = "Preventívna prehliadka"
    DENTALNE_CISTENIE = "Dentálne čistenie"
    KOMPOZITNA_VYPLN = "Kompozitná výplň"
    KORENOVE_OSETRENIE = "Koreňové ošetrenie"
    KORUNKA = "Korunka"
    IMPLANTAT = "Implantát"
    BIELENIE_ZUBOV = "Bielenie zubov"
    VSTUPNE_VYSETRENIE = "Vstupné vyšetrenie"
    KONZULTACIA = "Konzultácia"
    URGENTNY_PRIKAZ = "Urgentný prípad"

# Source of Truth for Services
SERVICES_DB: Dict[str, Dict[str, Any]] = {
    "Preventívna prehliadka": {
        "price": "20 €",
        "duration_min": 30,
        "category": "Preventívna stomatológia"
    },
    "Dentálne čistenie": {
        "price": "45–80 €",
        "duration_min": 60,
        "category": "Preventívna stomatológia",
        "aliases": ["hygiena", "dentálna hygiena", "čistenie zubov", "scaling"]
    },
    "Kompozitná výplň": {
        "price": "60–120 €",
        "duration_min": 45,
        "category": "Konzervatívna stomatológia",
        "aliases": ["plomba", "kaz", "výplň"]
    },
    "Koreňové ošetrenie": {
        "price": "150–300 €",
        "duration_min": 90,
        "category": "Konzervatívna stomatológia",
        "aliases": ["endodoncia", "koreň", "nervy"]
    },
    "Korunka": {
        "price": "450–800 €",
        "duration_min": 60,
        "category": "Protétika"
    },
    "Implantát": {
        "price": "800–1 200 €",
        "duration_min": 60,
        "category": "Implantológia"
    },
    "Bielenie zubov": {
        "price": "250–400 €",
        "duration_min": 60,
        "category": "Estetická stomatológia"
    },
    "Vstupné vyšetrenie": {
        "price": "20–50 €",
        "duration_min": 30,
        "category": "Preventívna stomatológia",
        "aliases": ["vstupná prehliadka", "prvé vyšetrenie"]
    },
    "Urgentný prípad": {
        "price": "Podľa výkonu",
        "duration_min": 30,
        "category": "Urgentné služby",
        "aliases": ["bolesť", "opuch", "akútne"]
    }
}

def validate_service(service_name: str) -> Optional[str]:
    """
    Validates if the service exists in our DB.
    Returns the canonical service name if found, None otherwise.
    Matches loosely against keys and aliases.
    """
    if not service_name:
        return None
        
    s_lower = service_name.lower().strip()
    
    # Direct match
    for canonical in SERVICES_DB.keys():
        if s_lower == canonical.lower():
            return canonical
            
    # Alias match
    for canonical, details in SERVICES_DB.items():
        if "aliases" in details:
            for alias in details["aliases"]:
                if alias in s_lower:
                    return canonical
                    
    return None

def get_service_details(service_name: str) -> Optional[Dict[str, Any]]:
    canonical = validate_service(service_name)
    if canonical:
        return SERVICES_DB[canonical]
    return None
