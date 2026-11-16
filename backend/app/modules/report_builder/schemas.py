from pydantic import BaseModel, Field, field_validator


class ReportBlock(BaseModel):
    id: str = Field(min_length=3, max_length=60, pattern=r'^[a-zA-Z0-9_-]+$')
    kind: str
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(default='', max_length=2000)
    metric_codes: list[str] = Field(default_factory=list, max_length=2)
    aggregation: str = 'avg'
    granularity: str = 'day'


class ReportCreate(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    description: str = Field(default='', max_length=500)
    scope: str = 'personal'
    blocks: list[ReportBlock] = Field(min_length=1, max_length=16)

    @field_validator('scope')
    @classmethod
    def scope_valid(cls, value):
        if value not in {'system', 'personal'}:
            raise ValueError('Jenis template tidak valid')
        return value


class ReportUpdate(ReportCreate):
    expected_version: int = Field(ge=1)


class ReportPreview(BaseModel):
    blocks: list[ReportBlock] = Field(min_length=1, max_length=16)
    start: str
    end: str
