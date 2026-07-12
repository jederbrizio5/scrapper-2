from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class EnrichedDomain:
    """Dominio completamente enriquecido con todas las etapas."""

    # Identidad
    domain: str
    library_id: Optional[str] = None
    keyword: Optional[str] = None

    # Stage 1: Discovery
    discovery: Optional[dict] = None
    discovery_status: str = "pending"

    # Stage 2: Meta Enrichment
    meta_enrichment: Optional[dict] = None
    meta_enrichment_status: str = "pending"

    # Stage 3: Landing Enrichment
    landing_enrichment: Optional[dict] = None
    landing_enrichment_status: str = "pending"

    # Stage 4: Social Enrichment
    social_enrichment: Optional[dict] = None
    social_enrichment_status: str = "pending"

    # Pipeline status
    pipeline_status: str = "pending"  # pending, partial, completed, failed
    completed_stages: list[str] = field(default_factory=list)
    errors: dict = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S hs")

    def get_completed_stages(self) -> list[str]:
        """Detecta qué etapas están completadas basado en los datos."""
        stages = []
        if self.discovery and self.discovery.get("library_id"):
            stages.append("discovery")
        if self.meta_enrichment or self.discovery and self.discovery.get("enrichment"):
            stages.append("meta_enrichment")
        if (
            self.landing_enrichment
            and self.landing_enrichment.get("status") == "completed"
        ):
            stages.append("landing_enrichment")
        if self.social_enrichment:
            fb = self.social_enrichment.get("facebook")
            ig = self.social_enrichment.get("instagram")
            fb_ok = fb and fb.get("status") == "completed"
            ig_ok = ig and ig.get("status") == "completed"
            if fb_ok or ig_ok:
                stages.append("social_enrichment")
        return stages

    def update_pipeline_status(self):
        """Actualiza estado general del pipeline."""
        self.completed_stages = self.get_completed_stages()
        expected = [
            "discovery",
            "meta_enrichment",
            "landing_enrichment",
            "social_enrichment",
        ]

        if all(s in self.completed_stages for s in expected):
            self.pipeline_status = "completed"
            if self.completed_at is None:
                self.completed_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S hs")
        elif self.completed_stages:
            self.pipeline_status = "partial"
        else:
            self.pipeline_status = "pending"

        # Detectar errores
        self.errors = {}
        if self.landing_enrichment and self.landing_enrichment.get("error"):
            self.errors["landing_enrichment"] = self.landing_enrichment["error"]
        if self.social_enrichment:
            fb = self.social_enrichment.get("facebook")
            ig = self.social_enrichment.get("instagram")
            if fb and fb.get("error"):
                self.errors.setdefault("social_enrichment", {})["facebook"] = fb[
                    "error"
                ]
            if ig and ig.get("error"):
                self.errors.setdefault("social_enrichment", {})["instagram"] = ig[
                    "error"
                ]

    def to_output_dict(self) -> dict:
        """Convierte al formato de salida JSON (compatibilidad con estructura actual)."""
        self.update_pipeline_status()

        # Compatibilidad: mantener "enrichment" como alias de meta_enrichment
        output = {
            "discovery": self.discovery,
        }

        if self.meta_enrichment:
            output["meta_enrichment"] = self.meta_enrichment
            output["enrichment"] = self.meta_enrichment  # retrocompat

        if self.landing_enrichment:
            output["landing_enrichment"] = self.landing_enrichment

        if self.social_enrichment:
            output["social_enrichment"] = self.social_enrichment

        # Metadata del pipeline
        output["pipeline_status"] = self.pipeline_status
        output["completed_stages"] = self.completed_stages
        output["errors"] = self.errors

        return output

    @classmethod
    def from_existing_entry(cls, entry: dict) -> "EnrichedDomain":
        """Crea EnrichedDomain desde entry JSON existente (para resume)."""
        disc = entry.get("discovery", entry)
        meta_enrich = entry.get("meta_enrichment") or entry.get("enrichment")
        landing = entry.get("landing_enrichment")
        social = entry.get("social_enrichment")

        return cls(
            domain=disc.get("domain", ""),
            library_id=disc.get("library_id"),
            keyword=disc.get("keyword"),
            discovery=disc,
            meta_enrichment=meta_enrich,
            landing_enrichment=landing,
            social_enrichment=social,
            discovery_status="completed" if disc.get("library_id") else "pending",
            meta_enrichment_status="completed" if meta_enrich else "pending",
            landing_enrichment_status=landing.get("status", "pending")
            if landing
            else "pending",
            social_enrichment_status="completed" if social else "pending",
        )


@dataclass
class PipelineState:
    """Estado global del pipeline para checkpoint/resume."""

    run_id: str
    started_at: str
    keywords: list[str]
    config: dict
    domains: list[EnrichedDomain] = field(default_factory=list)
    completed_stages_global: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "keywords": self.keywords,
            "config": self.config,
            "domains": [d.to_output_dict() for d in self.domains],
            "completed_stages_global": self.completed_stages_global,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineState":
        domains = [
            EnrichedDomain.from_existing_entry(d) for d in data.get("domains", [])
        ]
        return cls(
            run_id=data["run_id"],
            started_at=data["started_at"],
            keywords=data["keywords"],
            config=data["config"],
            domains=domains,
            completed_stages_global=data.get("completed_stages_global", []),
            stats=data.get("stats", {}),
        )
