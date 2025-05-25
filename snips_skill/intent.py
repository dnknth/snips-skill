from datetime import datetime, timedelta
from functools import cached_property
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

__all__ = ("IntentPayload",)


class UnknownValue(BaseModel):
    kind: Literal["Unknown"]
    value: str


class NumericValue(BaseModel):
    kind: Literal["Number"]
    value: int | float


# See: https://docs.snips.ai/articles/platform/dialog/slot-types#time-related-entities
class InstantTimeValue(BaseModel):
    kind: Literal["InstantTime"]
    grain: str
    precision: str
    value: datetime


class TimeIntervalValue(BaseModel):
    kind: Literal["TimeInterval"]
    t1: datetime | None = Field(alias="from", default=None)
    t2: datetime | None = Field(alias="to", default=None)


# See: https://docs.snips.ai/articles/platform/dialog/slot-types#duration-entities
class DurationValue(BaseModel):
    kind: Literal["Duration"]
    precision: str
    years: int = 0
    quarters: int = 0
    months: int = 0
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0

    def as_timedelta(self) -> timedelta:
        # TODO: years, quarters and months are not parsed
        return timedelta(
            weeks=self.weeks,
            days=self.days,
            hours=self.hours,
            minutes=self.minutes,
            seconds=self.seconds,
        )


class TemperatureValue(BaseModel):
    kind: Literal["Temperature"]
    unit: str
    value: float


class MonetaryValue(BaseModel):
    kind: Literal["AmountOfMoney"]
    unit: str
    precision: str
    value: float


class Range(BaseModel, alias_generator=to_camel, serialize_by_alias=True):
    start: int
    end: int
    raw_start: int
    raw_end: int


SlotValue = Annotated[
    UnknownValue
    | NumericValue
    | InstantTimeValue
    | TimeIntervalValue
    | DurationValue
    | TemperatureValue
    | MonetaryValue,
    Field(discriminator="kind"),
]


# See: https://docs.snips.ai/reference/dialogue#slot
class Slot(BaseModel, alias_generator=to_camel, serialize_by_alias=True):
    entity: str
    slot_name: str
    raw_value: str
    confidence: float
    range: Range | None
    value: SlotValue


# See: https://docs.snips.ai/reference/dialogue#intent
class Intent(BaseModel, alias_generator=to_camel, serialize_by_alias=True):
    intent_name: str
    confidence_score: float


class AsrToken(BaseModel, alias_generator=to_camel, serialize_by_alias=True):
    value: str
    confidence: float
    range_start: int
    range_end: int
    time: None


# See: https://docs.snips.ai/reference/dialogue#intent
class IntentPayload(BaseModel, alias_generator=to_camel, serialize_by_alias=True):
    session_id: str
    input: str
    intent: Intent
    site_id: str
    slots: list[Slot] | None = None
    id: str | None = None
    session_id: str
    custom_data: str
    asr_tokens: list[list[AsrToken]]
    asr_confidence: float
    raw_input: str
    # wakeword_id: str
    # lang: None

    @cached_property
    def slot_values(self) -> dict[str, SlotValue]:
        return {s.slot_name: s.value for s in self.slots or []}

    def __getitem__(self, name):
        return self.slot_values[name]
