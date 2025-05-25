from typing import Literal

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel


class ActionInit(
    BaseModel, alias_generator=to_camel, serialize_by_alias=True, validate_by_name=True
):
    "Start a session with an action"

    # See: https://docs.snips.ai/reference/dialogue#session-initialization-action
    type: Literal["action"] = "action"
    text: str | None = None
    intent_filter: list[str] | None = None
    can_be_enqueued: bool = True
    send_intent_not_recognized: bool = False


class NotififationInit(BaseModel):
    "Start a session with a notification"

    # See: https://docs.snips.ai/reference/dialogue#session-initialization-notification
    type: Literal["notification"] = "notification"
    text: str


class StartSession(
    BaseModel, alias_generator=to_camel, serialize_by_alias=True, validate_by_name=True
):
    "Start a session with an optional message"

    # See: https://docs.snips.ai/reference/dialogue#start-session
    site_id: str
    init: ActionInit | NotififationInit = Field(discriminator="type")
    custom_data: str | None = None


class EndSession(
    BaseModel, alias_generator=to_camel, serialize_by_alias=True, validate_by_name=True
):
    "End the session with an optional message"

    # See: https://docs.snips.ai/reference/dialogue#end-session
    session_id: str
    text: str | None = None


class ContinueSession(
    BaseModel, alias_generator=to_camel, serialize_by_alias=True, validate_by_name=True
):
    "Continue the session with a question"

    # See: https://docs.snips.ai/reference/dialogue#continue-session
    session_id: str
    text: str
    intent_filter: list[str] | None = None
    slot: str | None = None
    send_intent_not_recognized: bool = False
    custom_data: str | None = None
