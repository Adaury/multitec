from pydantic import BaseModel


class AccessoryCandidateOut(BaseModel):
    source_product_id: int
    source_product_name: str
    added_product_id: int
    added_product_name: str
    suggested_target_tag: str | None
    project_count: int
    total_projects_with_source: int
    ratio: float
    example_quantity: float
    example_project_codes: list[str]

    class Config:
        from_attributes = True


class StaleRuleCandidateOut(BaseModel):
    rule_id: int
    source_product_id: int
    source_product_name: str
    target_tag: str
    would_add_product_id: int | None
    would_add_product_name: str | None
    removed_count: int
    total_projects_with_source: int
    ratio: float
    example_project_codes: list[str]

    class Config:
        from_attributes = True


class LearningAnalysisOut(BaseModel):
    accessory_candidates: list[AccessoryCandidateOut]
    stale_rule_candidates: list[StaleRuleCandidateOut]
