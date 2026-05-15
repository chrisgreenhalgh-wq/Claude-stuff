from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Lead:
    name: str
    profile_url: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    connection_degree: Optional[str] = None
    mutual_connections: Optional[int] = None
    about: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    scraped_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
